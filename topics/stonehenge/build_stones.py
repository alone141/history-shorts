"""Stonehenge: one table of stones, each with its published identity and measured height.

What comes from where
  outline, upright/fallen state   Nash et al. 2021, PLoS ONE 16(8): e0254760, Fig 1B (CC BY 4.0),
                                  digitised by digitise_plan.py
  stone numbers                   the numbers printed on that figure (Petrie's system)
  heights                         Environment Agency National LIDAR Programme point cloud,
                                  tile SU1040, flown 4 April 2021 (OGL v3.0), above the
                                  LIDAR Composite DTM 2022 1 m ground model
  where the missing stones stood  30 even positions on the circle fitted through the standing
                                  uprights; the two fallen trilithon uprights mirrored across
                                  the solstice axis (Darvill 2022, Antiquity 96: 319-335, Fig 8
                                  and p. 324: the horseshoe sits symmetrically astride the axis)

Output: topics/stonehenge/stones.json (kept in the repository, so the film can be
made without downloading the laser scan) and build/stonehenge/stones_check.png

Run:  python -m topics.stonehenge.build_stones
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw, ImageFont
from scipy.optimize import minimize
from shapely import STRtree
from shapely import points as shapely_points
from shapely.affinity import affine_transform
from shapely.geometry import Polygon
from engine.files import fresh, write_text as save_text

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "build" / "stonehenge"
DATA = ROOT / "data" / "stonehenge"

# Labels read from the published figure, keyed by rough position (radius m, azimuth deg)
TRILITHON_UPRIGHTS = {"51": 104, "52": 122, "53": 165, "54": 183, "56": 240, "57": 278, "58": 297, "60": 353}
FALLEN = {
    "8": (17.8, 139), "9a": (16.2, 151), "9b": (18.3, 151), "12": (16.8, 186), "14": (12.8, 211),
    "15": (11.6, 225), "19": (18.2, 272), "25": (16.6, 337), "26": (15.4, 354),
    "120": (17.9, 278), "127": (15.9, 0),
    "55a": (4.3, 222), "55b": (8.1, 222), "59a": (6.6, 339), "59b": (4.1, 353), "59c": (2.9, 4),
    "156": (3.7, 259), "160a": (5.3, 10), "160b": (4.6, 33), "160c": (4.2, 65),
}
# Lintels in place today, and the two uprights each one rests on
LINTELS_IN_PLACE = {"130": ("29", "30"), "101": ("30", "1"), "102": ("1", "2"), "105": ("4", "5"),
                    "107": ("6", "7"), "122": ("21", "22"),
                    "152": ("51", "52"), "154": ("53", "54"), "158": ("57", "58")}
TRILITHON_PAIRS = {"152": ("51", "52"), "154": ("53", "54"), "156": ("55", "56"), "158": ("57", "58"), "160": ("59", "60")}
MIRROR = {"55": "56", "59": "52"}       # fallen trilithon upright -> its standing mirror image
TALL = 2.0                              # metres above ground: a point this high is on a standing stone


def ground_model():
    with zipfile.ZipFile(DATA / "lidar" / "SU1040_dtm_2022.zip") as archive:
        names = archive.namelist()
        tif = next(n for n in names if n.lower().endswith(".tif"))
        tfw = next(n for n in names if n.lower().endswith(".tfw"))
        grid = tifffile.imread(io.BytesIO(archive.read(tif)))
        a, _, _, e, c, f = [float(v) for v in archive.read(tfw).decode().split()]
    west, north = c - a / 2, f - e / 2

    def ground(x, y):
        fx, fy = x - west - 0.5, north - y - 0.5
        c0, r0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
        tx, ty = fx - c0, fy - r0

        def cell(r, col):
            return grid[np.clip(r, 0, grid.shape[0] - 1), np.clip(col, 0, grid.shape[1] - 1)]
        return (cell(r0, c0) * (1 - tx) * (1 - ty) + cell(r0, c0 + 1) * tx * (1 - ty)
                + cell(r0 + 1, c0) * (1 - tx) * ty + cell(r0 + 1, c0 + 1) * tx * ty)
    return ground


def place(polygon: Polygon, q) -> Polygon:
    """Plan metres (x east, y north) -> grid metres: rotate by q[2], scale q[3], shift."""
    cx, cy, theta, scale = q
    a, b = scale * np.cos(theta), scale * np.sin(theta)
    return affine_transform(polygon, [a, -b, b, a, cx, cy])


def register(uprights: list[Polygon], tall_xy: np.ndarray, start) -> np.ndarray:
    """Fit the plan to the scan: tall scan points should fall on upright sarsens."""
    cloud = shapely_points(tall_xy)

    def cost(q):
        polys = [place(p, q) for p in uprights]
        nearest = STRtree(polys).nearest(cloud)
        d = np.array([polys[i].distance(pt) for i, pt in zip(nearest, cloud)])
        return -np.exp(-(d / 0.35) ** 2).sum()

    best = None
    for dx in np.arange(-2.0, 2.1, 0.5):
        for dy in np.arange(-2.0, 2.1, 0.5):
            for deg in (-2, -1, 0, 1, 2):
                q = [start[0] + dx, start[1] + dy, np.radians(deg), 1.0]
                value = cost(q)
                if best is None or value < best[0]:
                    best = (value, q)
    q0 = np.array(best[1])
    steps = np.array([0.3, 0.3, np.radians(0.7), 0.01])
    simplex = np.vstack([q0] + [q0 + np.eye(4)[i] * steps[i] for i in range(4)])
    result = minimize(cost, q0, method="Nelder-Mead",
                      options={"initial_simplex": simplex, "xatol": 1e-4, "fatol": 1e-4, "maxiter": 1500})
    return result.x


def main() -> None:
    plan = json.loads((BUILD / "plan_outlines.json").read_text(encoding="utf-8"))
    survey = json.loads((BUILD / "survey.json").read_text(encoding="utf-8"))
    points = np.load(BUILD / "points_window.npy")
    ground = ground_model()
    height = points[:, 2] - ground(points[:, 0], points[:, 1])

    outlines = plan["outlines"]
    start = survey["centre"]
    within = np.hypot(points[:, 0] - start[0], points[:, 1] - start[1]) < 26
    tall_xy = points[within & (height >= TALL)][:, :2]
    uprights = [Polygon(o["poly"]) for o in outlines if o["kind"] == "upright_sarsen"]
    q = register(uprights, tall_xy, start)

    placed = [place(p, q) for p in uprights]
    cloud = shapely_points(tall_xy)
    nearest = STRtree(placed).nearest(cloud)
    dist = np.array([placed[i].distance(pt) for i, pt in zip(nearest, cloud)])
    fit = {"tall_points": int(len(tall_xy)), "inside_upright": int((dist == 0).sum()),
           "within_0.3m": int((dist <= 0.3).sum()), "beyond_1m": int((dist > 1).sum()),
           "centre_grid": [round(float(q[0]), 2), round(float(q[1]), 2)],
           "rotation_deg": round(float(np.degrees(q[2])), 2), "scale": round(float(q[3]), 4)}

    # ---- measure every outline against the scan
    xy = points[:, :2]
    for o in outlines:
        footprint = place(Polygon(o["poly"]), q)
        box = footprint.buffer(0.3).bounds
        candidates = np.where((xy[:, 0] >= box[0]) & (xy[:, 0] <= box[2]) & (xy[:, 1] >= box[1]) & (xy[:, 1] <= box[3]))[0]
        loose = footprint.buffer(0.3)
        inside = [i for i in candidates if loose.contains(shapely_points(xy[i]))]
        hs = height[inside] if inside else np.array([])
        o["n_points"] = len(inside)
        o["h_max"] = round(float(hs.max()), 2) if len(hs) else None
        o["h_p75"] = round(float(np.percentile(hs, 75)), 2) if len(hs) else None

    # ---- names
    circle = [o for o in outlines if o["kind"] == "upright_sarsen" and o["r"] > 13.5]
    az = np.array([o["azimuth"] for o in circle])
    # phase of the 12-degree lattice: stone 1 is the first position clockwise of the north-east axis
    phases = np.arange(0, 12, 0.01)
    spread = [np.abs(((az - p + 6) % 12) - 6).sum() for p in phases]
    phase = float(phases[int(np.argmin(spread))])
    lattice = phase + 12 * np.round((55.6 - phase) / 12)          # the lattice position nearest stone 1 on the figure
    for o in circle:
        o["id"] = str(int(round((o["azimuth"] - lattice) / 12)) % 30 + 1)
        o["group"], o["state"] = "circle_upright", "standing"
    for o in outlines:
        if o["kind"] == "upright_sarsen" and o["r"] <= 13.5:
            name = min(TRILITHON_UPRIGHTS, key=lambda k: abs(((o["azimuth"] - TRILITHON_UPRIGHTS[k] + 180) % 360) - 180))
            o["id"], o["group"], o["state"] = name, "trilithon_upright", "standing"
        elif o["kind"] == "fallen_sarsen":
            def gap(key):
                r, a = FALLEN[key]
                return np.hypot(o["r"] * np.sin(np.radians(o["azimuth"])) - r * np.sin(np.radians(a)),
                                o["r"] * np.cos(np.radians(o["azimuth"])) - r * np.cos(np.radians(a)))
            name = min(FALLEN, key=gap)
            assert gap(name) < 1.0, (o["index"], o["r"], o["azimuth"], name)
            number = int("".join(ch for ch in name if ch.isdigit()))
            o["id"], o["state"] = name, "fallen"
            o["group"] = ("circle_upright" if number <= 30 else "trilithon_upright" if number <= 60
                          else "circle_lintel" if number <= 130 else "trilithon_lintel")
        elif o["kind"] == "sandstone":
            o["id"], o["group"], o["state"] = "80", "altar_stone", "fallen"
        elif o["kind"] == "bluestone":
            o["group"] = "bluestone"
    blue = sorted((o for o in outlines if o["kind"] == "bluestone"), key=lambda o: (o["r"] < 9, o["azimuth"]))
    for n, o in enumerate(blue, 1):
        o["id"] = f"b{n:02d}"
        o["state"] = "standing" if (o["h_max"] or 0) >= 1.0 else "low"
    ids = [o["id"] for o in outlines]
    assert len(set(ids)) == len(ids) - 1, "only the Altar Stone may appear twice"   # two visible parts of stone 80

    by_id = {o["id"]: o for o in outlines}
    standing_circle = sorted(int(o["id"]) for o in circle)
    radius = float(np.mean([o["r"] for o in circle]))
    axis_az = (lattice - 6) % 360                              # between stones 30 and 1

    def slot_xy(n: int, r: float = radius):
        a = np.radians(lattice + 12 * (n - 1))
        return float(r * np.sin(a)), float(r * np.cos(a))

    # ---- measured sizes of the standing circle uprights (for the inferred ones)
    free = [by_id[str(n)] for n in standing_circle if not any(str(n) in pair for pair in LINTELS_IN_PLACE.values())]
    capped = [by_id[str(n)] for n in standing_circle if any(str(n) in pair for pair in LINTELS_IN_PLACE.values())]
    sizes = {
        "upright_tangential_m": round(float(np.median([o["length"] for o in circle])), 2),
        "upright_radial_m": round(float(np.median([o["width"] for o in circle])), 2),
        "uncapped_upright_top_m": round(float(np.median([o["h_max"] for o in free if o["id"] != "11"])), 2),
        "lintel_top_m": round(float(np.median([o["h_max"] for o in capped])), 2),
    }
    sizes["lintel_thickness_m"] = round(sizes["lintel_top_m"] - sizes["uncapped_upright_top_m"], 2)

    # ---- inferred: circle uprights not standing, lintels not in place, two trilithon uprights
    inferred = []
    for n in range(1, 31):
        if n in standing_circle:
            continue
        x, y = slot_xy(n)
        present = [k for k in by_id if k.rstrip("ab") == str(n) and by_id[k]["state"] == "fallen"]
        inferred.append({"id": str(n), "group": "circle_upright", "x": round(x, 3), "y": round(y, 3),
                         "azimuth": round((lattice + 12 * (n - 1)) % 360, 2),
                         "on_site": "fallen" if present else "missing"})
    lintels_inferred = []
    for n in range(1, 31):
        name = "101" if n == 1 else str(100 + n)
        pair = ("30", "1") if n == 1 else (str(n - 1), str(n))
        if name in LINTELS_IN_PLACE:
            continue
        lintels_inferred.append({"id": name, "group": "circle_lintel", "on": list(pair),
                                 "on_site": "fallen" if name in by_id else "missing"})
    ax = np.array([np.sin(np.radians(axis_az)), np.cos(np.radians(axis_az))])

    def mirror(pt):
        pt = np.array(pt)
        return (2 * np.dot(pt, ax) * ax - pt).tolist()
    for fallen_id, twin in MIRROR.items():
        t = by_id[twin]
        inferred.append({"id": fallen_id, "group": "trilithon_upright", "mirror_of": twin,
                         "poly": [[round(v, 3) for v in mirror(p)] for p in t["poly"]][::-1],
                         "x": round(mirror([t["x"], t["y"]])[0], 3), "y": round(mirror([t["x"], t["y"]])[1], 3),
                         "h": by_id["56" if fallen_id == "55" else "60"]["h_max"], "on_site": "fallen"})
    for name in ("156", "160"):
        lintels_inferred.append({"id": name, "group": "trilithon_lintel", "on": list(TRILITHON_PAIRS[name]), "on_site": "fallen"})

    stones = [{k: o[k] for k in ("id", "group", "state", "kind", "x", "y", "r", "azimuth", "area", "length", "width",
                                 "bearing", "n_points", "h_max", "h_p75", "poly")} for o in outlines]
    result = {
        "sources": {
            "outlines": plan["source"],
            "heights": "Environment Agency National LIDAR Programme point cloud, tile SU1040, flown 2021-04-04; "
                       "LIDAR Composite DTM 2022 1 m. Open Government Licence v3.0",
            "inferred": "Darvill 2022, Antiquity 96(386): 319-335, doi:10.15184/aqy.2022.5, CC BY 4.0",
        },
        "frame": "metres; x east, y north; origin at the centre of the circle through the standing uprights",
        "registration": fit,
        "circle": {"radius_m": round(radius, 3), "stone1_azimuth_deg": round(lattice % 360, 2),
                   "axis_azimuth_deg": round(axis_az, 2), "standing": standing_circle},
        "measured_sizes": sizes,
        "counts": {
            "circle_uprights_standing": len(standing_circle),
            "circle_uprights_fallen_on_site": sorted({k.rstrip("ab") for k, o in by_id.items()
                                                     if o["group"] == "circle_upright" and o["state"] == "fallen"}, key=int),
            "circle_lintels_in_place": [k for k in LINTELS_IN_PLACE if int(k) <= 130],
            "trilithon_uprights_standing": sorted(k for k, o in by_id.items() if o["group"] == "trilithon_upright" and o["state"] == "standing"),
            "trilithon_lintels_in_place": [k for k in LINTELS_IN_PLACE if int(k) > 130],
            "bluestones_outlined": len(blue),
        },
        "stones": stones,
        "lintels_in_place": [{"id": k, "on": list(v)} for k, v in LINTELS_IN_PLACE.items()],
        "inferred_uprights": inferred,
        "inferred_lintels": lintels_inferred,
        "ditch": [], "bank": [],
    }
    # earthwork lines from the OpenStreetMap extract, moved into the same frame
    theta, scale = q[2], q[3]

    def to_plan(pts):
        d = (np.array(pts) - q[:2]) / scale
        c, s = np.cos(-theta), np.sin(-theta)
        return np.c_[d[:, 0] * c - d[:, 1] * s, d[:, 0] * s + d[:, 1] * c].round(2).tolist()
    for key in ("ditch", "bank"):
        result[key] = [{"closed": w["closed"], "name": w["name"], "pts": to_plan(w["pts"])} for w in survey[key]]
    for s in survey["stones"]:
        if s["name"] in ("Heel Stone", "Slaughter Stone", "Station Stone"):
            result.setdefault("outliers", []).append({"name": s["name"], "poly": to_plan(s["poly"]), "h_max": s["h_max"],
                                                      "source": "OpenStreetMap footprint, (c) OpenStreetMap contributors, ODbL"})
    save_text(ROOT / "topics" / "stonehenge" / "stones.json", json.dumps(result, indent=1))

    # ---- check picture
    S, half = 30.0, 22.0
    size = int(2 * half * S)
    canvas = Image.new("RGB", (size, size), (250, 250, 248))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 13)
    except OSError:
        font = ImageFont.load_default()

    def pix(x, y):
        return ((x + half) * S, (half - y) * S)
    colours = {"standing": (60, 60, 60), "fallen": (225, 150, 70), "low": (120, 190, 220)}
    for o in stones:
        fill = colours[o["state"]] if o["group"] != "bluestone" else ((40, 110, 170) if o["state"] == "standing" else (150, 205, 235))
        draw.polygon([pix(x, y) for x, y in o["poly"]], fill=fill, outline=(0, 0, 0))
        label = o["id"] if o["group"] != "bluestone" else ""
        hx = f"{o['h_max']:.1f}" if o["h_max"] is not None else "-"
        draw.text(pix(o["x"] * 1.0 + 0.9, o["y"] + 0.5), f"{label} {hx}".strip(), fill=(170, 0, 0), font=font)
    for item in inferred:
        if "poly" in item:
            draw.polygon([pix(x, y) for x, y in item["poly"]], outline=(0, 160, 200))
        else:
            px, py = pix(item["x"], item["y"])
            draw.ellipse([px - 14, py - 14, px + 14, py + 14], outline=(0, 160, 200), width=2)
        draw.text(pix(item["x"] - 0.3, item["y"] + 0.3), item["id"], fill=(0, 120, 170), font=font)
    a = np.radians(axis_az)
    draw.line([pix(-21 * np.sin(a), -21 * np.cos(a)), pix(21 * np.sin(a), 21 * np.cos(a))], fill=(200, 60, 60), width=1)
    canvas.save(fresh(BUILD / "stones_check.png"))

    print("registration:", fit)
    print("circle radius", round(radius, 2), "m | stone 1 azimuth", round(lattice % 360, 2), "| axis", round(axis_az, 2))
    print("standing circle uprights:", len(standing_circle), standing_circle)
    print("measured sizes:", sizes)
    print("counts:", {k: (v if not isinstance(v, list) else f"{len(v)} {v}") for k, v in result["counts"].items()})
    print(" id    group              state     r    azim  len  wid  n  hmax  hp75")
    for o in sorted(stones, key=lambda o: (o["group"], o["id"].zfill(4))):
        hm = f"{o['h_max']:5.2f}" if o["h_max"] is not None else "    -"
        hp = f"{o['h_p75']:5.2f}" if o["h_p75"] is not None else "    -"
        print(f" {o['id']:<5} {o['group']:<18} {o['state']:<8} {o['r']:5.2f} {o['azimuth']:6.1f} {o['length']:4.2f} {o['width']:4.2f} {o['n_points']:2d} {hm} {hp}")
    print("inferred uprights:", [(i["id"], i["on_site"]) for i in inferred])
    print("inferred lintels:", len(lintels_inferred))


if __name__ == "__main__":
    main()
