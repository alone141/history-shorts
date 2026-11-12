"""Stonehenge: digitise the published plan of the stones as they are today.

Source: Nash, D.J. et al. 2021. Petrological and geochemical characterisation of
the sarsen stones at Stonehenge. PLoS ONE 16(8): e0254760, Fig 1B.
https://doi.org/10.1371/journal.pone.0254760  (CC BY 4.0)

The figure draws every stone as a flat-coloured outline (upright sarsen, fallen
sarsen, sandstone, bluestone) with a 10 m scale bar and north up. This script
reads the outlines by colour; it does not redraw or interpret them.

Output: build/stonehenge/plan_outlines.json  (metres, x east, y north, origin at
the centre of the circle fitted through the upright circle sarsens) and
build/stonehenge/plan_outlines_check.png (each outline with its index).

Run:  python -m topics.stonehenge.digitise_plan
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from scipy.optimize import least_squares
from shapely.geometry import Polygon
from skimage import measure
from engine.files import fresh, write_text as save_text

ROOT = Path(__file__).resolve().parents[2]
FIGURE = ROOT / "data" / "stonehenge" / "refs" / "nash_2021_plosone_fig1.png"
OUT = ROOT / "build" / "stonehenge"

# flat fill colours read from the figure's own legend
CLASSES = {
    "upright_sarsen": (255, 153, 153),
    "fallen_sarsen": (255, 204, 153),
    "sandstone": (51, 204, 102),
    "bluestone": (153, 255, 255),
}
SCALE_BAR_PX = 289.0      # outer edges of the 10 m scale bar, columns 670 to 959
SCALE_BAR_M = 10.0
OUTLINE_HALF_PX = 1.5     # the black outline is about 3 px wide, centred on the edge
MIN_AREA_PX = 30


def load_panel_b() -> np.ndarray:
    image = np.array(Image.open(FIGURE).convert("RGB")).astype(int)
    return image[image.shape[0] // 2:]


def components(panel: np.ndarray, colour: tuple[int, int, int]) -> list[np.ndarray]:
    """Boolean masks, one per connected patch of this fill colour."""
    mask = np.abs(panel - np.array(colour)).max(axis=2) <= 24
    mask[900:, :330] = False          # the legend swatches
    mask[:200, 990:] = False          # the inset location map
    labels, count = ndimage.label(mask)
    out = []
    for index in range(1, count + 1):
        patch = labels == index
        if patch.sum() < MIN_AREA_PX:
            continue
        # close the slits left by dashed lintel lines and fill enclosed holes,
        # one patch at a time so neighbouring stones can never merge
        closed = ndimage.binary_closing(patch, structure=np.ones((7, 7)), border_value=0)
        out.append(ndimage.binary_fill_holes(closed))
    return out


def outline(mask: np.ndarray) -> Polygon:
    padded = np.pad(mask.astype(float), 2)
    contour = max(measure.find_contours(padded, 0.5), key=len) - 2
    polygon = Polygon([(c, r) for r, c in contour]).buffer(0)
    return polygon.buffer(OUTLINE_HALF_PX).simplify(0.5)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    panel = load_panel_b()
    px_per_m = SCALE_BAR_PX / SCALE_BAR_M
    found = []
    for kind, colour in CLASSES.items():
        for mask in components(panel, colour):
            polygon = outline(mask)
            if polygon.is_empty or polygon.geom_type != "Polygon":
                continue
            found.append({"kind": kind, "px": polygon})

    # centre: circle through upright sarsens lying 12.5 to 18 m from a first guess
    guess = np.array([605.0, 520.0])
    ring = np.array([[f["px"].centroid.x, f["px"].centroid.y] for f in found
                     if f["kind"] == "upright_sarsen"
                     and 12.5 < np.hypot(*(np.array([f["px"].centroid.x, f["px"].centroid.y]) - guess)) / px_per_m < 18])

    def residual(q):
        return np.hypot(ring[:, 0] - q[0], ring[:, 1] - q[1]) - q[2]

    cx, cy, radius_px = least_squares(residual, [guess[0], guess[1], 15.5 * px_per_m]).x

    def to_metres(polygon: Polygon) -> list[list[float]]:
        return [[round((x - cx) / px_per_m, 3), round(-(y - cy) / px_per_m, 3)]
                for x, y in list(polygon.exterior.coords)[:-1]]

    records = []
    for index, item in enumerate(sorted(found, key=lambda f: (f["px"].centroid.y, f["px"].centroid.x))):
        polygon = item["px"]
        metres = Polygon(to_metres(polygon))
        mx, my = metres.centroid.x, metres.centroid.y
        rect = np.array(metres.minimum_rotated_rectangle.exterior.coords)[:4]
        sides = sorted(((float(np.hypot(*(rect[(i + 1) % 4] - rect[i]))), rect[(i + 1) % 4] - rect[i]) for i in range(2)),
                       key=lambda s: -s[0])
        records.append({
            "index": index,
            "kind": item["kind"],
            "px_centroid": [round(polygon.centroid.x, 1), round(polygon.centroid.y, 1)],
            "x": round(mx, 3), "y": round(my, 3),
            "r": round(float(np.hypot(mx, my)), 2),
            "azimuth": round(float(np.degrees(np.arctan2(mx, my)) % 360), 1),
            "area": round(metres.area, 2),
            "length": round(sides[0][0], 2), "width": round(sides[1][0], 2),
            "bearing": round(float(np.degrees(np.arctan2(sides[0][1][0], sides[0][1][1])) % 180), 1),
            "poly": to_metres(polygon),
        })

    result = {
        "source": "Nash et al. 2021, PLoS ONE 16(8): e0254760, Fig 1B, CC BY 4.0",
        "px_per_m": px_per_m,
        "centre_px": [round(cx, 2), round(cy, 2)],
        "circle_radius_m": round(radius_px / px_per_m, 3),
        "circle_fit_stones": int(len(ring)),
        "outlines": records,
    }
    save_text(OUT / "plan_outlines.json", json.dumps(result, indent=1))

    check = Image.fromarray(panel.astype(np.uint8)).convert("RGB")
    draw = ImageDraw.Draw(check)
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    by_index = {r["index"]: r for r in records}
    for item in sorted(found, key=lambda f: (f["px"].centroid.y, f["px"].centroid.x)):
        pass
    for record in records:
        pts = [(cx + x * px_per_m, cy - y * px_per_m) for x, y in record["poly"]]
        draw.line(pts + [pts[0]], fill=(0, 0, 255), width=1)
        px, py = record["px_centroid"]
        draw.text((px - 8, py - 8), str(record["index"]), fill=(0, 0, 160), font=font)
    draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], outline=(0, 0, 255), width=2)
    check.save(fresh(OUT / "plan_outlines_check.png"))

    kinds = {}
    for record in records:
        kinds[record["kind"]] = kinds.get(record["kind"], 0) + 1
    print("outlines:", kinds, "| circle radius", result["circle_radius_m"], "m from", len(ring), "stones | centre px", result["centre_px"])
    print(" idx kind             r    azim  area   len   wid  bear   px")
    for record in sorted(records, key=lambda r: (r["kind"], r["r"] > 12.5, r["azimuth"])):
        print(f" {record['index']:3d} {record['kind']:<15} {record['r']:5.2f} {record['azimuth']:6.1f} {record['area']:5.2f} "
              f"{record['length']:5.2f} {record['width']:5.2f} {record['bearing']:5.1f}  {record['px_centroid']}")


if __name__ == "__main__":
    main()
