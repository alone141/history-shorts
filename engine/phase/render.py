"""Phase model look: the picture.

A white model of what exists today, on a plate in a dark room, with a projector
painting what is inferred as light. Drawn off-screen with OpenGL (moderngl);
no browser is involved.

`Renderer.picture(frame)` is a pure function of the frame number: nothing is
carried from one frame to the next.
"""
from __future__ import annotations

import math
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from engine.phase import geometry

ROOT = Path(__file__).resolve().parents[2]
FLICKER = [0.9, 0.12, 0.65, 0.05, 0.8, 0.45]       # projector strike, one value per frame
SHADOW_SIZE = 4096
SHADOW_HALF = 46.0
PICK_GLOW = np.array([1.5, 1.45, 1.35])            # a counted stone flashes brighter than white, once

POISSON = [(-0.94201624, -0.39906216), (0.94558609, -0.76890725), (-0.094184101, -0.92938870), (0.34495938, 0.29387760),
           (-0.91588581, 0.45771432), (-0.81544232, -0.87912464), (-0.38277543, 0.27676845), (0.97484398, 0.75648379),
           (0.44323325, -0.97511554), (0.53742981, -0.47373420), (-0.26496911, -0.41893023), (0.79197514, 0.19090188),
           (-0.24188840, 0.99706507), (-0.81409955, 0.91437590), (0.19984126, 0.78641367), (0.14383161, -0.14100790)]

LIT_VS = """
#version 330
uniform mat4 uViewProj;
in vec3 in_pos; in vec3 in_nor; in float in_glow;
out vec3 vWorld; out vec3 vN; out float vGlow;
void main() { vWorld = in_pos; vN = in_nor; vGlow = in_glow; gl_Position = uViewProj * vec4(in_pos, 1.0); }
"""

LIT_FS = """
#version 330
uniform vec3 uCam;
uniform vec3 uAlbedo; uniform float uRough; uniform float uF0; uniform vec3 uEmissive;
uniform vec3 uKeyDir; uniform vec3 uKeyCol; uniform vec3 uRimDir; uniform vec3 uRimCol;
uniform vec3 uFillDir; uniform vec3 uFillCol;
uniform vec3 uSky; uniform vec3 uGround;
uniform vec3 uSpotPos; uniform vec3 uSpotCol; uniform float uSpotCos;
uniform sampler2DShadow uShadow; uniform mat4 uLightVP; uniform float uShadowTexel;
uniform sampler2D uMap; uniform int uUseMap; uniform float uPlateR;
uniform vec2 uPoisson[16]; uniform vec2 uTurn;
in vec3 vWorld; in vec3 vN; in float vGlow;
out vec4 fragColor;
const float PI = 3.14159265;

// eight taps per view, turned by a different angle for each accumulated view, so the
// averaged frame sees a soft edge built from many taps
float shadow(vec3 p, vec3 n) {
    vec4 s = uLightVP * vec4(p + n * 0.07, 1.0);
    vec3 c = s.xyz / s.w * 0.5 + 0.5;
    if (c.x < 0.0 || c.x > 1.0 || c.y < 0.0 || c.y > 1.0 || c.z > 1.0) return 1.0;
    float sum = 0.0;
    for (int i = 0; i < 8; i++) {
        vec2 o = vec2(uPoisson[i].x * uTurn.x - uPoisson[i].y * uTurn.y, uPoisson[i].x * uTurn.y + uPoisson[i].y * uTurn.x);
        sum += texture(uShadow, vec3(c.xy + o * uShadowTexel * 3.0, c.z - 0.0011));
    }
    return sum / 8.0;
}
float specular(vec3 n, vec3 v, vec3 l, float rough, float f0) {
    vec3 h = normalize(v + l);
    float a = rough * rough, a2 = a * a;
    float nh = max(dot(n, h), 0.0), nv = max(dot(n, v), 0.001), nl = max(dot(n, l), 0.0), vh = max(dot(v, h), 0.0);
    float d = a2 / (PI * pow(nh * nh * (a2 - 1.0) + 1.0, 2.0));
    float k = (rough + 1.0) * (rough + 1.0) / 8.0;
    float g = (nv / (nv * (1.0 - k) + k)) * (nl / (nl * (1.0 - k) + k));
    float f = f0 + (1.0 - f0) * pow(1.0 - vh, 5.0);
    return d * g * f / (4.0 * nv * max(nl, 0.001));
}
void main() {
    vec3 n = normalize(vN), v = normalize(uCam - vWorld);
    vec3 albedo = uAlbedo;
    if (uUseMap == 1) {
        vec2 uv = vec2(vWorld.x, -vWorld.z) / uPlateR * 0.5 + 0.5;
        albedo = pow(texture(uMap, uv).rgb, vec3(2.2));
    }
    float sh = shadow(vWorld, n);
    float nl = max(dot(n, uKeyDir), 0.0), nr = max(dot(n, uRimDir), 0.0);
    vec3 toSpot = normalize(uSpotPos - vWorld);
    float cone = smoothstep(uSpotCos, mix(uSpotCos, 1.0, 0.9), toSpot.y);
    vec3 spot = uSpotCol * max(dot(n, toSpot), 0.0) * cone;
    vec3 light = uKeyCol * nl * sh + uRimCol * nr + spot + uFillCol * max(dot(n, uFillDir), 0.0);
    vec3 colour = albedo / PI * (light + mix(uGround, uSky, n.y * 0.5 + 0.5));
    colour += uKeyCol * nl * sh * specular(n, v, uKeyDir, uRough, uF0) + uRimCol * nr * specular(n, v, uRimDir, uRough, uF0);
    fragColor = vec4(colour + uEmissive * vGlow, 1.0);
}
"""

DEPTH_VS = """
#version 330
uniform mat4 uLightVP;
in vec3 in_pos;
void main() { gl_Position = uLightVP * vec4(in_pos, 1.0); }
"""
DEPTH_FS = """
#version 330
void main() {}
"""

# a volume of projected light: brighter at the foot, on the top face and along the silhouette
GLOW_VS = """
#version 330
uniform mat4 uViewProj;
in vec3 in_pos; in vec3 in_nor; in vec2 in_span; in float in_k;
out vec3 vWorld; out vec3 vN; out vec2 vSpan; out float vK;
void main() { vWorld = in_pos; vN = in_nor; vSpan = in_span; vK = in_k; gl_Position = uViewProj * vec4(in_pos, 1.0); }
"""
GLOW_FS = """
#version 330
uniform vec3 uCam; uniform vec3 uColor;
uniform float uClipY; uniform float uBand; uniform float uLead;
in vec3 vWorld; in vec3 vN; in vec2 vSpan; in float vK;
out vec4 fragColor;
void main() {
    if (vWorld.y > uClipY) discard;                 // a volume still rising is drawn only up to its front
    vec3 n = normalize(vN), v = normalize(uCam - vWorld);
    float rim = pow(1.0 - abs(dot(n, v)), 2.0);
    float h = clamp((vWorld.y - vSpan.x) / max(vSpan.y - vSpan.x, 0.001), 0.0, 1.0);
    float topFace = smoothstep(0.6, 0.95, n.y);
    float lead = uLead * smoothstep(uClipY - uBand, uClipY, vWorld.y);
    float a = (mix(0.50, 0.26, h) + 0.95 * rim + 0.42 * topFace + lead) * vK;
    fragColor = vec4(uColor * a, 1.0);
}
"""
FLAT_VS = """
#version 330
uniform mat4 uViewProj;
in vec3 in_pos; in float in_k;
out vec3 vWorld; out float vK;
void main() { vWorld = in_pos; vK = in_k; gl_Position = uViewProj * vec4(in_pos, 1.0); }
"""
FLAT_FS = """
#version 330
uniform vec3 uColor; uniform float uPool; uniform float uPlateR;
in vec3 vWorld; in float vK;
out vec4 fragColor;
void main() {
    float k = vK;
    if (uPool > 0.5) { float r = length(vWorld.xz) / uPlateR; k *= mix(0.55, 0.0, smoothstep(0.0, 1.0, r)) + 0.26 * (1.0 - smoothstep(0.45, 0.75, r)); }
    fragColor = vec4(uColor * k, 1.0);
}
"""

# edges of the light volumes: lines with a real width in pixels and soft sides
LINE_VS = """
#version 330
uniform mat4 uViewProj; uniform vec2 uViewport; uniform float uWidth;
in vec3 in_pos; in vec3 in_other; in float in_side; in float in_k;
out float vK; out float vSide; out float vY;
void main() {
    vY = in_pos.y;
    vec4 p = uViewProj * vec4(in_pos, 1.0), q = uViewProj * vec4(in_other, 1.0);
    vec2 sp = p.xy / p.w * uViewport * 0.5, sq = q.xy / q.w * uViewport * 0.5;
    vec2 d = normalize(sq - sp + vec2(1e-6, 0.0));
    p.xy += vec2(-d.y, d.x) * in_side * uWidth * 0.5 / (uViewport * 0.5) * p.w;
    gl_Position = p; vK = in_k; vSide = in_side;
}
"""
LINE_FS = """
#version 330
uniform vec3 uColor; uniform float uClipY;
in float vK; in float vSide; in float vY;
out vec4 fragColor;
void main() {
    if (vY > uClipY) discard;
    fragColor = vec4(uColor * vK * (1.0 - smoothstep(0.35, 1.0, abs(vSide))), 1.0);
}
"""

QUAD_VS = """
#version 330
in vec2 in_pos;
out vec2 vUv;
void main() { vUv = in_pos * 0.5 + 0.5; gl_Position = vec4(in_pos, 0.0, 1.0); }
"""
ADD_FS = """
#version 330
uniform sampler2D uTex; uniform float uWeight;
in vec2 vUv; out vec4 fragColor;
void main() { fragColor = vec4(texture(uTex, vUv).rgb * uWeight, 1.0); }
"""
BRIGHT_FS = """
#version 330
uniform sampler2D uTex; uniform float uThreshold;
in vec2 vUv; out vec4 fragColor;
void main() { vec3 c = texture(uTex, vUv).rgb; float v = max(c.r, max(c.g, c.b)); fragColor = vec4(c * smoothstep(uThreshold, uThreshold + 0.35, v), 1.0); }
"""
BLUR_FS = """
#version 330
uniform sampler2D uTex; uniform vec2 uStep;
in vec2 vUv; out vec4 fragColor;
void main() {
    vec3 c = texture(uTex, vUv).rgb * 0.227027;
    c += (texture(uTex, vUv + uStep * 1.384615).rgb + texture(uTex, vUv - uStep * 1.384615).rgb) * 0.316216;
    c += (texture(uTex, vUv + uStep * 3.230769).rgb + texture(uTex, vUv - uStep * 3.230769).rgb) * 0.070270;
    fragColor = vec4(c, 1.0);
}
"""
GRADE_FS = """
#version 330
uniform sampler2D uTex; uniform sampler2D uB0; uniform sampler2D uB1; uniform sampler2D uB2; uniform sampler2D uB3; uniform sampler2D uB4;
uniform float uBloom; uniform float uRadius; uniform float uExposure; uniform float uVignette; uniform float uSeed;
in vec2 vUv; out vec4 fragColor;
float hash(vec2 p) { vec3 q = fract(vec3(p.xyx) * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }
vec3 filmic(vec3 x) { x = max(vec3(0.0), x); return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0); }
void main() {
    vec3 bloom = texture(uB0, vUv).rgb * mix(1.0, 0.2, uRadius) + texture(uB1, vUv).rgb * mix(0.8, 0.4, uRadius)
               + texture(uB2, vUv).rgb * 0.6 + texture(uB3, vUv).rgb * mix(0.4, 0.8, uRadius) + texture(uB4, vUv).rgb * mix(0.2, 1.0, uRadius);
    vec3 c = (texture(uTex, vUv).rgb + bloom * uBloom) * uExposure;
    vec2 d = (vUv - vec2(0.5, 0.58)) * vec2(1.0, 1.25);
    c *= 1.0 - uVignette * smoothstep(0.25, 0.95, length(d));
    c = pow(filmic(c), vec3(1.0 / 2.2));
    c += (hash(gl_FragCoord.xy + uSeed * 17.0) - 0.5) * (1.6 / 255.0);
    fragColor = vec4(c, 1.0);
}
"""


# ---------------------------------------------------------------- small maths
def srgb(hex_colour: str) -> np.ndarray:
    """'#RRGGBB' -> linear RGB."""
    value = hex_colour.lstrip("#")
    c = np.array([int(value[i:i + 2], 16) for i in (0, 2, 4)]) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def look_at(eye: np.ndarray, target: np.ndarray, up=(0.0, 1.0, 0.0)) -> np.ndarray:
    f = target - eye
    f = f / np.linalg.norm(f)
    r = np.cross(f, up)
    r = r / np.linalg.norm(r)
    u = np.cross(r, f)
    m = np.eye(4)
    m[0, :3], m[1, :3], m[2, :3] = r, u, -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


def perspective(fov_deg: float, aspect: float, near: float, far: float, shift=(0.0, 0.0)) -> np.ndarray:
    t = 1.0 / math.tan(math.radians(fov_deg) / 2)
    m = np.zeros((4, 4))
    m[0, 0], m[1, 1] = t / aspect, t
    m[2, 2], m[2, 3] = (far + near) / (near - far), 2 * far * near / (near - far)
    m[3, 2] = -1.0
    m[0, 2], m[1, 2] = -shift[0], -shift[1]          # shifts the picture in normalised device units
    return m


def ortho(half: float, near: float, far: float) -> np.ndarray:
    m = np.eye(4)
    m[0, 0] = m[1, 1] = 1.0 / half
    m[2, 2], m[2, 3] = -2.0 / (far - near), -(far + near) / (far - near)
    return m


def bearing_vector(bearing_deg: float, elevation_deg: float) -> np.ndarray:
    b, e = math.radians(bearing_deg), math.radians(elevation_deg)
    return np.array([math.cos(e) * math.sin(b), math.sin(e), -math.cos(e) * math.cos(b)])


def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ramp(t: float, a: float, b: float) -> float:
    return (1.0 if t >= b else 0.0) if b <= a else clamp01((t - a) / (b - a))


def ease_out(u: float) -> float:
    return 1 - (1 - clamp01(u)) ** 3


def ease_in_out(u: float) -> float:
    u = clamp01(u)
    return u * u * (3 - 2 * u)


def keyed(keys: list, t: float) -> float:
    """Piecewise curve through [t, value] keys with eased segments."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys[:-1], keys[1:]):
        if t <= t1:
            return v0 + (v1 - v0) * ease_in_out((t - t0) / (t1 - t0))
    return keys[-1][1]


def spline(keys: list[dict], field: str, t: float) -> float:
    """Catmull-Rom through camera keys: velocity is continuous, so the camera never stops."""
    if t <= keys[0]["t"]:
        return keys[0][field]
    if t >= keys[-1]["t"]:
        return keys[-1][field]
    i = next(i for i in range(1, len(keys)) if keys[i]["t"] >= t)
    k0, k1, k2, k3 = keys[max(0, i - 2)], keys[i - 1], keys[i], keys[min(len(keys) - 1, i + 1)]
    dt = k2["t"] - k1["t"]
    u = (t - k1["t"]) / dt
    m1 = (k2[field] - k0[field]) / max(1e-6, k2["t"] - k0["t"]) * dt
    m2 = (k3[field] - k1[field]) / max(1e-6, k3["t"] - k1["t"]) * dt
    u2, u3 = u * u, u * u * u
    return (2 * u3 - 3 * u2 + 1) * k1[field] + (u3 - 2 * u2 + u) * m1 + (-2 * u3 + 3 * u2) * k2[field] + (u3 - u2) * m2


def pick_schedule(t0: float, t1: float, count: int) -> list[float]:
    """When each counted stone is picked out: almost even, the last one landing on t1."""
    last = max(1, count - 1)
    return [t0 + (t1 - t0) * (0.82 * (i / last) + 0.18 * ease_in_out(i / last)) for i in range(count)]


def halton(i: int, base: int) -> float:
    f, r = 1.0, 0.0
    while i > 0:
        f /= base
        r += f * (i % base)
        i //= base
    return r


# ---------------------------------------------------------------- the renderer
class Renderer:
    def __init__(self, desc: dict, *, accent: str | None = None, samples: int | None = None):
        self.desc = desc
        self.tokens = desc["tokens"]
        self.look = desc["render"]
        self.tl = desc["timeline"]
        self.palette = self.tokens["phase"]
        self.W, self.H = self.tokens["frame"]["width"], self.tokens["frame"]["height"]
        self.fps = desc["narration"]["fps"]
        self.samples = samples or self.look["samples"]
        self.accent = srgb(accent or desc["accent"])
        self.R = desc["model"]["plate"]["radius"]

        self.ctx = moderngl.create_standalone_context()
        self.info = {"gl": self.ctx.info["GL_RENDERER"], "samples": self.samples}
        ctx = self.ctx
        self.lit = ctx.program(vertex_shader=LIT_VS, fragment_shader=LIT_FS)
        self.depth = ctx.program(vertex_shader=DEPTH_VS, fragment_shader=DEPTH_FS)
        self.glow = ctx.program(vertex_shader=GLOW_VS, fragment_shader=GLOW_FS)
        self.flat = ctx.program(vertex_shader=FLAT_VS, fragment_shader=FLAT_FS)
        self.line = ctx.program(vertex_shader=LINE_VS, fragment_shader=LINE_FS)
        self.p_add = ctx.program(vertex_shader=QUAD_VS, fragment_shader=ADD_FS)
        self.p_bright = ctx.program(vertex_shader=QUAD_VS, fragment_shader=BRIGHT_FS)
        self.p_blur = ctx.program(vertex_shader=QUAD_VS, fragment_shader=BLUR_FS)
        self.p_grade = ctx.program(vertex_shader=QUAD_VS, fragment_shader=GRADE_FS)
        quad = ctx.buffer(np.array([-1, -1, 3, -1, -1, 3], dtype="f4").tobytes())
        self.quads = {p: ctx.vertex_array(p, [(quad, "2f", "in_pos")]) for p in (self.p_add, self.p_bright, self.p_blur, self.p_grade)}

        self._build_room()
        self._build_model()
        self._build_targets()
        self._build_lights()
        self._render_shadow_map()

        self.pick_ids = desc["model"]["pick_order"]
        self.pick_times = pick_schedule(self.tl["pick"]["t0"], self.tl["pick"]["t1"], len(self.pick_ids))

    # ---- scene construction
    def _mesh(self, tris: np.ndarray, material: dict, *, casts: bool = True) -> dict:
        buffer = self.ctx.buffer(tris.astype("f4").tobytes())
        glow = self.ctx.buffer(np.zeros(len(tris), dtype="f4").tobytes(), dynamic=True)
        return {
            "vao": self.ctx.vertex_array(self.lit, [(buffer, "3f 3f", "in_pos", "in_nor"), (glow, "1f", "in_glow")]),
            "depth": self.ctx.vertex_array(self.depth, [(buffer, "3f 12x", "in_pos")]) if casts else None,
            "material": material, "glow": glow, "count": len(tris),
        }

    def _build_room(self) -> None:
        p, R = self.palette, self.R
        g = geometry
        self.meshes = [
            self._mesh(g.disc(520, -11.2, 96), {"albedo": srgb(p["floor"]), "rough": 0.62, "f0": 0.04}, casts=False),
            self._mesh(np.vstack([g.cone_wall(R + 1.5, R + 2.3, -1.6, -11.2), g.annulus(R, R + 1.5, -1.6)]),
                       {"albedo": srgb(p["plinth"]), "rough": 0.36, "f0": 0.16}),
            self._mesh(np.vstack([g.cone_wall(R + 1.58, R + 1.58, -1.38, -1.6), g.annulus(R + 0.2, R + 1.58, -1.38)]),
                       {"albedo": srgb(p["plinth_lip"]), "rough": 0.28, "f0": 0.35}),
            self._mesh(g.cone_wall(R, R + 0.25, 0.0, -1.6), {"albedo": srgb(p["plate_edge"]), "rough": 0.75, "f0": 0.04}),
            self._mesh(g.disc(R, 0.0), {"albedo": srgb(p["plate"]), "rough": 0.9, "f0": 0.04, "map": True}, casts=False),
        ]
        self.plate_tex = self._plate_texture()

    def _plate_texture(self) -> moderngl.Texture:
        """The plate's top: a quiet cast surface with an engraved scale bar and north mark."""
        size, R, look = 4096, self.R, self.look
        k = size / (2 * R)
        base = np.array([int(self.palette["plate"].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)
        rng = np.random.default_rng(11)
        mottle = np.zeros((size // 16, size // 16), dtype=np.float32)
        for scale, weight in ((4, 2.2), (16, 1.6), (64, 1.1)):
            coarse = rng.normal(0, 1, (size // 16 // scale + 2, size // 16 // scale + 2)).astype(np.float32)
            layer = np.array(Image.fromarray(coarse).resize((size // 16, size // 16), Image.BICUBIC))
            mottle += layer * weight
        mottle = np.array(Image.fromarray(mottle).resize((size, size), Image.BICUBIC))
        image = Image.fromarray(np.clip(base[None, None, :] + mottle[:, :, None], 0, 255).astype(np.uint8)).convert("RGBA")
        draw = ImageDraw.Draw(image)
        ink = (34, 38, 42, 170)
        mid = size / 2
        rim = (R - 0.7) * k
        draw.ellipse([mid - rim, mid - rim, mid + rim, mid + rim], outline=ink, width=max(2, round(0.06 * k)))
        # the mono face has a marked zero, which closes up when the lettering is small on screen ("100" reads "188")
        family = self.desc["model"]["plate"].get("label_family", "mono")
        font = ImageFont.truetype(str(ROOT / self.tokens["type"]["families"][family]["medium"]), round(1.05 * k))

        def stamp(bearing: float, radius: float, turn: float, paint) -> None:
            """Draw upright in a tile, turn it anticlockwise by `turn` degrees, place it at a compass bearing."""
            tile = Image.new("RGBA", (round(14 * k), round(5 * k)), (0, 0, 0, 0))
            paint(ImageDraw.Draw(tile), tile.width / 2, tile.height / 2)
            turned = tile.rotate(turn, expand=True, resample=Image.BICUBIC)
            b = math.radians(bearing)
            cx, cy = mid + radius * math.sin(b) * k, mid - radius * math.cos(b) * k
            image.alpha_composite(turned, (round(cx - turned.width / 2), round(cy - turned.height / 2)))

        bar_m = self.desc["model"]["plate"]["scale_bar_m"]
        bar = bar_m / self.desc["model"]["plate"].get("unit_m", 1.0)       # length in model units
        width = max(3, round(0.11 * k))

        def scale_bar(d: ImageDraw.ImageDraw, cx: float, cy: float) -> None:
            d.line([cx - bar / 2 * k, cy, cx + bar / 2 * k, cy], fill=ink, width=width)
            for u in (-0.5, 0.0, 0.5):
                d.line([cx + u * bar * k, cy - 0.36 * k, cx + u * bar * k, cy + 0.36 * k], fill=ink, width=width)
            d.text((cx, cy - 0.62 * k), f"{bar_m} m", font=font, fill=ink, anchor="ms")

        def north(d: ImageDraw.ImageDraw, cx: float, cy: float) -> None:
            d.line([cx, cy + 0.9 * k, cx, cy - 0.7 * k], fill=ink, width=width)
            d.polygon([(cx, cy - 1.3 * k), (cx - 0.34 * k, cy - 0.6 * k), (cx + 0.34 * k, cy - 0.6 * k)], fill=ink)
            d.text((cx + 0.8 * k, cy), "N", font=font, fill=ink, anchor="lm")

        # the bar reads upright for a viewer standing outside the plate at its bearing; the arrow points north
        stamp(look["scale_bar_bearing"], R - 2.4, 180 - look["scale_bar_bearing"], scale_bar)
        stamp(look["north_mark_bearing"], R - 2.6, 0, north)
        data = np.flipud(np.array(image.convert("RGB")))          # row 0 becomes the south edge: v grows northwards
        texture = self.ctx.texture((size, size), 3, data.tobytes())
        texture.build_mipmaps()
        texture.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        texture.anisotropy = 16.0
        return texture

    def _build_model(self) -> None:
        model, matter = self.desc["model"], srgb(self.palette["matter"])
        parts, self.pick_ranges, cursor = [], {}, 0
        for prism in model["matter"]:
            lintel = prism["base"] > 0
            built = geometry.prism(prism["poly"], prism["base"], prism["top"], prism["taper"],
                                   prism.get("bevel", 0.07 if lintel else (0.16 if prism["top"] > 2 else 0.09)),
                                   hole=prism.get("cap_hole"))
            if prism["id"] in model["pick_order"] and prism["group"] == model["pick_group"]:
                self.pick_ranges[prism["id"]] = (cursor, len(built["tris"]))
            parts.append(built["tris"])
            cursor += len(built["tris"])
        self.matter = self._mesh(np.vstack(parts), {"albedo": matter, "rough": 0.82, "f0": 0.04})
        self.meshes.append(self.matter)

        # projected light: every volume, edge and footprint in three buffers, with a per-vertex strength
        reveals = self.tl["reveal"]
        self.light_top = max((prism["top"] for prism in model["light"]), default=1.0)
        self.lights, bodies, lines, feet = [], [], [], []
        for prism in model["light"]:
            built = geometry.prism(prism["poly"], prism["base"], prism["top"], prism["taper"],
                                   prism.get("bevel", 0.07 if prism["base"] > 0 else 0.16),
                                   rings=tuple(prism.get("rings", (True, True))), cap=prism.get("cap", True))
            cx, cz = built["centre"]
            bearing = math.degrees(math.atan2(cx, -cz)) % 360
            reveal = next((r for r in reveals if prism["group"] in r["groups"]), None)
            span = np.tile(np.array([prism["base"], prism["top"]], dtype="f4"), (len(built["tris"]), 1))
            foot = built["foot"] + np.array([0, 0.03, 0], dtype="f4") if prism["base"] == 0 else np.zeros((0, 3), dtype="f4")
            # each edge becomes a thin quad: (this end, other end, side) per corner
            a, b = built["lines"][0::2], built["lines"][1::2]
            plus, minus = np.ones((len(a), 1), dtype="f4"), -np.ones((len(a), 1), dtype="f4")
            corners = [np.c_[a, b, plus], np.c_[a, b, minus], np.c_[b, a, minus],
                       np.c_[a, b, minus], np.c_[b, a, plus], np.c_[b, a, minus]]
            ribbon = np.stack(corners, axis=1).reshape(-1, 7)
            self.lights.append({"group": prism["group"], "reveal": reveal, "order": ((bearing - reveal["from_bearing"]) % 360) / 360 if reveal else 0.0,
                                "n_body": len(built["tris"]), "n_lines": len(ribbon), "n_foot": len(foot)})
            bodies.append(np.c_[built["tris"], span])
            lines.append(ribbon)
            feet.append(foot)
        ctx = self.ctx
        self.k_body = ctx.buffer(reserve=4 * sum(i["n_body"] for i in self.lights), dynamic=True)
        self.k_lines = ctx.buffer(reserve=4 * sum(i["n_lines"] for i in self.lights), dynamic=True)
        self.k_foot = ctx.buffer(reserve=4 * max(1, sum(i["n_foot"] for i in self.lights)), dynamic=True)
        self.vao_body = ctx.vertex_array(self.glow, [(ctx.buffer(np.vstack(bodies).astype("f4").tobytes()), "3f 3f 2f", "in_pos", "in_nor", "in_span"),
                                                     (self.k_body, "1f", "in_k")])
        self.vao_lines = ctx.vertex_array(self.line, [(ctx.buffer(np.vstack(lines).astype("f4").tobytes()), "3f 3f 1f", "in_pos", "in_other", "in_side"),
                                                      (self.k_lines, "1f", "in_k")])
        self.vao_foot = ctx.vertex_array(self.flat, [(ctx.buffer(np.vstack(feet).astype("f4").tobytes()), "3f", "in_pos"), (self.k_foot, "1f", "in_k")])
        pool = geometry.disc(self.R - 0.8, 0.015, 96)[:, :3].copy()
        self.vao_pool = ctx.vertex_array(self.flat, [(ctx.buffer(pool.tobytes()), "3f", "in_pos"),
                                                     (ctx.buffer(np.ones(len(pool), dtype="f4").tobytes()), "1f", "in_k")])

    def _build_targets(self) -> None:
        ctx, size = self.ctx, (self.W, self.H)
        self.resolve_tex = ctx.texture(size, 4, dtype="f2")
        msaa = int(self.look.get("msaa", 0))
        if msaa:
            # multisampled target, resolved into resolve_tex after each view
            self.msaa = ctx.framebuffer([ctx.renderbuffer(size, 4, samples=msaa, dtype="f2")], ctx.depth_renderbuffer(size, samples=msaa))
            self.resolve = ctx.framebuffer([self.resolve_tex])
        else:
            # the accumulated jittered views already smooth the edges
            self.msaa = ctx.framebuffer([self.resolve_tex], ctx.depth_renderbuffer(size))
            self.resolve = None
        self.accum_tex = ctx.texture(size, 4, dtype="f2")
        self.accum = ctx.framebuffer([self.accum_tex])
        self.bloom = []
        w, h = self.W // 2, self.H // 2
        for _ in range(5):
            pair = []
            for _ in range(2):
                tex = ctx.texture((w, h), 4, dtype="f2")
                tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
                tex.repeat_x = tex.repeat_y = False
                pair.append((tex, ctx.framebuffer([tex])))
            self.bloom.append(pair)
            w, h = max(1, w // 2), max(1, h // 2)
        for tex in (self.resolve_tex, self.accum_tex):
            tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            tex.repeat_x = tex.repeat_y = False
        self.out = ctx.framebuffer([ctx.texture(size, 3)])
        self.shadow_tex = ctx.depth_texture((SHADOW_SIZE, SHADOW_SIZE))
        self.shadow_tex.compare_func = "<="
        self.shadow_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.shadow_tex.repeat_x = self.shadow_tex.repeat_y = False
        self.shadow_fbo = ctx.framebuffer(depth_attachment=self.shadow_tex)

    def _build_lights(self) -> None:
        look = self.look
        self.key_dir = bearing_vector(look["key_bearing"], look["key_elevation_deg"])
        self.rim_dir = bearing_vector(look["key_bearing"] + 205, 30)
        view = look_at(self.key_dir * 150.0, np.zeros(3))
        self.light_vp = ortho(SHADOW_HALF, 20.0, 320.0) @ view

    def _render_shadow_map(self) -> None:
        self.shadow_fbo.use()
        self.shadow_fbo.clear(depth=1.0)
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.depth["uLightVP"].write(self.light_vp.T.astype("f4").tobytes())
        for mesh in self.meshes:
            if mesh["depth"] is not None:
                mesh["depth"].render()

    # ---- per frame
    def state(self, frame: int) -> dict:
        """Every animated value for this frame. Pure function of the frame number."""
        t, tl, look = frame / self.fps, self.tl, self.look
        house = keyed(tl["house"], t)
        strike = 0.0
        struck = [s for s in tl["strikes"] if t >= s]            # dark before the first strike; each strike flickers
        if struck:
            index = int(math.floor((t - struck[-1]) * self.fps + 1e-6))
            strike = FLICKER[index] if index < len(FLICKER) else 1.0
        level = strike * keyed(tl["projector"], t)
        clip = keyed(tl["clip"], t) if tl.get("clip") else None
        pulse = 1.0
        if t >= tl["legend"]["light_pulse"]:
            pulse += look["light_pulse"] * math.exp(-(t - tl["legend"]["light_pulse"]) * 1.8)
        glows, count = {}, 0
        for stone, when in zip(self.pick_ids, self.pick_times):
            d = t - when
            if d >= 0:
                count += 1
            glows[stone] = look["pick_gain"] * (0.0 if d < -0.12 else ease_in_out(1 + d / 0.12) if d < 0
                                                else (math.exp(-d * look["pick_decay"]) if d < 2.2 else 0.0))
        camera = {field: spline(tl["camera"], field, t) for field in ("bearing", "elevation", "distance", "target_y")}
        value = None
        figure = tl.get("figure")
        if figure:                                    # the readout follows the count, then the rising light
            value = figure["values"][count - 1] if count else 0.0
            if clip is not None and t >= figure["follow_clip_from"]:
                # ... and returns to the count at once, so the number never sits beside the wrong label
                if not figure.get("follow_clip_until") or t < figure["follow_clip_until"]:
                    value = max(value, clip * figure["clip_top"])
        groups = {name: keyed(keys, t) for name, keys in (tl.get("light_levels") or {}).items()}
        return {"t": t, "house": house, "level": level * pulse, "pool": level, "glows": glows, "count": count,
                "camera": camera, "clip": clip, "value": value, "groups": groups}

    def _set(self, program: moderngl.Program, name: str, value) -> None:
        if name in program:
            member = program[name]
            if isinstance(value, np.ndarray) and value.ndim == 2:
                member.write(value.T.astype("f4").tobytes())
            elif isinstance(value, np.ndarray):
                member.value = tuple(float(v) for v in value)
            else:
                member.value = value

    def _prepare(self, st: dict) -> None:
        """Everything that is the same for all the jittered views of one frame."""
        look, p, lit, house = self.look, self.palette, self.lit, st["house"]
        self._set(lit, "uLightVP", self.light_vp)
        self._set(lit, "uKeyDir", self.key_dir)
        self._set(lit, "uKeyCol", srgb(p["key_light"]) * look["key"] * house)
        self._set(lit, "uRimDir", self.rim_dir)
        self._set(lit, "uRimCol", srgb(p["rim_light"]) * look["rim"] * (look["rim_dark"] + (1 - look["rim_dark"]) * house))
        self._set(lit, "uFillCol", srgb(p["fill_light"]) * look["fill"] * (0.15 + 0.85 * house))
        hemi = look["hemi"] * (0.06 + 0.94 * house)
        self._set(lit, "uSky", srgb(p["fill_light"]) * hemi)
        self._set(lit, "uGround", srgb(p["ground_bounce"]) * hemi)
        self._set(lit, "uSpotPos", np.array([0.0, 120.0, 0.0]))
        self._set(lit, "uSpotCol", srgb(p["rim_light"]) * look["floor_spot"] * (look["spot_dark"] + (1 - look["spot_dark"]) * house))
        self._set(lit, "uSpotCos", math.cos(math.radians(34)))
        self._set(lit, "uShadowTexel", 1.0 / SHADOW_SIZE)
        self._set(lit, "uPlateR", self.R)
        self._set(lit, "uEmissive", PICK_GLOW)
        if "uPoisson" in lit:
            # a driver may report only the elements the shader reads (Mesa trims the array to 8)
            taps = lit["uPoisson"].array_length
            lit["uPoisson"].write(np.array(POISSON[:taps], dtype="f4").tobytes())
        self._set(lit, "uShadow", 0)
        self._set(lit, "uMap", 1)

        glow = np.zeros(self.matter["count"], dtype="f4")
        for stone, (start, count) in self.pick_ranges.items():
            glow[start:start + count] = st["glows"].get(stone, 0.0)
        self.matter["glow"].write(glow.tobytes())

        t, level = st["t"], st["level"]
        body, edge, foot = [], [], []
        for item in self.lights:
            reveal = item["reveal"]
            f = b = 0.0
            if reveal is not None:
                start = reveal["t"] + reveal["spread"] * item["order"]
                own = level * st["groups"].get(item["group"], 1.0)       # a group of volumes may be dimmed on its own
                f = ease_out(ramp(t, start, start + 0.4)) * own
                b = ease_out(ramp(t, start + reveal["rise_after"], start + reveal["rise_after"] + 0.65)) * own
            body.append(np.full(item["n_body"], b, dtype="f4"))
            edge.append(np.full(item["n_lines"], b, dtype="f4"))
            foot.append(np.full(item["n_foot"], f, dtype="f4"))
        self.k_body.write(np.concatenate(body).tobytes())
        self.k_lines.write(np.concatenate(edge).tobytes())
        if sum(i["n_foot"] for i in self.lights):
            self.k_foot.write(np.concatenate(foot).tobytes())
        self._set(self.glow, "uColor", self.accent * look["light_body"])
        self._set(self.flat, "uPlateR", self.R)
        clip = st.get("clip")
        rising = clip is not None and clip < 1.0
        clip_y = clip * self.light_top if rising else 1e9
        self._set(self.glow, "uClipY", clip_y)
        self._set(self.glow, "uBand", look["clip_band"])
        # the bright front fades out over its own height as it reaches the top, so it does not vanish on one frame
        lead = look["clip_lead"] * min(1.0, (1.0 - clip) * self.light_top / look["clip_band"]) if rising else 0.0
        self._set(self.glow, "uLead", lead)
        self._set(self.line, "uClipY", clip_y)

    def _draw(self, view_proj: np.ndarray, eye: np.ndarray, forward: np.ndarray, st: dict) -> None:
        ctx, look, lit = self.ctx, self.look, self.lit
        self._set(lit, "uViewProj", view_proj)
        self._set(lit, "uCam", eye)
        self._set(lit, "uFillDir", -forward)
        self.shadow_tex.use(0)
        self.plate_tex.use(1)
        for mesh in reversed(self.meshes):          # nearest surfaces first, so hidden floor is not shaded
            m = mesh["material"]
            self._set(lit, "uAlbedo", m["albedo"])
            self._set(lit, "uRough", m["rough"])
            self._set(lit, "uF0", m["f0"])
            self._set(lit, "uUseMap", 1 if m.get("map") else 0)
            mesh["vao"].render()

        # projected light: added on top, never darkening, and hidden behind matter
        if st["level"] > 0.002:
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = (moderngl.ONE, moderngl.ONE)
            self.msaa.depth_mask = False
            self._set(self.flat, "uViewProj", view_proj)
            self._set(self.glow, "uViewProj", view_proj)
            self._set(self.glow, "uCam", eye)
            self._set(self.flat, "uPool", 1.0)
            self._set(self.flat, "uColor", self.accent * look["light_pool"] * st["pool"])
            self.vao_pool.render()
            self._set(self.flat, "uPool", 0.0)
            self._set(self.flat, "uColor", self.accent * look["light_foot"])
            self.vao_foot.render()
            self.vao_body.render()
            self._set(self.line, "uViewProj", view_proj)
            self._set(self.line, "uViewport", (float(self.W), float(self.H)))
            self._set(self.line, "uWidth", look["light_edge_px"])
            self._set(self.line, "uColor", self.accent * look["light_edge"])
            self.vao_lines.render()
            self.msaa.depth_mask = True
            ctx.disable(moderngl.BLEND)

    def picture(self, frame: int) -> tuple[np.ndarray, dict]:
        """The 3D picture for this frame as (H, W, 3) uint8, plus the frame's state."""
        ctx, look, W, H = self.ctx, self.look, self.W, self.H
        st = self.state(frame)
        room = srgb(self.palette["room"])

        def camera_at(moment: float):
            """Where the camera is and looks at a moment (seconds): a pure function of time."""
            c = {field: spline(self.tl["camera"], field, moment) for field in ("bearing", "elevation", "distance", "target_y")}
            aim = np.array([0.0, c["target_y"], 0.0])
            eye0 = aim + bearing_vector(c["bearing"], c["elevation"]) * c["distance"]
            ahead = (aim - eye0) / np.linalg.norm(aim - eye0)
            side = np.cross(ahead, [0.0, 1.0, 0.0])
            side /= np.linalg.norm(side)
            return c, aim, eye0, ahead, side, np.cross(side, ahead)

        cam, target, base, forward, right, up = camera_at(st["t"])
        # a film that moves in close keeps the same depth of field by scaling the lens with the distance
        aperture = look["aperture"] * (cam["distance"] / look["aperture_at"] if look.get("aperture_at") else 1.0)
        self._prepare(st)

        self.accum.use()
        self.accum.clear(0.0, 0.0, 0.0, 0.0)
        n = self.samples
        for i in range(n):
            # jittered views: depth of field about the focus point, and edge smoothing
            if n > 1:
                radius, angle = math.sqrt((i + 0.5) / n), i * 2.39996323
                dx, dy = radius * math.cos(angle) * aperture, radius * math.sin(angle) * aperture
            else:
                dx = dy = 0.0
            if look["shutter"] > 0 and n > 1:
                # the shutter stays open for part of the frame: each view sees the camera where it is at its own
                # moment, so fine lines that move far between frames blur along their path and do not strobe
                # (the moments come from their own sequence, base 5, so that time is tied neither to the lens offsets
                # nor to the pixel offsets, which use bases 2 and 3; a fixed stride through the views was tried first
                # and fell in step with the vertical pixel offset, which undid the blur for lines moving up or down)
                moment = st["t"] + (halton(i + 1, 5) - 0.5) * look["shutter"] / self.fps
                _, target, base, forward, right, up = camera_at(moment)
            eye = base + right * dx + up * dy
            # each view is moved by part of a pixel; a wider spread (aa_width) quietens very fine parallel lines
            jx, jy = (halton(i + 1, 2) - 0.5) * look["aa_width"], (halton(i + 1, 3) - 0.5) * look["aa_width"]
            shift = (2 * jx / W, 2 * (look["view_offset_y"] + jy) / H)
            view_proj = perspective(look["fov"], W / H, look["near"], 700.0, shift) @ look_at(eye, target)
            self.msaa.use()
            self.msaa.clear(float(room[0]), float(room[1]), float(room[2]), 1.0, depth=1.0)
            ctx.enable(moderngl.DEPTH_TEST)
            turn = i * 2.39996323 * 1.7
            self._set(self.lit, "uTurn", (math.cos(turn), math.sin(turn)))
            self._draw(view_proj, eye, forward, st)
            if self.resolve is not None:
                ctx.copy_framebuffer(self.resolve, self.msaa)
            self.accum.use()
            ctx.disable(moderngl.DEPTH_TEST)
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = (moderngl.ONE, moderngl.ONE)
            self.resolve_tex.use(0)
            self.p_add["uTex"].value = 0
            self.p_add["uWeight"].value = 1.0 / n
            self.quads[self.p_add].render()
            ctx.disable(moderngl.BLEND)

        # bloom: bright parts only, blurred at five sizes
        ctx.disable(moderngl.DEPTH_TEST)
        source = self.accum_tex
        for level, pair in enumerate(self.bloom):
            (tex_a, fbo_a), (tex_b, fbo_b) = pair
            fbo_a.use()
            source.use(0)
            if level == 0:
                self.p_bright["uTex"].value = 0
                self.p_bright["uThreshold"].value = look["bloom_threshold"]
                self.quads[self.p_bright].render()
            else:
                self.p_add["uTex"].value = 0
                self.p_add["uWeight"].value = 1.0
                self.quads[self.p_add].render()
            for step, (src, dst) in (((1.0 / tex_a.width, 0.0), (tex_a, fbo_b)), ((0.0, 1.0 / tex_a.height), (tex_b, fbo_a))):
                dst.use()
                src.use(0)
                self.p_blur["uTex"].value = 0
                self.p_blur["uStep"].value = step
                self.quads[self.p_blur].render()
            source = tex_a

        self.out.use()
        self.accum_tex.use(0)
        grade = self.p_grade
        grade["uTex"].value = 0
        for level, pair in enumerate(self.bloom):
            pair[0][0].use(level + 1)
            grade[f"uB{level}"].value = level + 1
        grade["uBloom"].value = look["bloom_strength"]
        grade["uRadius"].value = look["bloom_radius"]
        grade["uExposure"].value = look["exposure"]
        grade["uVignette"].value = look["vignette"]
        grade["uSeed"].value = float(frame % 997)
        self.quads[grade].render()
        pixels = np.frombuffer(self.out.read(components=3), dtype=np.uint8).reshape(H, W, 3)
        return np.flipud(pixels).copy(), st

    def close(self) -> None:
        self.ctx.release()
