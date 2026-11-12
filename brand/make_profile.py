"""Profile photo options for the Measured Past channel. Run from the repository root:
python brand/make_profile.py   ->  brand/profile_*.png (1024 x 1024) and brand/profile_options.jpg
Platforms crop the picture to a circle, so everything sits inside the central 80 %."""
import json, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "brand"
S = 2048                                   # drawn at double size, then reduced
DARK, PAPER, WHITE, INK, ACCENT = "#0E1014", "#EEF1F4", "#F4F4F2", "#15171B", "#FF4A1F"
BOLD = str(ROOT / "assets/fonts/InterDisplay-Bold.otf")
MONO = str(ROOT / "assets/fonts/JetBrainsMono-Medium.ttf")


def centred(draw, text, font, cy, fill, cx=S / 2):
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    draw.text((cx - (l + r) / 2, cy - (t + b) / 2), text, font=font, fill=fill)


def scale_bar(draw, x0, x1, y, colour, width=26, tick=70):
    draw.line([(x0, y), (x1, y)], fill=colour, width=width)
    for x in (x0, x1):
        draw.line([(x, y - tick), (x, y + tick)], fill=colour, width=width)


def monogram():
    im = Image.new("RGB", (S, S), DARK); d = ImageDraw.Draw(im)
    centred(d, "MP", ImageFont.truetype(BOLD, 760), S * 0.45, WHITE)
    scale_bar(d, S * 0.27, S * 0.73, S * 0.71, ACCENT)
    return im


def ruler():
    im = Image.new("RGB", (S, S), DARK); d = ImageDraw.Draw(im)
    x0, x1, y = S * 0.22, S * 0.78, S * 0.56
    d.line([(x0, y), (x1, y)], fill=WHITE, width=30)
    for i in range(11):
        x = x0 + (x1 - x0) * i / 10
        h = 230 if i % 5 == 0 else 120
        d.line([(x, y - h), (x, y)], fill=ACCENT if i == 7 else WHITE, width=30)
    centred(d, "M", ImageFont.truetype(BOLD, 300), S * 0.70, WHITE, cx=S * 0.5)
    return im


def plan():
    data = json.loads((ROOT / "topics/stonehenge/stones.json").read_text(encoding="utf-8"))
    im = Image.new("RGB", (S, S), DARK); d = ImageDraw.Draw(im)
    k = S * 0.36 / 17.5                                    # metres to pixels; the circle fills 72 % of the frame
    px = lambda x, y: (S / 2 + x * k, S / 2 - y * k)
    for st in data["inferred_uprights"]:                    # missing circle uprights, in the accent
        a = math.atan2(st["y"], st["x"]); c, s = math.cos(a), math.sin(a)
        w, t = 1.05, 0.55                                   # half length along the ring, half thickness
        pts = [px(st["x"] + sx * t * c - sy * w * s, st["y"] + sx * t * s + sy * w * c) for sx, sy in ((1, 1), (1, -1), (-1, -1), (-1, 1))]
        d.polygon(pts, fill=ACCENT)
    for st in data["stones"]:
        if st["group"] == "bluestone":
            continue
        d.polygon([px(x, y) for x, y in st["poly"]], fill=WHITE)
    return im


def paper():
    im = Image.new("RGB", (S, S), PAPER); d = ImageDraw.Draw(im)
    centred(d, "M", ImageFont.truetype(BOLD, 1050), S * 0.44, INK)
    d.rectangle([S * 0.30, S * 0.735, S * 0.70, S * 0.735 + 44], fill=ACCENT)
    return im


def main():
    options = {"a_monogram": monogram(), "b_ruler": ruler(), "c_plan": plan(), "d_paper": paper()}
    small = {}
    for name, im in options.items():
        small[name] = im.resize((1024, 1024), Image.LANCZOS)
        small[name].save(OUT / f"profile_{name}.png")
    # preview: each option as the platforms show it, in a circle, large and at feed size
    sheet = Image.new("RGB", (4 * 520 + 40, 760), "#22252B"); d = ImageDraw.Draw(sheet)
    label = ImageFont.truetype(MONO, 30)
    for i, (name, im) in enumerate(small.items()):
        x = 40 + i * 520
        for size, y in ((440, 70), (96, 560)):
            tile = im.resize((size * 2, size * 2), Image.LANCZOS)
            mask = Image.new("L", tile.size, 0); ImageDraw.Draw(mask).ellipse([0, 0, tile.size[0] - 1, tile.size[1] - 1], fill=255)
            tile.putalpha(mask); tile = tile.resize((size, size), Image.LANCZOS)
            sheet.paste(tile, (x + (440 - size) // 2 if size == 96 else x, y), tile)
        d.text((x, 20), name.replace("_", "  ").upper(), font=label, fill="#C9CDD3")
    sheet.save(OUT / "profile_options.jpg", quality=92)


if __name__ == "__main__":
    main()
