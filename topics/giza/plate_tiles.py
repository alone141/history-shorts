"""Petrie 1883, Plate VIII: cut the strips of the fold-out into small reading tiles.

The plate prints, against one upright line per course, the level of that course
in inches above the pavement at the N.E. corner (upper row) and the S.W. corner
(lower row). The numerals are written sideways, so each tile is the numeral band
under a few upright lines, turned to read left to right and enlarged. A margin
on the left gives each row the index of its upright line in the strip (a reading
aid only; nothing in the scan is changed).

    python -m topics.giza.plate_tiles            # writes build/giza/tiles/*.png and tiles.json

The geometry found here (where each upright line and each grid line sits) is
also what build_courses.py uses to check the readings against the drawing.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from engine.files import fresh, write_text as save_text

ROOT = Path(__file__).resolve().parents[2]
SCANS = ROOT / "data" / "giza" / "petrie"
OUT = ROOT / "build" / "giza" / "tiles"
FONT = ROOT / "assets" / "fonts" / "JetBrainsMono-Medium.ttf"

# The three leaves of the Cornell copy that hold the plate, lowest courses first.
# "zero" is the bottom frame line (0 inches) as (x, y) points read off the scan; the
# 10-inch line is `PX_PER_10IN` above it. Leaf 0290 is slightly warped, hence three points.
PX_PER_10IN = 290.6
STRIPS = {
    "lower": {"leaf": "0306", "zero": [(700, 1884), (1870, 1886), (3100, 1882)]},
    "middle": {"leaf": "0290", "zero": [(713, 1838), (1878, 1834), (3118, 1824)]},
    "upper": {"leaf": "0291", "zero": [(300, 1812), (780, 1811), (1290, 1809)]},
}
PER_TILE = 8
ZOOM = 4
MARGIN = 230


def scan(leaf: str) -> np.ndarray:
    Image.MAX_IMAGE_PIXELS = None
    return np.asarray(Image.open(SCANS / f"cu31924012038927_{leaf}.jp2").convert("L"))


def zero_y(strip: dict, x: float) -> float:
    xs, ys = zip(*strip["zero"])
    return float(np.interp(x, xs, ys))


def level_y(strip: dict, x: float, inches: float) -> float:
    """Scan row of a level on the thickness scale (0 at the bottom frame line)."""
    return zero_y(strip, x) - inches * PX_PER_10IN / 10.0


def upright_lines(pixels: np.ndarray, strip: dict) -> list[float]:
    """x of every upright line, found in the clear band between the 19 and 14 inch levels."""
    dark = pixels < 128
    width = dark.shape[1]
    hits = []
    for x in range(width):
        y0, y1 = int(level_y(strip, x, 19.0)), int(level_y(strip, x, 14.2))
        if dark[y0:y1, x].sum() > 0.6 * (y1 - y0):
            hits.append(x)
    groups: list[list[int]] = []
    for x in hits:
        if groups and x - groups[-1][-1] <= 3:
            groups[-1].append(x)
        else:
            groups.append([x])
    return [(g[0] + g[-1]) / 2 for g in groups]


def geometry() -> dict:
    out = {}
    for name, strip in STRIPS.items():
        pixels = scan(strip["leaf"])
        out[name] = {"leaf": strip["leaf"], "size": [int(pixels.shape[1]), int(pixels.shape[0])],
                     "lines": upright_lines(pixels, strip)}
    return out


def make_tiles() -> list[dict]:
    OUT.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(str(FONT), 40)
    tiles = []
    for name, strip in STRIPS.items():
        pixels = scan(strip["leaf"])
        lines = upright_lines(pixels, strip)
        for start in range(0, len(lines), PER_TILE):
            group = lines[start:start + PER_TILE]
            x0 = max(0, int(group[0] - 36))
            x1 = min(pixels.shape[1], int(group[-1] + 36))
            mid = (x0 + x1) / 2
            y0 = int(level_y(strip, mid, 13.2))
            y1 = min(pixels.shape[0], int(zero_y(strip, mid) + 8))
            band = Image.fromarray(pixels[y0:y1, x0:x1]).transpose(Image.ROTATE_90)
            band = band.resize((band.width * ZOOM, band.height * ZOOM), Image.LANCZOS)
            tile = Image.new("L", (band.width + MARGIN, band.height), 255)
            tile.paste(band, (MARGIN, 0))
            draw = ImageDraw.Draw(tile)
            for k, x in enumerate(group, start):
                row = (x1 - x) * ZOOM
                draw.text((14, row - 24), f"{k:>3} >", font=font, fill=0)
            path = OUT / f"{name}_{start:03d}.png"
            tile.save(fresh(path))
            tiles.append({"strip": name, "first": start, "last": start + len(group) - 1,
                          "path": str(path.relative_to(ROOT))})
    save_text(OUT / "tiles.json", json.dumps({"tiles": tiles, "geometry": geometry()}, indent=1))
    return tiles


if __name__ == "__main__":
    made = make_tiles()
    for strip, lines in ((k, v["lines"]) for k, v in geometry().items()):
        print(f"{strip}: {len(lines)} upright lines")
    print(f"{len(made)} tiles in {OUT.relative_to(ROOT)}")
