"""Archive light table: real page scans on a cool backlit table, a loupe at a true
magnification, accent-colour marks, a dark caption plate.  1080x1920, 30 fps.

Every animated value is a pure function of the frame number.  Nothing in a scan
is redrawn, retouched or generated.  The only change made to scan pixels is one
uniform levels curve (``film["levels"]``), applied identically to the table
image and to the lens, so the loupe shows exactly what lies on the table.

Demo (writes stills, strip and accent variants)::

    E:/CLAUDE/VIRAL/.venv/Scripts/python.exe build/table_test/demo.py

API::

    scene = load(film, narration, accent=None)   # static layers built once
    validate(scene) -> list[str]                 # layout problems, [] when clean
    frame(scene, n) -> PIL.Image (RGB 1080x1920)
    still(film, narration, when, out_png, accent=None)
    frames(film, narration, accent=None, workers=4, start=0, stop=None)  # numpy uint8 (H, W, 3)
    strip(film, narration, out_jpg, count=8, accent=None)

``narration`` is the dict written by engine/voice.py.  All times are time
expressions (``"s3"``, ``"s3.end"``, ``"s3.cue:name"``, ``"s3+0.4"``) or plain
seconds, resolved with engine/timeline.py.

Film schema (plain data; coordinates in "table px" are frame pixels at camera
scale 1; "scan px" are pixels of the upright scan, i.e. after ``rotate``)::

    {
      "hook":   {"lines": ["What did Stonehenge", "look like in 1740?"],
                 "x": 60, "y": 200},               # on screen from frame 0, never moves; accent underline
      "levels": {"black": 0, "gain": 1.06, "lift": 6},   # optional, uniform, out = (in-black)*gain+lift
      "objects": [{"id": "plan", "scan": "path.jp2" | "archive.zip!member.jp2",
                   "rotate": 90,                   # counter-clockwise quarter turns, degrees (0/90/180/270)
                   "crop": [x0, y0, x1, y1],       # optional, scan px
                   "centre": [x, y], "width": 440, # table px; height follows the crop aspect
                   "tilt": -4.0, "z": 1}],         # degrees, positive = counter-clockwise; stacking order
      "loupe":  {"radius": 230, "magnification": 2.5,   # lens px per on-table px, whole film
                 "fade_in": {"at": "s3", "dur": 0.4}, "fade_out": {"at": "s5", "dur": 0.7},
                 "enter": [x, y],                  # optional table px start point
                 "stops": [{"object": "wide", "at": [sx, sy], "arrive": "s3+1.6",
                            "travel": 1.8, "bulge": 0.2}]},   # glides on a curved path, eased
      "marks":  [{"id": "m1", "type": "ellipse"|"underline"|"box"|"ring-around-object",
                  "object": "wide", "box": [x0, y0, x1, y1],   # scan px (optional for ring)
                  "draw": "s3+2", "dur": 0.9,
                  "fade": {"at": "s4", "dur": 0.4},            # optional
                  "width": 2.6}],                              # table px; magnified in the lens
      "plate":  {"label": "...", "reading": "TAB. XIII", "text": "..." | ["line", ...],
                 "source": "...", "ours": "...",   # ours is drawn in the accent colour
                 "x": 60, "bottom": 1380, "width": 800,        # or "y" for the top edge
                 "in": {"at": "s6", "dur": 0.9}, "rise": 24,
                 "leader": {"from": "m2" | "loupe", "at": "s6+0.4", "dur": 0.6}},   # optional
      "camera": {"scale": [1.0, 1.06], "focus": [540, 900],
                 "moves": [{"at": "s5", "dur": 3.0, "focus": [400, 820]}]},
      "credit": {"text": "...", "at": "end-2.2", "dur": 0.6, "x": 60, "bottom": 1524}
    }

Subtitles are the narration sentences, one at a time, with 0.15 s fades, styled
from tokens.json ("captions").  The accent colour is used only for marks, the
hook underline, the plate edge bar and the plate "ours" line.
"""
from __future__ import annotations

import io
import json
import math
import multiprocessing as mp
import zipfile
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Iterator, Sequence

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter
from engine.files import fresh, write_text as save_text

try:  # imported as engine.table
    from engine import timeline as tl
except ImportError:  # run with engine/ on sys.path
    import timeline as tl

Image.MAX_IMAGE_PIXELS = None

ROOT = Path(__file__).resolve().parents[1]
TOKENS_PATH = ROOT / "engine" / "tokens.json"

SS = 3                      # supersampling for strokes and the loupe
SHEET_PAD = 2               # transparent, colour-extended margin around every master (px)
BEZEL_OUTER, BEZEL_FRAME, BEZEL_LINE = 14, 3, 1.5
BEZEL_INSET = int(BEZEL_OUTER + BEZEL_FRAME + BEZEL_LINE + 1)
GRAIN_SIGMA = 1.35          # diffuser grain, 8-bit levels
GRAIN_SEED = 7
REG_INSET, REG_LEN = 84, 40  # registration corner ticks
LOUPE_RIM, LOUPE_GLOW = 16, 34
LOUPE_SHADOW_OFFSET = (16, 26)
LEADER_WIDTH = 2.0
MARK_WIDTH = 2.6
VISIBLE = 0.02              # opacity above which something counts as "on screen"


# --------------------------------------------------------------------------- basics
@lru_cache(maxsize=1)
def tokens() -> dict:
    return json.loads(TOKENS_PATH.read_text(encoding="utf-8"))


def _rgb(hex_colour: str) -> tuple[int, int, int]:
    h = hex_colour.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def accent_colour(accent: str | None) -> tuple[int, int, int]:
    """Accent from tokens (current option) unless a name or hex string is given."""
    acc = tokens()["accent"]
    if accent is None:
        return _rgb(acc["options"][acc["current"]])
    if accent in acc["options"]:
        return _rgb(acc["options"][accent])
    return _rgb(accent if accent.startswith("#") else "#" + accent)


def _frame_size() -> tuple[int, int]:
    f = tokens()["frame"]
    return int(f["width"]), int(f["height"])


def _opacity_lut(opacity: float) -> list[int]:
    return [int(round(i * opacity)) for i in range(256)]


def _fade(t: float, spec: dict | None, narration: dict) -> float:
    """1 before a fade-out and after a fade-in; here: eased 0..1 ramp for {"at","dur"}."""
    if not spec:
        return 0.0
    t0 = tl.resolve(spec["at"], narration)
    return tl.ease_in_out(tl.ramp(t, t0, t0 + float(spec.get("dur", 0.4))))


# --------------------------------------------------------------------------- type
@dataclass(frozen=True)
class Style:
    name: str
    path: str
    size: int
    line: int
    tracking: float  # px per character

    @property
    def font(self) -> ImageFont.FreeTypeFont:
        return _font(self.path, self.size)


@lru_cache(maxsize=64)
def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def style(name: str, weight: str | None = None) -> Style:
    tk = tokens()["type"]
    sc = tk["scale"][name]
    fam = tk["families"][sc["family"]]
    path = str(ROOT / fam[weight or sc["weight"]])
    return Style(name, path, int(sc["size"]), int(sc["line"]), float(sc["tracking"]) * sc["size"])


def measure(text: str, st: Style) -> float:
    return st.font.getlength(text) + st.tracking * max(0, len(text) - 1)


def wrap(text: str, st: Style, max_w: float) -> list[str]:
    lines: list[str] = []
    cur = ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if measure(trial, st) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    lines.append(cur)
    return lines


def baseline(top: float, st: Style) -> float:
    """Baseline y of a line whose line box starts at ``top``."""
    asc, desc = st.font.getmetrics()
    return top + (st.line - (asc + desc)) / 2 + asc


def draw_text(d: ImageDraw.ImageDraw, x: float, top: float, text: str, st: Style, fill) -> None:
    base = baseline(top, st)
    if abs(st.tracking) < 0.01:
        d.text((x, base), text, font=st.font, fill=fill, anchor="ls")
        return
    for i, ch in enumerate(text):
        if ch != " ":
            d.text((x + st.font.getlength(text[:i]) + st.tracking * i, base), ch,
                   font=st.font, fill=fill, anchor="ls")


Box = tuple[float, float, float, float]


def ink_box(x: float, top: float, text: str, st: Style) -> Box:
    base = baseline(top, st)
    l, t, r, b = st.font.getbbox(text, anchor="ls")
    return (x + l, base + t, x + max(r, measure(text, st)), base + b)


def _shift(box: Box, dx: float, dy: float) -> Box:
    return (box[0] + dx, box[1] + dy, box[2] + dx, box[3] + dy)


def _union(boxes: Sequence[Box]) -> Box:
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def _boxes_overlap(a: Box, b: Box, gap: float = 0.0) -> bool:
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


# --------------------------------------------------------------------------- sprites
@dataclass
class Sprite:
    """A pre-rendered straight-alpha element placed at a fixed screen position."""
    rgb: Image.Image
    alpha: Image.Image
    x: int
    y: int

    @property
    def size(self) -> tuple[int, int]:
        return self.rgb.size

    def blit(self, base: Image.Image, opacity: float = 1.0, dx: float = 0, dy: float = 0) -> None:
        if opacity <= 0.001:
            return
        a = self.alpha if opacity >= 0.999 else self.alpha.point(_opacity_lut(opacity))
        base.paste(self.rgb, (int(round(self.x + dx)), int(round(self.y + dy))), a)


def rounded_mask(size: tuple[int, int], radius: float, opacity: float = 1.0) -> Image.Image:
    w, h = size
    m = Image.new("L", (w * 4, h * 4), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * 4 - 1, h * 4 - 1], radius * 4, fill=255)
    m = m.resize((w, h), Image.LANCZOS)
    return m if opacity >= 1 else m.point(_opacity_lut(opacity))


def stroke_mask(points: np.ndarray, width: float, bounds: tuple[int, int]):
    """Supersampled round-capped polyline.  Returns (x0, y0, L mask) or None."""
    if len(points) == 0:
        return None
    pad = width + 3
    x0 = max(0, int(math.floor(points[:, 0].min() - pad)))
    y0 = max(0, int(math.floor(points[:, 1].min() - pad)))
    x1 = min(bounds[0], int(math.ceil(points[:, 0].max() + pad)))
    y1 = min(bounds[1], int(math.ceil(points[:, 1].max() + pad)))
    if x1 <= x0 or y1 <= y0:
        return None
    big = Image.new("L", ((x1 - x0) * SS, (y1 - y0) * SS), 0)
    d = ImageDraw.Draw(big)
    pts = [((px - x0) * SS, (py - y0) * SS) for px, py in points]
    if len(pts) > 1:
        d.line(pts, fill=255, width=max(1, int(round(width * SS))), joint="curve")
    r = width * SS / 2
    for p in (pts[0], pts[-1]):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=255)
    return x0, y0, big.resize((x1 - x0, y1 - y0), Image.LANCZOS)


def draw_stroke(canvas: Image.Image, points: np.ndarray, width: float, colour, opacity: float = 1.0) -> None:
    res = stroke_mask(points, width, canvas.size)
    if res is None or opacity <= 0.001:
        return
    x0, y0, m = res
    if opacity < 0.999:
        m = m.point(_opacity_lut(opacity))
    canvas.paste(colour, (x0, y0, x0 + m.width, y0 + m.height), m)


# --------------------------------------------------------------------------- layers
@dataclass
class Layer:
    """A raster placed on the table: layer px ``pivot`` sits at table point ``p0``, turned by ``theta``."""
    im: Image.Image
    res: float                      # layer px per table px
    pivot: tuple[float, float]
    p0: tuple[float, float]
    theta: float = 0.0              # radians, counter-clockwise on screen


def _rot(theta: float) -> np.ndarray:
    """Screen rotation, counter-clockwise for positive theta (y points down)."""
    c, s = math.cos(theta), math.sin(theta)
    return np.array([[c, s], [-s, c]])


def _layer_affine(layer: Layer, t0, px0, vs: float, origin) -> tuple[float, ...]:
    ri = _rot(layer.theta).T
    scale = layer.res / vs
    base = (np.array(layer.pivot) + layer.res * (ri @ (np.array(t0) - np.array(layer.p0)))
            + scale * (ri @ (np.array(origin, float) - np.array(px0))))
    m = scale * ri
    return (m[0, 0], m[0, 1], base[0], m[1, 0], m[1, 1], base[1])


def render_layer(layer: Layer, t0, px0, vs: float, bounds: tuple[int, int]):
    """Resample ``layer`` into a view where table point t0 sits at target px0 with scale vs.

    Only the screen bounding box of the layer is computed.  Returns (x, y, image) or None."""
    w, h = layer.im.size
    corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], float)
    table = np.array(layer.p0) + ((corners - np.array(layer.pivot)) / layer.res) @ _rot(layer.theta).T
    scr = np.array(px0) + (table - np.array(t0)) * vs
    x0, y0 = max(0, int(math.floor(scr[:, 0].min()))), max(0, int(math.floor(scr[:, 1].min())))
    x1, y1 = min(bounds[0], int(math.ceil(scr[:, 0].max()))), min(bounds[1], int(math.ceil(scr[:, 1].max())))
    if x1 <= x0 or y1 <= y0:
        return None
    coeffs = _layer_affine(layer, t0, px0, vs, (x0, y0))
    return x0, y0, layer.im.transform((x1 - x0, y1 - y0), Image.AFFINE, coeffs, Image.BICUBIC)


def paste_layer(canvas: Image.Image, layer: Layer, t0, px0, vs: float) -> None:
    res = render_layer(layer, t0, px0, vs, canvas.size)
    if res is not None:
        x, y, im = res
        canvas.paste(im, (x, y), im)


# --------------------------------------------------------------------------- scene data
@dataclass
class ObjectLayer:
    id: str
    centre: np.ndarray
    theta: float
    k: float                       # table px per scan px
    crop: tuple[int, int, int, int]
    w: float
    h: float
    z: int
    sheet: Layer
    lens_sheet: Layer
    aura: Layer

    def to_table(self, scan_pts: np.ndarray) -> np.ndarray:
        cx0, cy0, cx1, cy1 = self.crop
        local = (np.asarray(scan_pts, float) - [(cx0 + cx1) / 2, (cy0 + cy1) / 2]) * self.k
        return self.centre + local @ _rot(self.theta).T

    def quad(self) -> np.ndarray:
        loc = np.array([[-self.w / 2, -self.h / 2], [self.w / 2, -self.h / 2],
                        [self.w / 2, self.h / 2], [-self.w / 2, self.h / 2]])
        return self.centre + loc @ _rot(self.theta).T


@dataclass
class Mark:
    id: str
    kind: str
    obj: ObjectLayer
    pts: np.ndarray                # polyline in table px
    cum: np.ndarray
    t0: float
    dur: float
    fade_at: float | None
    fade_dur: float
    width: float


@dataclass
class Stop:
    point: np.ndarray
    depart: float
    arrive: float
    control: np.ndarray
    start: np.ndarray


@dataclass
class LoupeSpec:
    radius: int
    mag: float
    stops: list[Stop]
    enter: np.ndarray
    fade_in: tuple[float, float]
    fade_out: tuple[float, float]
    ext: tuple[float, float, float, float]       # left, top, right, bottom extents from the centre
    shadow: Sprite
    ring: Sprite
    over: Sprite
    tag: Sprite
    tag_offset: tuple[int, int]
    lens_mask: Image.Image
    lens_vig: Image.Image
    centre_off: int                # sprite half-size M


@dataclass
class PlateSpec:
    sprite: Sprite
    panel: Box
    children: list[tuple[str, Box]]
    t0: float
    dur: float
    rise: float
    leader: dict | None
    leader_t0: float
    leader_dur: float


@dataclass
class TimedSprite:
    sprite: Sprite
    box: Box
    t0: float
    t1: float
    fade: float
    sentence: str = ""


@dataclass
class Scene:
    film: dict
    narration: dict
    accent: tuple[int, int, int]
    fps: int
    nframes: int
    duration: float
    under: Image.Image
    bezel: Sprite
    objects: list[ObjectLayer]
    marks: list[Mark]
    loupe: LoupeSpec | None
    plate: PlateSpec | None
    hook: Sprite
    hook_boxes: list[Box]
    subs: list[TimedSprite]
    credit: TimedSprite | None
    cam_scale: tuple[float, float]
    cam_focus: tuple[float, float]
    cam_moves: list[tuple[float, float, tuple[float, float]]]
    text_sizes: list[tuple[str, int, int]] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- table surface
def _smooth(u):
    u = np.clip(u, 0, 1)
    return u * u * (3 - 2 * u)


def build_under() -> Image.Image:
    """Backlit diffuser: even cool-white glow, gentle falloff, fine static grain, registration ticks."""
    W, H = _frame_size()
    tk = tokens()["table"]
    glow, surf, edge = (np.array(_rgb(tk[k]), np.float32) for k in ("surface_glow", "surface", "surface_edge"))
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d2 = ((x - W * 0.5) / (W * 0.72)) ** 2 + ((y - H * 0.47) / (H * 0.62)) ** 2
    u = np.clip(d2 / 1.35, 0, 1)
    a = _smooth(u / 0.55)[..., None]
    b = _smooth((u - 0.55) / 0.45)[..., None]
    col = (glow + (surf - glow) * a)
    col = col + (edge - col) * b
    rng = np.random.default_rng(GRAIN_SEED)
    grain = gaussian_filter(rng.standard_normal((H, W)).astype(np.float32), 0.55)
    grain *= GRAIN_SIGMA / grain.std()
    img = np.clip(col + grain[..., None], 0, 255)
    under = Image.fromarray(np.rint(img).astype(np.uint8), "RGB")
    return _draw_registration(under, _rgb(tk["registration"]))


def _draw_registration(under: Image.Image, colour) -> Image.Image:
    W, H = under.size
    big = Image.new("L", (W * SS, H * SS), 0)
    d = ImageDraw.Draw(big)
    w = int(round(1.5 * SS))
    i, n = REG_INSET, REG_LEN
    for cx, sx in ((i, 1), (W - i, -1)):
        for cy, sy in ((i, 1), (H - i, -1)):
            d.line([(cx * SS, cy * SS), ((cx + sx * n) * SS, cy * SS)], fill=255, width=w)
            d.line([(cx * SS, cy * SS), (cx * SS, (cy + sy * n) * SS)], fill=255, width=w)
    t = 18
    for (px, py, dx, dy) in ((W // 2, i, 0, 1), (W // 2, H - i, 0, -1), (i, H // 2, 1, 0), (W - i, H // 2, -1, 0)):
        d.line([(px * SS, py * SS), ((px + dx * t) * SS, (py + dy * t) * SS)], fill=255, width=w)
    mask = big.resize((W, H), Image.LANCZOS).point(_opacity_lut(0.85))
    under.paste(colour, (0, 0, W, H), mask)
    return under


def build_bezel() -> Sprite:
    """Screen-fixed dark frame with a thin catch-light and a soft inner shadow."""
    W, H = _frame_size()
    tk = tokens()["table"]
    rgb = Image.new("RGB", (W, H), _rgb(tk["surround"]))
    alpha = Image.new("L", (W, H), 255)
    ad = ImageDraw.Draw(alpha)
    d = ImageDraw.Draw(rgb)
    o, f = BEZEL_OUTER, BEZEL_FRAME
    d.rectangle([o, o, W - o - 1, H - o - 1], fill=_rgb(tk["frame"]))
    d.rectangle([o + f, o + f, W - o - f - 1, H - o - f - 1], outline=_rgb(tk["surface_edge"]), width=2)
    inner = o + f + 2
    ad.rectangle([inner, inner, W - inner - 1, H - inner - 1], fill=0)
    # soft inner shadow, fading quickly from the frame
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    dist = np.minimum(np.minimum(x, W - 1 - x), np.minimum(y, H - 1 - y)) - inner
    shade = np.clip(1 - dist / 26.0, 0, 1) ** 2 * 0.20
    a = np.asarray(alpha, np.float32) / 255
    out_a = np.maximum(a, shade)
    colour = np.array(_rgb(tk["surround"]), np.float32)
    rgb_arr = np.asarray(rgb, np.float32)
    keep = np.where(a[..., None] > 0.5, rgb_arr, colour)
    return Sprite(Image.fromarray(keep.astype(np.uint8)), Image.fromarray(np.rint(out_a * 255).astype(np.uint8)), 0, 0)


# --------------------------------------------------------------------------- scans
def _open_scan(spec: str) -> Image.Image:
    if "!" in spec:
        zpath, member = spec.split("!", 1)
        zpath = zpath if Path(zpath).is_absolute() else str(ROOT / zpath)
        with zipfile.ZipFile(zpath) as z:
            im = Image.open(io.BytesIO(z.read(member)))
            im.load()
    else:
        p = Path(spec)
        im = Image.open(p if p.is_absolute() else ROOT / p)
        im.load()
    return im.convert("RGB")


def _levels_lut(levels: dict | None) -> list[int]:
    lv = {"black": 0.0, "gain": 1.06, "lift": 6.0}
    lv.update(levels or {})
    return [int(min(255, max(0, round((i - lv["black"]) * lv["gain"] + lv["lift"])))) for i in range(256)]


def _master(im: Image.Image, width: int, height: int, lut: list[int]) -> Image.Image:
    """Resize the original-resolution crop with LANCZOS, apply the uniform levels, pad for clean edges."""
    m = im.resize((width, height), Image.LANCZOS).point(lut * 3)
    a = np.pad(np.asarray(m), ((SHEET_PAD, SHEET_PAD), (SHEET_PAD, SHEET_PAD), (0, 0)), mode="edge")
    alpha = np.zeros(a.shape[:2], np.uint8)
    alpha[SHEET_PAD:-SHEET_PAD, SHEET_PAD:-SHEET_PAD] = 255
    return Image.fromarray(np.dstack([a, alpha]), "RGBA")


def _polygon_mask(poly: np.ndarray, size: tuple[int, int], origin) -> np.ndarray:
    big = Image.new("L", (size[0] * 4, size[1] * 4), 0)
    pts = [((x - origin[0]) * 4, (y - origin[1]) * 4) for x, y in poly]
    ImageDraw.Draw(big).polygon(pts, fill=255)
    return np.asarray(big.resize(size, Image.LANCZOS), np.float32) / 255


def build_aura(quad: np.ndarray) -> Layer:
    """Soft contact shadows, a slightly lifted edge and a faint warm rim, as one RGBA layer under a sheet."""
    margin = 72
    x0, y0 = int(math.floor(quad[:, 0].min())) - margin, int(math.floor(quad[:, 1].min())) - margin
    x1, y1 = int(math.ceil(quad[:, 0].max())) + margin, int(math.ceil(quad[:, 1].max())) + margin
    size = (x1 - x0, y1 - y0)
    m = _polygon_mask(quad, size, (x0, y0))

    def shifted(arr: np.ndarray, dx: int, dy: int) -> np.ndarray:
        return np.roll(np.roll(arr, dy, 0), dx, 1)

    wide = np.clip(gaussian_filter(shifted(m, 9, 15), 11), 0, 1) * 0.30
    lift = np.clip(gaussian_filter(shifted(m, 2, 3), 2.0), 0, 1) * 0.30
    sa = 1 - (1 - wide) * (1 - lift)
    warm1 = np.clip(gaussian_filter(m, 1.0) - m, 0, 1) * 0.80
    warm2 = np.clip(gaussian_filter(m, 5.0) - m, 0, 1) * 0.16
    wa = 1 - (1 - warm1) * (1 - warm2)
    shadow_c = np.array([16, 22, 30], np.float32)
    warm_c = np.array([255, 226, 184], np.float32)
    out_a = wa + sa * (1 - wa)
    safe = np.maximum(out_a, 1e-6)[..., None]
    rgb = (warm_c * wa[..., None] + shadow_c * (sa * (1 - wa))[..., None]) / safe
    rgb = np.where(out_a[..., None] > 1e-4, rgb, shadow_c)
    im = Image.fromarray(np.dstack([np.rint(rgb), np.rint(out_a * 255)]).astype(np.uint8), "RGBA")
    return Layer(im, 1.0, (0.0, 0.0), (float(x0), float(y0)), 0.0)


def build_object(spec: dict, mag: float, smax: float, lut: list[int]) -> ObjectLayer:
    im = _open_scan(spec["scan"])
    rot = int(spec.get("rotate", 0)) % 360
    if rot:
        im = im.transpose({90: Image.ROTATE_90, 180: Image.ROTATE_180, 270: Image.ROTATE_270}[rot])
    crop = tuple(int(v) for v in spec.get("crop", (0, 0, im.width, im.height)))
    im = im.crop(crop)
    cw, ch = im.size
    w = float(spec["width"])
    k = w / cw
    h = ch * k
    theta = math.radians(float(spec.get("tilt", 0.0)))
    centre = np.array(spec["centre"], float)
    pivot_for = lambda wm, hm: (SHEET_PAD + wm / 2, SHEET_PAD + hm / 2)

    def make(res: float) -> Layer:
        wm, hm = max(2, int(round(w * res))), max(2, int(round(h * res)))
        return Layer(_master(im, wm, hm, lut), wm / w, pivot_for(wm, hm), (centre[0], centre[1]), theta)

    obj = ObjectLayer(spec["id"], centre, theta, k, crop, w, h, int(spec.get("z", 0)),
                      make(smax), make(smax * mag), None)  # type: ignore[arg-type]
    obj.aura = build_aura(obj.quad())
    return obj


# --------------------------------------------------------------------------- marks
def _ellipse_pts(box, n=260) -> np.ndarray:
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    ax, ay = (box[2] - box[0]) / 2, (box[3] - box[1]) / 2
    a = -math.pi / 2 + 2 * math.pi * np.linspace(0, 1, n)
    return np.stack([cx + ax * np.cos(a), cy + ay * np.sin(a)], 1)


def _rect_pts(box, per_side=70) -> np.ndarray:
    x0, y0, x1, y1 = box
    c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    parts = [np.linspace(c[i], c[i + 1], per_side, endpoint=False) for i in range(4)]
    return np.vstack(parts + [np.array([c[0]])])


def build_mark(spec: dict, objs: dict[str, ObjectLayer], narration: dict) -> Mark:
    obj = objs[spec["object"]]
    kind = spec["type"]
    cx0, cy0, cx1, cy1 = obj.crop
    margin_scan = 14 / obj.k
    if kind == "ring-around-object":
        box = spec.get("box") or (cx0 - margin_scan, cy0 - margin_scan, cx1 + margin_scan, cy1 + margin_scan)
        pts = _rect_pts(box)
    elif kind == "box":
        pts = _rect_pts(spec["box"])
    elif kind == "ellipse":
        pts = _ellipse_pts(spec["box"])
    elif kind == "underline":
        b = spec["box"]
        pts = np.linspace((b[0], b[3]), (b[2], b[3]), 80)
    else:
        raise ValueError(f"unknown mark type {kind!r}")
    table = obj.to_table(pts)
    cum = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(table, axis=0).T))])
    fade = spec.get("fade")
    return Mark(spec.get("id", kind), kind, obj, table, cum, tl.resolve(spec["draw"], narration),
                float(spec.get("dur", 0.9)), tl.resolve(fade["at"], narration) if fade else None,
                float(fade.get("dur", 0.4)) if fade else 0.0, float(spec.get("width", MARK_WIDTH)))


def mark_state(m: Mark, t: float) -> tuple[float, float]:
    """(draw progress 0..1, opacity)."""
    p = tl.ease_in_out(tl.ramp(t, m.t0, m.t0 + m.dur))
    a = 1.0
    if m.fade_at is not None:
        a = 1 - tl.ease_in_out(tl.ramp(t, m.fade_at, m.fade_at + m.fade_dur))
    return p, a


def cut_polyline(m: Mark, p: float) -> np.ndarray:
    target = p * m.cum[-1]
    i = int(np.searchsorted(m.cum, target, side="right"))
    if i >= len(m.pts):
        return m.pts
    seg = m.cum[i] - m.cum[i - 1]
    f = (target - m.cum[i - 1]) / seg if seg > 0 else 0.0
    end = m.pts[i - 1] + (m.pts[i] - m.pts[i - 1]) * f
    return np.vstack([m.pts[:i], end])


# --------------------------------------------------------------------------- loupe
def _loupe_geometry(R: int, tag_w: int, tag_h: int):
    tag_dx = tag_dy = int(round((R + LOUPE_RIM + 6) * 0.7071))
    tag_box = (tag_dx, -tag_dy - tag_h, tag_dx + tag_w, -tag_dy)
    ext = (R + LOUPE_GLOW, max(R + LOUPE_GLOW, -tag_box[1]), max(R + LOUPE_GLOW, tag_box[2]), R + LOUPE_GLOW)
    return tag_box, ext


def build_loupe(spec: dict, narration: dict, objs: dict[str, ObjectLayer]) -> LoupeSpec:
    tk = tokens()["table"]
    R = int(spec["radius"])
    mag = float(spec["magnification"])
    M = R + 100
    n = 2 * M * SS
    c = M * SS
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    dx, dy = xx + 0.5 - c, yy + 0.5 - c
    r = np.hypot(dx, dy) / SS
    ang = np.arctan2(dy, dx)
    lit = 0.5 + 0.5 * np.cos(ang - math.atan2(-1, -1))           # light from the upper left
    rim_c, bevel_c = np.array(_rgb(tk["loupe_rim"]), np.float32), np.array(_rgb(tk["loupe_rim_light"]), np.float32)

    def over(base, base_a, col, a):
        out_a = a + base_a * (1 - a)
        pre = col * a[..., None] + base * (base_a * (1 - a))[..., None]
        return pre, out_a

    pre = np.zeros((n, n, 3), np.float32)
    alp = np.zeros((n, n), np.float32)
    # glow, then dark rim, then bevels
    g = np.clip(1 - (r - R - LOUPE_RIM) / (LOUPE_GLOW - LOUPE_RIM), 0, 1) ** 2 * 0.34 * (r > R + LOUPE_RIM - 1)
    pre, alp = over(pre, alp, np.array([236, 243, 249], np.float32), g.astype(np.float32))
    rim_a = ((r >= R - 2) & (r <= R + LOUPE_RIM)).astype(np.float32)
    rim_col = rim_c + (18 * lit)[..., None] + (14 * (1 - np.clip((r - R) / LOUPE_RIM, 0, 1)))[..., None]
    pre, alp = over(pre, alp, rim_col, rim_a) if rim_col.ndim == 3 else (pre, alp)
    outer = ((r >= R + LOUPE_RIM - 2.4) & (r <= R + LOUPE_RIM)).astype(np.float32) * (0.18 + 0.82 * lit ** 1.6)
    pre, alp = over(pre, alp, bevel_c, outer.astype(np.float32))
    inner = ((r >= R - 0.6) & (r <= R + 1.8)).astype(np.float32) * (0.10 + 0.55 * (1 - lit) ** 1.4)
    pre, alp = over(pre, alp, bevel_c, inner.astype(np.float32))
    # highlight arc on the glass (over the lens)
    delta = np.abs((ang - math.atan2(-1, -1) + math.pi) % (2 * math.pi) - math.pi)
    taper = np.clip(1 - delta / math.radians(52), 0, 1) ** 2
    prof = np.exp(-((r - (R - 13)) ** 2) / (2 * 3.4 ** 2))
    arc = (taper * prof * 0.55).astype(np.float32)

    def down(a: np.ndarray) -> np.ndarray:
        return a.reshape(2 * M, SS, 2 * M, SS, *a.shape[2:]).mean((1, 3))

    def sprite_from(pre_c: np.ndarray, a: np.ndarray, flat=None) -> Sprite:
        a1, p1 = down(a), down(pre_c)
        rgb = p1 / np.maximum(a1, 1e-5)[..., None]
        return Sprite(Image.fromarray(np.clip(np.rint(rgb), 0, 255).astype(np.uint8)),
                      Image.fromarray(np.clip(np.rint(a1 * 255), 0, 255).astype(np.uint8)), 0, 0)

    ring = sprite_from(pre, alp)
    white = np.ones((n, n, 3), np.float32) * 255
    over_sprite = sprite_from(white * arc[..., None], arc)

    # soft shadow on the table
    disc = (r <= R + 4).astype(np.float32)
    disc1 = down(disc)
    sh = np.roll(np.roll(disc1, LOUPE_SHADOW_OFFSET[1], 0), LOUPE_SHADOW_OFFSET[0], 1)
    sh = np.clip(gaussian_filter(sh, 22), 0, 1) * 0.42
    shadow = Sprite(Image.new("RGB", (2 * M, 2 * M), (14, 20, 28)),
                    Image.fromarray(np.rint(sh * 255).astype(np.uint8)), 0, 0)

    # lens mask (3x supersampled) and inner vignette
    mask_big = Image.new("L", (2 * R * SS, 2 * R * SS), 0)
    ImageDraw.Draw(mask_big).ellipse([0, 0, 2 * R * SS - 1, 2 * R * SS - 1], fill=255)
    lens_mask = mask_big.resize((2 * R, 2 * R), Image.LANCZOS)
    y2, x2 = np.mgrid[0:2 * R, 0:2 * R].astype(np.float32)
    rr = np.hypot(x2 + 0.5 - R, y2 + 0.5 - R) / R
    vig = 1 - 0.10 * rr ** 3 - 0.10 * np.clip((rr - 0.93) / 0.07, 0, 1)
    lens_vig = Image.fromarray(np.repeat(np.clip(vig * 255, 0, 255)[..., None], 3, 2).astype(np.uint8))

    # magnification tag
    st = style("mono_small", "bold")
    text = f"{mag:g}x"
    pad_x, pad_y = 14, 7
    tw = int(math.ceil(measure(text, st))) + 2 * pad_x
    th = st.line + 2 * pad_y - 6
    tag_box, ext = _loupe_geometry(R, tw, th)
    tag_rgb = Image.new("RGB", (tw, th), _rgb(tk["loupe_rim"]))
    td = ImageDraw.Draw(tag_rgb)
    td.rounded_rectangle([0, 0, tw - 1, th - 1], 8, outline=_rgb(tk["loupe_rim_light"]), width=2)
    draw_text(td, pad_x, (th - st.line) / 2, text, st, _rgb(tk["plate_text"]))
    tag = Sprite(tag_rgb, rounded_mask((tw, th), 8), 0, 0)

    f_in, f_out = spec["fade_in"], spec["fade_out"]
    stops: list[Stop] = []
    prev = None
    for i, s in enumerate(spec["stops"]):
        obj = objs[s["object"]]
        p = obj.to_table(np.array([s["at"]], float))[0]
        arrive = tl.resolve(s["arrive"], narration)
        if prev is None:
            prev = np.array(spec["enter"], float) if "enter" in spec else p + np.array([-170.0, 150.0])
        chord = p - prev
        length = float(np.hypot(*chord)) or 1.0
        normal = np.array([-chord[1], chord[0]]) / length
        bulge = float(s.get("bulge", 0.2)) * (1 if i % 2 == 0 else -1)
        control = (prev + p) / 2 + normal * bulge * length
        stops.append(Stop(p, arrive - float(s["travel"]), arrive, control, prev.copy()))
        prev = p
    enter = stops[0].start
    return LoupeSpec(R, mag, stops, enter,
                     (tl.resolve(f_in["at"], narration), float(f_in.get("dur", 0.4))),
                     (tl.resolve(f_out["at"], narration), float(f_out.get("dur", 0.7))),
                     (ext[0], ext[1], ext[2], ext[3]), shadow, ring, over_sprite, tag,
                     (int(tag_box[0]), int(tag_box[1])), lens_mask, lens_vig, M)


@dataclass
class LoupeState:
    centre: tuple[float, float]       # screen, after keep-in clamp
    raw: tuple[float, float]          # screen, before clamp
    table: np.ndarray                 # table point under the centre
    opacity: float


def loupe_table_point(spec: LoupeSpec, t: float) -> np.ndarray:
    pos = spec.enter
    for st in spec.stops:
        if t < st.depart:
            return pos
        if t < st.arrive:
            u = tl.ease_in_out(tl.ramp(t, st.depart, st.arrive))
            return (1 - u) ** 2 * st.start + 2 * (1 - u) * u * st.control + u * u * st.point
        pos = st.point
    return pos


def loupe_opacity(spec: LoupeSpec, t: float) -> float:
    fi = tl.ease_out(tl.ramp(t, spec.fade_in[0], spec.fade_in[0] + spec.fade_in[1]))
    fo = tl.ease_in_out(tl.ramp(t, spec.fade_out[0], spec.fade_out[0] + spec.fade_out[1]))
    return fi * (1 - fo)


def keep_in_limits(spec: LoupeSpec) -> tuple[float, float, float, float]:
    W, H = _frame_size()
    l, t, r, b = spec.ext
    return BEZEL_INSET + l, BEZEL_INSET + t, W - BEZEL_INSET - r, H - BEZEL_INSET - b


def loupe_state(scene: Scene, t: float, cam: tuple[float, float, float]) -> LoupeState | None:
    sp = scene.loupe
    if sp is None:
        return None
    op = loupe_opacity(sp, t)
    if op <= 0:
        return None
    s, fx, fy = cam
    c = loupe_table_point(sp, t)
    raw = (fx + (c[0] - fx) * s, fy + (c[1] - fy) * s)
    x0, y0, x1, y1 = keep_in_limits(sp)
    cx, cy = min(max(raw[0], x0), x1), min(max(raw[1], y0), y1)
    table = np.array([fx + (cx - fx) / s, fy + (cy - fy) / s])
    return LoupeState((cx, cy), raw, table, op)


def render_lens(scene: Scene, ls: LoupeState, t: float, s: float) -> Image.Image:
    sp = scene.loupe
    R = sp.radius
    vs = sp.mag * s
    size = (2 * R, 2 * R)
    t0, px0 = ls.table, (R, R)
    lens = scene.under.transform(size, Image.AFFINE,
                                 _layer_affine(Layer(scene.under, 1.0, (0.0, 0.0), (0.0, 0.0)), t0, px0, vs, (0, 0)),
                                 Image.BICUBIC)
    reach = R / vs * 1.02
    for obj in sorted(scene.objects, key=lambda o: o.z):
        if _circle_hits_object(obj, ls.table, reach):
            paste_layer(lens, obj.aura, t0, px0, vs)
            paste_layer(lens, obj.lens_sheet, t0, px0, vs)
    for m in scene.marks:
        p, a = mark_state(m, t)
        if p > 0 and a > 0.001:
            pts = px0 + (cut_polyline(m, p) - t0) * vs
            draw_stroke(lens, pts, m.width * vs, scene.accent, a)
    return ImageChops.multiply(lens, sp.lens_vig)


def _circle_hits_object(obj: ObjectLayer, centre: np.ndarray, reach: float) -> bool:
    local = _rot(obj.theta).T @ (centre - obj.centre)
    dx = max(abs(local[0]) - obj.w / 2, 0.0)
    dy = max(abs(local[1]) - obj.h / 2, 0.0)
    return math.hypot(dx, dy) <= reach


def draw_loupe(scene: Scene, img: Image.Image, ls: LoupeState, t: float, s: float) -> None:
    sp = scene.loupe
    R, M, op = sp.radius, sp.centre_off, ls.opacity
    cx, cy = int(round(ls.centre[0])), int(round(ls.centre[1]))
    lens = render_lens(scene, ls, t, s)
    for part in (sp.shadow, sp.ring):
        part.blit(img, op, cx - M - part.x, cy - M - part.y)
    mask = sp.lens_mask if op >= 0.999 else sp.lens_mask.point(_opacity_lut(op))
    img.paste(lens, (cx - R, cy - R), mask)
    sp.over.blit(img, op, cx - M, cy - M)
    sp.tag.blit(img, op, cx + sp.tag_offset[0], cy + sp.tag_offset[1])


# --------------------------------------------------------------------------- camera
def camera_at(scene: Scene, t: float) -> tuple[float, float, float]:
    u = tl.clamp01(t / scene.duration)
    s0, s1 = scene.cam_scale
    s = s0 + (s1 - s0) * (0.25 * u + 0.75 * tl.ease_in_out(u))
    f = np.array(scene.cam_focus, float)
    prev = f.copy()
    for t0, t1, target in scene.cam_moves:
        if t <= t0:
            break
        k = tl.ease_in_out(tl.ramp(t, t0, t1))
        f = prev + (np.array(target, float) - prev) * k
        prev = np.array(target, float)
        if k < 1:
            break
    return s, float(f[0]), float(f[1])


# --------------------------------------------------------------------------- text elements
def build_hook(spec: dict, accent, sizes: list) -> tuple[Sprite, list[Box]]:
    tk = tokens()["table"]
    st = style("hook")
    sizes.append(("hook", st.size, tokens()["type"]["hook_minimum_px"]))
    lines = spec["lines"]
    x, y = int(spec.get("x", tokens()["safe"]["left"])), int(spec.get("y", tokens()["safe"]["top"]))
    wpx = int(max(measure(l, st) for l in lines)) + 12
    h = st.line * len(lines) + 24
    rgb = Image.new("RGB", (wpx, h), _rgb(tk["ink"]))
    mask = Image.new("L", (wpx, h), 0)
    md = ImageDraw.Draw(mask)
    boxes: list[Box] = []
    for i, line in enumerate(lines):
        draw_text(md, 0, i * st.line, line, st, 255)
        boxes.append(_shift(ink_box(0, i * st.line, line, st), x, y))
    bar_y = st.line * len(lines) + 8
    ImageDraw.Draw(rgb).rectangle([0, bar_y, 99, bar_y + 4], fill=accent)
    md.rectangle([0, bar_y, 99, bar_y + 4], fill=255)
    boxes.append((x, y + bar_y, x + 100, y + bar_y + 5))
    return Sprite(rgb, mask, x, y), boxes


def build_subs(narration: dict, sizes: list, problems: list) -> list[TimedSprite]:
    cap = tokens()["captions"]
    tk = tokens()["table"]
    st = style("caption")
    sizes.append(("caption", st.size, tokens()["type"]["caption_minimum_px"]))
    pad_x, pad_y = 24, 14
    out = []
    for s in narration["sentences"]:
        lines = wrap(s["text"], st, cap["max_width"] - 2 * pad_x)
        if len(lines) > cap["max_lines"]:
            problems.append(f"subtitle {s['id']} needs {len(lines)} lines (max {cap['max_lines']})")
        bw = int(math.ceil(max(measure(l, st) for l in lines))) + 2 * pad_x
        bh = st.line * len(lines) + 2 * pad_y
        rgb = Image.new("RGB", (bw, bh), _rgb(tk["subtitle_bg"]))
        d = ImageDraw.Draw(rgb)
        for i, line in enumerate(lines):
            draw_text(d, pad_x, pad_y + i * st.line, line, st, _rgb(tk["subtitle_text"]))
        x, y = cap["x"], cap["bottom"] - bh
        out.append(TimedSprite(Sprite(rgb, rounded_mask((bw, bh), 16, 0.88), x, y), (x, y, x + bw, y + bh),
                               float(s["start_s"]), float(s["end_s"]), float(cap["fade_s"]), s["id"]))
    return out


def sub_alpha(sub: TimedSprite, t: float) -> float:
    return min(tl.ramp(t, sub.t0, sub.t0 + sub.fade), 1 - tl.ramp(t, sub.t1, sub.t1 + sub.fade))


def build_credit(spec: dict, narration: dict, sizes: list) -> TimedSprite:
    tk = tokens()["table"]
    st = style("credit")
    sizes.append(("credit", st.size, tokens()["type"]["minimum_px"]))
    w = int(math.ceil(measure(spec["text"], st))) + 8
    rgb = Image.new("RGB", (w, st.line), _rgb(tk["plate"]))
    mask = Image.new("L", (w, st.line), 0)
    draw_text(ImageDraw.Draw(mask), 0, 0, spec["text"], st, 255)
    x = int(spec.get("x", tokens()["safe"]["left"]))
    y = int(spec["bottom"]) - st.line if "bottom" in spec else int(spec["y"])
    t0 = tl.resolve(spec["at"], narration)
    box = _shift(ink_box(0, 0, spec["text"], st), x, y)
    return TimedSprite(Sprite(rgb, mask, x, y), box, t0, t0 + float(spec.get("dur", 0.6)), 0.0)


def build_plate(spec: dict, narration: dict, accent, sizes: list, problems: list) -> PlateSpec:
    tk = tokens()["table"]
    s_lab, s_read, s_body, s_src = style("eyebrow"), style("plate_title"), style("plate_body"), style("credit")
    for st in (s_lab, s_read, s_body, s_src):
        sizes.append((f"plate {st.name}", st.size, tokens()["type"]["minimum_px"]))
    width = int(spec.get("width", 800))
    bar, padx, pady, gutter = 6, 26, 16, 24
    inner_l, inner_w = bar + padx, width - bar - 2 * padx
    text = spec["text"]
    parts = [text] if isinstance(text, str) else list(text)

    left_w = max(measure(spec["reading"], s_read), measure(spec["label"], s_lab))
    col_w = inner_w - left_w - gutter
    stacked = col_w < 260
    body_w = inner_w if stacked else col_w
    body = [ln for p in parts for ln in wrap(p, s_body, body_w)]
    src = wrap(spec["source"], s_src, inner_w)
    ours = wrap(spec["ours"], s_body, inner_w)

    items: list[tuple[str, str, Style, float, float, object]] = []  # name, text, style, x, top, fill
    y = float(pady)
    items.append(("label", spec["label"], s_lab, inner_l, y, _rgb(tk["plate_secondary"])))
    if stacked:
        y += s_lab.line + 6
        items.append(("reading", spec["reading"], s_read, inner_l, y, _rgb(tk["plate_text"])))
        y += s_read.line + 4
        for i, ln in enumerate(body):
            items.append((f"text{i}", ln, s_body, inner_l, y + i * s_body.line, _rgb(tk["plate_text"])))
        y += len(body) * s_body.line
    else:
        items.append(("reading", spec["reading"], s_read, inner_l, y + s_lab.line + 2, _rgb(tk["plate_text"])))
        row_h = s_lab.line + 2 + s_read.line
        top = y + (row_h - len(body) * s_body.line) / 2
        for i, ln in enumerate(body):
            items.append((f"text{i}", ln, s_body, inner_l + left_w + gutter, top + i * s_body.line, _rgb(tk["plate_text"])))
        y += max(row_h, len(body) * s_body.line)
    y += 12
    rule_y = y
    y += 1 + 10
    for i, ln in enumerate(src):
        items.append((f"source{i}", ln, s_src, inner_l, y + i * s_src.line, _rgb(tk["plate_secondary"])))
    y += len(src) * s_src.line + 4
    for i, ln in enumerate(ours):
        items.append((f"ours{i}", ln, s_body, inner_l, y + i * s_body.line, accent))
    y += len(ours) * s_body.line
    height = int(math.ceil(y + pady))

    rgb = Image.new("RGB", (width, height), _rgb(tk["plate"]))
    d = ImageDraw.Draw(rgb)
    d.rectangle([0, 0, bar - 1, height], fill=accent)
    d.line([inner_l, rule_y, width - padx, rule_y], fill=tuple(int(c * 0.45 + p * 0.55) for c, p in
                                                              zip(_rgb(tk["plate_secondary"]), _rgb(tk["plate"]))), width=1)
    x = int(spec.get("x", tokens()["safe"]["left"]))
    top = int(spec["bottom"]) - height if "bottom" in spec else int(spec["y"])
    children: list[tuple[str, Box]] = []
    for name, txt, st, ix, itop, fill in items:
        draw_text(d, ix, itop, txt, st, fill)
        children.append((name, _shift(ink_box(ix, itop, txt, st), x, top)))
        if ix + measure(txt, st) > width - padx + 1:
            problems.append(f"plate line {name!r} is wider than the plate")
    sprite = Sprite(rgb, rounded_mask((width, height), 14, 0.97), x, top)
    t_in = spec.get("in", {"at": "start", "dur": 0.9})
    leader = spec.get("leader")
    return PlateSpec(sprite, (x, top, x + width, top + height), children, tl.resolve(t_in["at"], narration),
                     float(t_in.get("dur", 0.9)), float(spec.get("rise", 24)), leader,
                     tl.resolve(leader["at"], narration) if leader else 0.0,
                     float(leader.get("dur", 0.6)) if leader else 0.0)


def plate_progress(pl: PlateSpec, t: float) -> float:
    return tl.ease_out(tl.ramp(t, pl.t0, pl.t0 + pl.dur))


# --------------------------------------------------------------------------- build
def _frame_count(narration: dict) -> int:
    return int(narration.get("frames") or round(narration["duration_s"] * narration.get("fps", 30)))


def load(film: dict, narration: dict, *, accent: str | None = None) -> Scene:
    """Open the scans and build every static layer once."""
    fps = int(narration.get("fps", tokens()["frame"]["fps"]))
    duration = float(narration["duration_s"])
    cam = film.get("camera", {})
    scale = tuple(cam.get("scale", (1.0, 1.06)))
    smax = max(scale)
    mag = float(film["loupe"]["magnification"]) if film.get("loupe") else 1.0
    lut = _levels_lut(film.get("levels"))
    acc = accent_colour(accent)
    sizes: list[tuple[str, int, int]] = []
    problems: list[str] = []

    objs = [build_object(o, mag, smax, lut) for o in film["objects"]]
    by_id = {o.id: o for o in objs}
    marks = [build_mark(m, by_id, narration) for m in film.get("marks", [])]
    loupe = build_loupe(film["loupe"], narration, by_id) if film.get("loupe") else None
    if loupe:
        sizes.append(("loupe tag", style("mono_small").size, tokens()["type"]["minimum_px"]))
    plate = build_plate(film["plate"], narration, acc, sizes, problems) if film.get("plate") else None
    hook, hook_boxes = build_hook(film["hook"], acc, sizes)
    subs = build_subs(narration, sizes, problems)
    credit = build_credit(film["credit"], narration, sizes) if film.get("credit") else None
    moves = [(tl.resolve(m["at"], narration), tl.resolve(m["at"], narration) + float(m.get("dur", 2.0)),
              tuple(m["focus"])) for m in cam.get("moves", [])]
    return Scene(film, narration, acc, fps, _frame_count(narration), duration, build_under(), build_bezel(),
                 objs, marks, loupe, plate, hook, hook_boxes, subs, credit, (scale[0], scale[1]),
                 tuple(cam.get("focus", (tokens()["frame"]["width"] / 2, 900))), moves, sizes, problems)


# --------------------------------------------------------------------------- frame
def render_table(scene: Scene, cam: tuple[float, float, float], t: float) -> Image.Image:
    s, fx, fy = cam
    W, H = _frame_size()
    img = scene.under.transform((W, H), Image.AFFINE,
                                _layer_affine(Layer(scene.under, 1.0, (0.0, 0.0), (0.0, 0.0)), (fx, fy), (fx, fy), s, (0, 0)),
                                Image.BICUBIC)
    for obj in sorted(scene.objects, key=lambda o: o.z):
        paste_layer(img, obj.aura, (fx, fy), (fx, fy), s)
        paste_layer(img, obj.sheet, (fx, fy), (fx, fy), s)
    for m in scene.marks:
        p, a = mark_state(m, t)
        if p > 0 and a > 0.001:
            pts = np.array((fx, fy)) + (cut_polyline(m, p) - (fx, fy)) * s
            draw_stroke(img, pts, m.width * s, scene.accent, a)
    return img


def draw_leader(scene: Scene, img: Image.Image, t: float, cam, ls: LoupeState | None) -> None:
    pl = scene.plate
    if pl is None or not pl.leader:
        return
    p = tl.ease_in_out(tl.ramp(t, pl.leader_t0, pl.leader_t0 + pl.leader_dur))
    if p <= 0:
        return
    s, fx, fy = cam
    src = pl.leader["from"]
    if src == "loupe":
        if ls is None:
            return
        start = np.array([ls.centre[0], ls.centre[1] + scene.loupe.radius + LOUPE_RIM])
    else:
        m = next(m for m in scene.marks if m.id == src)
        start = np.array([m.pts[:, 0].mean(), m.pts[:, 1].max() + m.width])
        start = np.array((fx, fy)) + (start - (fx, fy)) * s
    x0, y0, x1, _ = pl.panel
    dy = (1 - plate_progress(pl, t)) * pl.rise
    end = np.array([min(max(start[0], x0 + 40), x1 - 40), y0 + dy])
    tip = start + (end - start) * p
    ink = _rgb(tokens()["table"]["ink"])
    draw_stroke(img, np.array([start, tip]), LEADER_WIDTH, ink)
    if p >= 0.98:
        draw_stroke(img, np.array([tip, tip + 0.01]), 9.0, ink)


def frame(scene: Scene, n: int) -> Image.Image:
    """1080x1920 RGB.  A pure function of the frame number n."""
    t = n / scene.fps
    cam = camera_at(scene, t)
    img = render_table(scene, cam, t)
    scene.bezel.blit(img)
    ls = loupe_state(scene, t, cam)
    if ls is not None:
        draw_loupe(scene, img, ls, t, cam[0])
    draw_leader(scene, img, t, cam, ls)
    if scene.plate is not None:
        pp = plate_progress(scene.plate, t)
        scene.plate.sprite.blit(img, pp, 0, (1 - pp) * scene.plate.rise)
    scene.hook.blit(img)
    for sub in scene.subs:
        sub.sprite.blit(img, sub_alpha(sub, t))
    if scene.credit is not None:
        scene.credit.sprite.blit(img, tl.ease_in_out(tl.ramp(t, scene.credit.t0, scene.credit.t1)))
    return img


# --------------------------------------------------------------------------- validate
def _plate_visible(scene: Scene, t: float) -> float:
    return plate_progress(scene.plate, t) if scene.plate else 0.0


def text_boxes(scene: Scene, t: float, ls: LoupeState | None) -> list[tuple[str, str, Box]]:
    """(group, name, box) for every piece of text on screen at time t."""
    out: list[tuple[str, str, Box]] = [("hook", f"hook{i}", b) for i, b in enumerate(scene.hook_boxes)]
    if scene.plate is not None:
        pp = plate_progress(scene.plate, t)
        if pp > VISIBLE:
            dy = (1 - pp) * scene.plate.rise
            out.append(("plate", "plate", _shift(scene.plate.panel, 0, dy)))
            out += [("plate", f"plate.{n}", _shift(b, 0, dy)) for n, b in scene.plate.children]
    for sub in scene.subs:
        if sub_alpha(sub, t) > VISIBLE:
            out.append((f"subtitle {sub.sentence}", f"subtitle {sub.sentence}", sub.box))
    if scene.credit is not None and tl.ramp(t, scene.credit.t0, scene.credit.t1) > VISIBLE:
        out.append(("credit", "credit", scene.credit.box))
    if ls is not None and ls.opacity > VISIBLE:
        sp = scene.loupe
        tw, th = sp.tag.size
        x, y = ls.centre[0] + sp.tag_offset[0], ls.centre[1] + sp.tag_offset[1]
        out.append(("tag", "loupe tag", (x, y, x + tw, y + th)))
    return out


def _quad_hits_box(quad: np.ndarray, box: Box) -> bool:
    rect = np.array([[box[0], box[1]], [box[2], box[1]], [box[2], box[3]], [box[0], box[3]]])
    axes = [np.array([1.0, 0.0]), np.array([0.0, 1.0])]
    for i in range(4):
        e = quad[(i + 1) % 4] - quad[i]
        axes.append(np.array([-e[1], e[0]]))
    for ax in axes:
        a, b = quad @ ax, rect @ ax
        if a.max() <= b.min() or b.max() <= a.min():
            return False
    return True


def validate(scene: Scene) -> list[str]:
    """Layout problems over the whole film; empty when clean (first offending frame is reported)."""
    W, H = _frame_size()
    safe, ty = tokens()["safe"], tokens()["type"]
    issues: list[str] = list(scene.problems)
    seen: set[str] = set()

    def report(key: str, text: str) -> None:
        if key not in seen:
            seen.add(key)
            issues.append(text)

    for name, size, minimum in scene.text_sizes:
        if size < minimum:
            issues.append(f"text size {name}: {size}px is under the minimum {minimum}px")
    for name, size, minimum in scene.text_sizes:
        if size < ty["minimum_px"]:
            issues.append(f"text size {name}: {size}px is under {ty['minimum_px']}px")
    ids = [o.id for o in scene.objects]
    if len(set(ids)) != len(ids):
        issues.append("duplicate object ids")
    for m in scene.marks:
        if m.t0 + m.dur > scene.duration + 1e-6:
            issues.append(f"mark {m.id} finishes after the film ends")

    for n in range(scene.nframes):
        t = n / scene.fps
        cam = camera_at(scene, t)
        ls = loupe_state(scene, t, cam)
        if ls is not None and ls.opacity > VISIBLE:
            l, tp, r, b = scene.loupe.ext
            x, y = ls.raw
            if x - l < 0 or y - tp < 0 or x + r > W or y + b > H:
                report("loupe-frame",
                       f"loupe (rim, glow, tag) leaves the frame at frame {n} (t={t:.2f}s): extents "
                       f"x {x - l:.0f}..{x + r:.0f}, y {y - tp:.0f}..{y + b:.0f} (frame {W}x{H})")
            lim = keep_in_limits(scene.loupe)
            if not (lim[0] - 0.5 <= x <= lim[2] + 0.5 and lim[1] - 0.5 <= y <= lim[3] + 0.5):
                report("loupe-bezel", f"loupe would touch the frame edge at frame {n} (t={t:.2f}s), centre "
                                       f"({x:.0f}, {y:.0f}); the renderer clamps it, move the stop or the path")
        boxes = text_boxes(scene, t, ls)
        if ls is not None and ls.opacity > VISIBLE:
            R = scene.loupe.radius + LOUPE_RIM
            boxes = boxes + [("loupe rim", "loupe rim", (ls.centre[0] - R, ls.centre[1] - R,
                                                         ls.centre[0] + R, ls.centre[1] + R))]
        groups: dict[str, list[tuple[str, Box]]] = {}
        for g, nm, bx in boxes:
            groups.setdefault(g, []).append((nm, bx))
        # overlaps between groups (plate uses its panel) and between a group's own lines
        whole = {g: (v[0][1] if g == "plate" else _union([b for _, b in v])) for g, v in groups.items()}
        names = [g for g in whole if g != "loupe rim"]
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if _boxes_overlap(whole[a], whole[b]):
                    report(f"ov-{a}-{b}", f"text overlap: {a} and {b} at frame {n} (t={t:.2f}s)")
        for g in ("plate", "hook"):
            items = [(nm, bx) for nm, bx in groups.get(g, []) if nm != "plate"]
            for i, (na, ba) in enumerate(items):
                for nb, bb in items[i + 1:]:
                    if _boxes_overlap(ba, bb):
                        report(f"in-{na}-{nb}", f"text overlap inside {g}: {na} and {nb} at frame {n} (t={t:.2f}s)")
        # safe areas
        for g, v in groups.items():
            bx = whole[g]
            if bx[1] < safe["top"] - 0.5:
                report(f"top-{g}", f"{g} is above y {safe['top']} (y {bx[1]:.0f}) at frame {n}")
            if bx[3] > safe["bottom"] + 0.5:
                report(f"bot-{g}", f"{g} is below y {safe['bottom']} (y {bx[3]:.0f}) at frame {n}")
            if bx[3] > safe["lower_half_from_y"] and bx[2] > safe["lower_half_right"] + 0.5:
                report(f"right-{g}", f"{g} is right of x {safe['lower_half_right']} in the lower half "
                                     f"(x {bx[2]:.0f}) at frame {n} (t={t:.2f}s)")
            if g not in ("loupe rim", "tag") and (bx[0] < safe["left"] - 0.5 or bx[2] > safe["right"] + 0.5):
                report(f"side-{g}", f"{g} is outside x {safe['left']}..{safe['right']} at frame {n}")
        # text sitting on a scan
        s = cam[0]
        for obj in scene.objects:
            quad = np.array(cam[1:]) + (obj.quad() - np.array(cam[1:])) * s
            for g in ("hook", "plate"):
                if g in whole and _quad_hits_box(quad, whole[g]):
                    report(f"scan-{g}-{obj.id}", f"{g} covers scan {obj.id!r} at frame {n} (t={t:.2f}s)")
    return issues


# --------------------------------------------------------------------------- outputs
def _when(film: dict, narration: dict, when) -> int:
    t = tl.resolve(when, narration)
    fps = narration.get("fps", 30)
    return min(max(0, int(round(t * fps))), _frame_count(narration) - 1)


def still(film: dict, narration: dict, when, out_png, *, accent: str | None = None) -> None:
    scene = load(film, narration, accent=accent)
    frame(scene, _when(film, narration, when)).save(fresh(out_png))


_WORKER: Scene | None = None


def _init_worker(film, narration, accent) -> None:
    global _WORKER
    _WORKER = load(film, narration, accent=accent)


def _render_one(n: int) -> np.ndarray:
    return np.array(frame(_WORKER, n))


def frames(film: dict, narration: dict, *, accent: str | None = None, workers: int = 4,
           start: int = 0, stop: int | None = None) -> Iterator[np.ndarray]:
    """Yield numpy uint8 (H, W, 3) frames in order.  Each worker builds its own scene."""
    stop = _frame_count(narration) if stop is None else min(stop, _frame_count(narration))
    if workers <= 1:
        scene = load(film, narration, accent=accent)
        for n in range(start, stop):
            yield np.array(frame(scene, n))
        return
    with mp.get_context("spawn").Pool(workers, _init_worker, (film, narration, accent)) as pool:
        yield from pool.imap(_render_one, range(start, stop), chunksize=2)


def strip(film: dict, narration: dict, out_jpg, *, count: int = 8, accent: str | None = None) -> None:
    scene = load(film, narration, accent=accent)
    picks = [int(round(i)) for i in np.linspace(0, scene.nframes - 1, count)]
    tw, th = 360, 640
    sheet = Image.new("RGB", (tw * count, th))
    for i, n in enumerate(picks):
        sheet.paste(frame(scene, n).resize((tw, th), Image.LANCZOS), (tw * i, 0))
    sheet.save(fresh(out_jpg), quality=88)
