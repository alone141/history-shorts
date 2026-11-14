"""Phase model look: the text layer.

Hook, readout, legend, captions and credit, drawn with Pillow over the 3D
picture. Positions and sizes come from engine/tokens.json. Every opacity is a
pure function of the frame's time.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]

# vertical positions of the text blocks (top of each line box, px)
EYEBROW_Y, HOOK_Y = 200, 240
FIGURE_Y, LABEL_Y = 1104, 1280
LEGEND_Y = (1346, 1384)
CAPTION_Y, CREDIT_Y = 1422, 1470
CAPTION_BIG_Y = 1430          # captions shown a few words at a time, in the larger size
CHUNK_FADE_S = 0.07


def _rgb(hex_colour: str) -> tuple[int, int, int]:
    value = hex_colour.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ramp(t: float, a: float, b: float) -> float:
    return (1.0 if t >= b else 0.0) if b <= a else clamp01((t - a) / (b - a))


def ease_out(u: float) -> float:
    return 1 - (1 - clamp01(u)) ** 3


def ease_in_out(u: float) -> float:
    u = clamp01(u)
    return u * u * (3 - 2 * u)


class Sprite:
    """A pre-drawn piece of text: premultiplied-free RGBA at a fixed place."""

    def __init__(self, image: Image.Image, x: int, y: int):
        data = np.asarray(image, dtype=np.float32)
        self.rgb, self.alpha = data[:, :, :3], data[:, :, 3:4] / 255.0
        self.x, self.y = x, y

    def blend(self, frame: np.ndarray, opacity: float, brightness: float = 1.0) -> None:
        if opacity <= 0.002:
            return
        h, w = self.alpha.shape[:2]
        y0, x0 = max(0, self.y), max(0, self.x)
        y1, x1 = min(frame.shape[0], self.y + h), min(frame.shape[1], self.x + w)
        if y1 <= y0 or x1 <= x0:
            return
        sy, sx = slice(y0 - self.y, y1 - self.y), slice(x0 - self.x, x1 - self.x)
        a = self.alpha[sy, sx] * opacity
        rgb = np.minimum(self.rgb[sy, sx] * brightness, 255.0)
        region = frame[y0:y1, x0:x1]
        region += (rgb - region) * a


class Overlay:
    def __init__(self, desc: dict, accent_hex: str):
        self.desc, self.tokens = desc, desc["tokens"]
        self.tl, self.text = desc["timeline"], desc["text"]
        self.palette = self.tokens["phase"]
        self.W, self.H = self.tokens["frame"]["width"], self.tokens["frame"]["height"]
        self.x = self.tokens["safe"]["left"]
        self.accent = _rgb(accent_hex)
        self.sentences = desc["narration"]["sentences"]
        self._fonts: dict = {}
        self.problems: list[str] = []
        self._shades()
        self._static()

    # ---- drawing helpers
    def font(self, style: str) -> tuple[ImageFont.FreeTypeFont, dict]:
        if style not in self._fonts:
            spec = self.tokens["type"]["scale"][style]
            path = ROOT / self.tokens["type"]["families"][spec["family"]][spec["weight"]]
            self._fonts[style] = (ImageFont.truetype(str(path), spec["size"]), spec)
        return self._fonts[style]

    def _width(self, text: str, style: str) -> float:
        font, spec = self.font(style)
        tracking = spec["tracking"] * spec["size"]
        if abs(tracking) < 1.0:
            return font.getlength(text)
        return sum(font.getlength(ch) + tracking for ch in text) - tracking

    def _draw(self, draw: ImageDraw.ImageDraw, x: float, top: float, text: str, style: str, fill) -> float:
        """Draw one line with its line box starting at `top`; returns the x after the text."""
        font, spec = self.font(style)
        ascent, descent = font.getmetrics()
        baseline = top + (spec["line"] - (ascent + descent)) / 2 + ascent
        tracking = spec["tracking"] * spec["size"]
        if abs(tracking) < 1.0:                       # keep the font's own kerning
            draw.text((x, baseline), text, font=font, fill=fill, anchor="ls")
            return x + font.getlength(text)
        for ch in text:
            draw.text((x, baseline), ch, font=font, fill=fill, anchor="ls")
            x += font.getlength(ch) + tracking
        return x - tracking

    def _sprite(self, width: int, height: int, x: int, y: int, paint) -> Sprite:
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        paint(ImageDraw.Draw(image), image)
        return Sprite(image, x, y)

    def wrap(self, text: str, style: str, max_width: float) -> list[str]:
        lines, current = [], ""
        for word in text.split():
            trial = (current + " " + word).strip()
            if not current or self._width(trial, style) <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    # ---- static layers
    def _shades(self) -> None:
        """Soft dark bands behind the text at top and bottom, as per-row opacity."""
        y = np.arange(self.H, dtype=np.float32)
        top = np.interp(y, [0, 286, 520], [0.92, 0.62, 0.0])
        bottom = np.interp(y, [1020, 1398, 1920], [0.0, 0.86, 0.97])
        self.shade = np.maximum(top, bottom)[:, None, None]
        self.shade_colour = np.array(_rgb(self.palette["room"]), dtype=np.float32)

    def _static(self) -> None:
        p, x = self.palette, self.x
        text_colour, secondary, mono = _rgb(p["text"]), _rgb(p["text_secondary"]), _rgb(p["text_mono"])
        hook_line = self.tokens["type"]["scale"]["hook"]["line"]

        def head(draw, image):
            self._draw(draw, 0, 0, self.text["eyebrow"], "eyebrow", mono + (255,))
            for i, line in enumerate(self.text["hook"]):
                self._draw(draw, 0, HOOK_Y - EYEBROW_Y + i * hook_line, line, "hook", text_colour + (255,))
        self.head = self._sprite(self.W - x, HOOK_Y - EYEBROW_Y + 2 * hook_line + 20, x, EYEBROW_Y, head)
        widest = max(self._width(line, "hook") for line in self.text["hook"])
        if x + widest > self.tokens["safe"]["right"]:
            self.problems.append(f"hook is {widest:.0f} px wide and runs past x = {self.tokens['safe']['right']}")

        self.label = self._sprite(self.W - x, 60, x, LABEL_Y,
                                  lambda d, im: self._draw(d, 0, 0, self.text["label"], "label", text_colour + (255,)))
        self.label_after = None
        if self.text.get("label_after"):
            self.label_after = self._sprite(self.W - x, 60, x, LABEL_Y,
                                            lambda d, im: self._draw(d, 0, 0, self.text["label_after"], "label", text_colour + (255,)))
        for text in (self.text["label"], self.text.get("label_after") or ""):
            if x + self._width(text, "label") > self.tokens["safe"]["lower_half_right"]:
                self.problems.append(f"label {text!r} runs past x = {self.tokens['safe']['lower_half_right']}")

        def legend(row: list[str], swatch: tuple[int, int, int], glow: bool):
            def paint(draw, image):
                if glow:
                    halo = Image.new("RGBA", image.size, (0, 0, 0, 0))
                    ImageDraw.Draw(halo).rounded_rectangle([14, 14, 38, 38], 3, fill=swatch + (200,))
                    image.alpha_composite(halo.filter(ImageFilter.GaussianBlur(7)))
                draw.rounded_rectangle([14, 14, 38, 38], 3, fill=swatch + (255,))
                after = self._draw(draw, 54, 10, row[0], "mono_small", text_colour + (255,))
                self._draw(draw, after + 18, 10, row[1], "mono_small", secondary + (255,))
            return paint
        self.legend = [
            self._sprite(self.W - x + 14, 52, x - 14, LEGEND_Y[0] - 10, legend(self.text["legend_matter"], _rgb(p["matter"]), False)),
            self._sprite(self.W - x + 14, 52, x - 14, LEGEND_Y[1] - 10, legend(self.text["legend_light"], self.accent, True)),
        ]
        for row in (self.text["legend_matter"], self.text["legend_light"]):
            width = 40 + self._width(row[0], "mono_small") + 18 + self._width(row[1], "mono_small")
            if x + width > self.tokens["safe"]["lower_half_right"]:
                self.problems.append(f"legend row {row[0]!r} runs past x = {self.tokens['safe']['lower_half_right']}")

        # figure: "17" + "of" + "30", digits drawn once per value
        self.digits: dict[str, Sprite] = {}
        self._figure_cache: dict = {}
        if self.text.get("figure"):
            for value in list(self.tl["figure"]["values"]) + [self.tl["figure"]["clip_top"]]:
                self._reading_fits(value)

        credit_lines = self.wrap(self.text.get("credit", ""), "credit", self.tokens["captions"]["max_width"])
        line = self.tokens["type"]["scale"]["credit"]["line"]
        if len(credit_lines) > 2:
            self.problems.append("credit line needs more than two lines")

        def credit(draw, image):
            for i, text in enumerate(credit_lines):
                self._draw(draw, 0, i * line, text, "credit", mono + (255,))
        self.credit = self._sprite(self.W - x, line * max(1, len(credit_lines)) + 8, x, CREDIT_Y, credit)
        if CREDIT_Y + line * len(credit_lines) > self.tokens["safe"]["bottom"]:
            self.problems.append("credit runs below the safe area")

        # captions: (sprite, start, end, (fade in, fade out)). A sentence is shown whole, or, when the
        # script splits it into chunks, a few words at a time in the larger size.
        self.captions: list[tuple[Sprite, float, float, tuple[float, float]]] = []
        caps = self.tokens["captions"]
        cap_line = self.tokens["type"]["scale"]["caption"]["line"]
        big_line = self.tokens["type"]["scale"]["caption_big"]["line"]

        def caption_sprite(lines: list[str], style: str, line: int, top: int) -> Sprite:
            def paint(draw, image):
                shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
                sd = ImageDraw.Draw(shadow)
                for i, text in enumerate(lines):
                    self._draw(sd, 20, 20 + i * line + 2, text, style, (0, 0, 0, 215))
                image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(6)))
                for i, text in enumerate(lines):
                    self._draw(draw, 20, 20 + i * line, text, style, text_colour + (255,))
            return self._sprite(self.W - x + 20, line * len(lines) + 44, x - 20, top - 20, paint)

        for sentence in self.sentences:
            if sentence.get("caption") is False:
                continue
            if sentence.get("chunks"):
                last = len(sentence["chunks"]) - 1
                for i, chunk in enumerate(sentence["chunks"]):
                    if self._width(chunk["text"], "caption_big") > caps["max_width"]:
                        self.problems.append(f"caption chunk {chunk['text']!r} is wider than {caps['max_width']} px")
                    # one chunk gives way to the next on a single frame; only the sentence fades in and out
                    self.captions.append((caption_sprite([chunk["text"]], "caption_big", big_line, CAPTION_BIG_Y),
                                          chunk["start_s"], chunk["end_s"],
                                          (CHUNK_FADE_S if i == 0 else 0.0, CHUNK_FADE_S if i == last else 0.0)))
                if CAPTION_BIG_Y + big_line > caps["bottom"]:
                    self.problems.append(f"caption {sentence['id']} runs below y = {caps['bottom']}")
                continue
            lines = self.wrap(sentence["text"], "caption", caps["max_width"])
            if len(lines) > caps["max_lines"]:
                self.problems.append(f"caption {sentence['id']} needs {len(lines)} lines")
            if CAPTION_Y + cap_line * len(lines) > caps["bottom"]:
                self.problems.append(f"caption {sentence['id']} runs below y = {caps['bottom']}")
            self.captions.append((caption_sprite(lines, "caption", cap_line, CAPTION_Y),
                                  sentence["start_s"], sentence["end_s"], (caps["fade_s"], caps["fade_s"])))

    def _figure(self, count: int) -> tuple[Sprite, Sprite]:
        """The big count, and the 'of 30' that joins it later."""
        if count not in self._figure_cache:
            p = self.palette
            text_colour, secondary = _rgb(p["text"]), _rgb(p["text_secondary"])
            number = str(count)
            end = self._width(number, "figure")
            figure_font, figure_spec = self.font("figure")
            unit_font, unit_spec = self.font("figure_unit")
            asc_f, desc_f = figure_font.getmetrics()
            baseline = (figure_spec["line"] - (asc_f + desc_f)) / 2 + asc_f
            asc_u, desc_u = unit_font.getmetrics()
            unit_top = baseline - asc_u - (unit_spec["line"] - (asc_u + desc_u)) / 2

            left = self._sprite(520, 200, self.x - 8, FIGURE_Y,
                                lambda d, im: self._draw(d, 0, 0, number, "figure", text_colour + (255,)))

            def rest(draw, image):
                after = self._draw(draw, end + 12, unit_top, "of", "figure_unit", secondary + (255,))
                self._draw(draw, after + 14, 0, str(self.text["figure_total"]), "figure", text_colour + (255,))
            right = self._sprite(900, 200, self.x - 8, FIGURE_Y, rest)
            self._figure_cache[count] = (left, right)
        return self._figure_cache[count]

    def _reading(self, value: float) -> Sprite:
        """The readout in real units: the big number, its unit, and the same length in a second unit."""
        spec = self.text["figure"]
        number = f"{value:.{spec.get('decimals', 0)}f}"
        second = spec.get("second")
        # the second unit is worked from the number as printed, so the two always agree
        other = f"{float(number) * second['factor']:.{second.get('decimals', 0)}f} {second['unit']}" if second else ""
        key = (number, other)
        if key not in self._figure_cache:
            p = self.palette
            text_colour = _rgb(p["text"])
            end = self._width(number, "figure")
            figure_font, figure_spec = self.font("figure")
            unit_font, unit_spec = self.font("figure_unit")
            asc_f, desc_f = figure_font.getmetrics()
            baseline = (figure_spec["line"] - (asc_f + desc_f)) / 2 + asc_f
            asc_u, desc_u = unit_font.getmetrics()
            unit_top = baseline - asc_u - (unit_spec["line"] - (asc_u + desc_u)) / 2

            def paint(draw, image):
                # the lit model is often behind the readout, so it stands on the same soft shadow as the captions
                shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
                sd = ImageDraw.Draw(shadow)
                after = self._draw(sd, end + 12, unit_top + 2, spec["unit"], "figure_unit", (0, 0, 0, 200))
                self._draw(sd, 0, 2, number, "figure", (0, 0, 0, 150))
                if other:
                    self._draw(sd, after + 44, unit_top + 2, other, "figure_unit", (0, 0, 0, 215))
                image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(7)))
                self._draw(draw, 0, 0, number, "figure", text_colour + (255,))
                after = self._draw(draw, end + 12, unit_top, spec["unit"], "figure_unit", text_colour + (255,))
                if other:
                    self._draw(draw, after + 44, unit_top, other, "figure_unit", text_colour + (255,))
            while len(self._figure_cache) >= 8:             # a frame needs one; a dropped one is redrawn the same
                self._figure_cache.pop(next(iter(self._figure_cache)))
            self._figure_cache[key] = self._sprite(self.W - self.x, 200, self.x - 8, FIGURE_Y, paint)
        return self._figure_cache[key]

    def _reading_fits(self, value: float) -> None:
        """Layout test for one readout value; run for every value before any frame is drawn."""
        spec = self.text["figure"]
        number = f"{value:.{spec.get('decimals', 0)}f}"
        second = spec.get("second")
        other = f"{float(number) * second['factor']:.{second.get('decimals', 0)}f} {second['unit']}" if second else ""
        width = (self._width(number, "figure") + 12 + self._width(spec["unit"], "figure_unit")
                 + (44 + self._width(other, "figure_unit") if other else 0))
        limit = self.tokens["safe"]["lower_half_right"]
        if self.x - 8 + width > limit and not any("readout" in p for p in self.problems):
            self.problems.append(f"readout {number} {spec['unit']} {other} runs past x = {limit}")

    # ---- per frame
    def apply(self, picture: np.ndarray, t: float, count: int, value: float | None = None) -> np.ndarray:
        tl = self.tl
        frame = picture.astype(np.float32)
        frame += (self.shade_colour - frame) * self.shade
        self.head.blend(frame, 1.0)

        figure_in = tl["figure_in"]
        shown = ease_out(ramp(t, figure_in, figure_in + 0.5))
        if self.text.get("figure"):
            self._reading(value or 0.0).blend(frame, shown)
        else:
            left, right = self._figure(count)
            left.blend(frame, shown)
            right.blend(frame, ease_out(ramp(t, tl["of_in"], tl["of_in"] + 0.6)))
        label_in = ease_out(ramp(t, figure_in + 0.2, figure_in + 0.7))
        if self.label_after is not None:
            after = tl["label_after"]
            if after.get("above") is not None:
                # the label follows the number, frame for frame and with no cross-fade: the first label while the
                # readout rests at "above" (or anywhere under it, unless "first_from" makes it wait for the count to
                # land), the second once it has reached "from", and none while the number is running
                live = after.get("until") is None or t < after["until"]
                first = 0.0 if live and (value or 0.0) > after["above"] else 1.0
                if after.get("first_from") is not None and (value or 0.0) < after["first_from"]:
                    first = 0.0
                second = 1.0 if live and (value or 0.0) >= after["from"] else 0.0
            else:
                second = ease_in_out(ramp(t, after["t"], after["t"] + 0.35))
                if after.get("until") is not None:
                    second *= 1 - ease_in_out(ramp(t, after["until"], after["until"] + 0.35))
                first = 1 - second
            self.label.blend(frame, label_in * first)
            self.label_after.blend(frame, label_in * second)
        else:
            self.label.blend(frame, label_in)

        def emphasis(t0: float) -> float:
            d = t - t0
            return 0.0 if d < 0 else ease_in_out(d / 0.25) if d < 0.25 else math.exp(-(d - 0.25) * 1.6)
        for sprite, start, pulse in ((self.legend[0], tl["legend"]["matter_in"], tl["legend"]["matter_pulse"]),
                                     (self.legend[1], tl["legend"]["light_in"], tl["legend"]["light_pulse"])):
            e = emphasis(pulse)
            sprite.blend(frame, ease_out(ramp(t, start, start + 0.5)) * (0.74 + 0.26 * e), 1 + 0.45 * e)

        for sprite, start, end, (fade_in, fade_out) in self.captions:
            # with no fade a caption is on screen for exactly [start, end), so two chunks never show together
            if start - 0.001 <= t < end + max(fade_out, 1e-9):
                sprite.blend(frame, ramp(t, start, start + fade_in) * (1 - ramp(t, end, end + fade_out)))
        credit = ease_out(ramp(t, tl["credit_in"], tl["credit_in"] + 0.6))
        if tl.get("credit_also"):
            a, b = tl["credit_also"]
            credit = max(credit, ease_out(ramp(t, a, a + 0.4)) * (1 - ease_in_out(ramp(t, b - 0.4, b))))
        self.credit.blend(frame, credit)
        return np.clip(frame + 0.5, 0, 255).astype(np.uint8)
