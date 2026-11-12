"""Stonehenge: the white model and its projected light, as plain geometry.

Reads topics/stonehenge/stones.json (see build_stones.py for where each value
comes from) and returns the generic model the phase look draws:

  matter  prisms that exist today. White.
  light   prisms that are inferred. Projected light.

Frame: metres, x east, y north, origin at the centre of the sarsen circle.
A prism is {"id", "group", "poly" [[x, y], ...], "base", "top", "taper"}.

Modelling choices that are not measurements are named constants below and are
listed in the film's README.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from shapely.affinity import rotate, translate
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
STONES = ROOT / "topics" / "stonehenge" / "stones.json"     # written by build_stones.py, kept in the repository

PLATE_RADIUS = 22.0            # metres of ground shown on the plate
LINTEL_RADIAL = 1.05           # circle lintel width across the ring (median radial size of the uprights is 1.10 m)
TRILITHON_LINTEL = 1.05        # thickness: lintel top of trilithon 51-52 (6.01 m) minus the top of upright 60 (4.96 m)
FALLEN_MIN, FALLEN_MAX = 0.35, 1.45
LOW_BLUESTONE = 0.25           # bluestones the scan does not resolve are drawn as low footprints


def _ring(poly: Polygon) -> list[list[float]]:
    return [[round(x, 3), round(y, 3)] for x, y in list(poly.exterior.coords)[:-1]]


def _soften(poly: Polygon) -> Polygon:
    """Remove the pixel stair-steps of the traced plan (3.5 cm pixels) without moving the outline."""
    smooth = poly.buffer(0.09, 8).buffer(-0.18, 8).buffer(0.09, 8)
    if smooth.geom_type != "Polygon" or smooth.is_empty:
        return poly
    return smooth.simplify(0.015)


def _sector(radius: float, width: float, az0: float, az1: float, steps: int = 8) -> Polygon:
    """Part of a ring between two compass bearings (degrees, clockwise from north)."""
    if az1 < az0:
        az1 += 360
    angles = np.radians(np.linspace(az0, az1, steps + 1))
    outer = [((radius + width / 2) * np.sin(a), (radius + width / 2) * np.cos(a)) for a in angles]
    inner = [((radius - width / 2) * np.sin(a), (radius - width / 2) * np.cos(a)) for a in angles[::-1]]
    return Polygon(outer + inner)


def _upright_footprint(x: float, y: float, azimuth: float, tangential: float, radial: float) -> Polygon:
    shape = box(-tangential / 2, -radial / 2, tangential / 2, radial / 2).buffer(-0.22).buffer(0.22, 6)
    return translate(rotate(shape, -azimuth, origin=(0, 0)), x, y)


def build_model() -> dict:
    data = json.loads(STONES.read_text(encoding="utf-8"))
    stones = data["stones"]
    by_id = {s["id"]: s for s in stones}
    sizes = data["measured_sizes"]
    circle = data["circle"]
    radius = circle["radius_m"]
    thickness = sizes["lintel_thickness_m"]
    ring_top = sizes["lintel_top_m"]
    slot_azimuth = lambda n: (circle["stone1_azimuth_deg"] + 12 * (n - 1)) % 360

    matter, light = [], []

    # ---- lintels in place: top from the scan over the two uprights they rest on
    lintel_bottom: dict[str, float] = {}
    for lintel in data["lintels_in_place"]:
        a, b = (by_id[i] for i in lintel["on"])
        top = round(float(np.median([a["h_max"], b["h_max"]])), 2)
        if int(lintel["id"]) <= 130:
            poly = _sector((a["r"] + b["r"]) / 2, LINTEL_RADIAL, a["azimuth"], b["azimuth"])
            base = round(top - thickness, 2)
            group = "circle_lintel"
        else:
            hull = unary_union([Polygon(a["poly"]), Polygon(b["poly"])]).minimum_rotated_rectangle
            poly = hull.buffer(-0.10)
            top = round(float(max(a["h_max"], b["h_max"])), 2)
            base = round(top - TRILITHON_LINTEL, 2)
            group = "trilithon_lintel"
        matter.append({"id": lintel["id"], "group": group, "poly": _ring(poly), "base": base, "top": top, "taper": 1.0})
        for upright in lintel["on"]:
            lintel_bottom[upright] = min(lintel_bottom.get(upright, 99.0), base)

    # ---- stones on the plan
    for s in stones:
        group, state = s["group"], s["state"]
        poly = _soften(Polygon(s["poly"]))
        if group == "bluestone":
            top = s["h_max"] if state == "standing" else LOW_BLUESTONE
            taper = 0.86 if state == "standing" else 1.0
        elif group == "altar_stone":
            top, taper = FALLEN_MIN, 1.0
        elif state == "standing":
            top = lintel_bottom.get(s["id"], s["h_max"])
            taper = 1.0 if group == "circle_upright" else 0.97
        else:
            top = float(np.clip(s["h_max"] or FALLEN_MIN, FALLEN_MIN, FALLEN_MAX))
            taper = 0.97
        matter.append({"id": s["id"], "group": group, "state": state, "poly": _ring(poly),
                       "base": 0.0, "top": round(float(top), 2), "taper": taper})

    # ---- inferred circle uprights and the lintels not in place
    upright_top = round(ring_top - thickness, 2)
    centre_az: dict[str, float] = {}
    centre_r: dict[str, float] = {}
    for n in range(1, 31):
        key = str(n)
        if key in by_id and by_id[key]["state"] == "standing":
            centre_az[key], centre_r[key] = by_id[key]["azimuth"], by_id[key]["r"]
        else:
            centre_az[key], centre_r[key] = slot_azimuth(n), radius
    for item in data["inferred_uprights"]:
        if item["group"] == "circle_upright":
            poly = _upright_footprint(item["x"], item["y"], item["azimuth"],
                                      sizes["upright_tangential_m"], sizes["upright_radial_m"])
            light.append({"id": item["id"], "group": "circle_upright", "on_site": item["on_site"],
                          "poly": _ring(poly), "base": 0.0, "top": upright_top, "taper": 1.0})
        else:
            top = item["h"] if item["id"] == "59" else round(item["h"] - 0.10, 2)
            light.append({"id": item["id"], "group": "trilithon_upright", "on_site": item["on_site"],
                          "poly": item["poly"], "base": 0.0, "top": top, "taper": 0.97})
    light_by_id = {p["id"]: p for p in light}
    for item in data["inferred_lintels"]:
        a, b = item["on"]
        if item["group"] == "circle_lintel":
            poly = _sector((centre_r[a] + centre_r[b]) / 2, LINTEL_RADIAL, centre_az[a], centre_az[b])
            base, top = upright_top, ring_top
        else:
            parts = [Polygon(light_by_id[i]["poly"]) if i in light_by_id else Polygon(by_id[i]["poly"]) for i in (a, b)]
            poly = unary_union(parts).minimum_rotated_rectangle.buffer(-0.10)
            base = min(light_by_id[i]["top"] if i in light_by_id else by_id[i]["h_max"] for i in (a, b))
            base = round(float(base) - (0.10 if item["id"] == "156" else 0.0), 2)
            top = round(base + TRILITHON_LINTEL, 2)
        light.append({"id": item["id"], "group": item["group"], "on_site": item["on_site"],
                      "poly": _ring(poly), "base": base, "top": top, "taper": 1.0})

    inside = lambda prism: max(np.hypot(x, y) for x, y in prism["poly"]) < PLATE_RADIUS - 0.4
    assert all(inside(p) for p in matter + light), "a stone falls off the plate"

    counts = data["counts"]
    return {
        "frame": data["frame"],
        "plate": {"radius": PLATE_RADIUS, "scale_bar_m": 10, "axis_azimuth_deg": circle["axis_azimuth_deg"]},
        "matter": matter,
        "light": light,
        "pick_order": [str(n) for n in circle["standing"]],
        "counts": {
            "circle_uprights_standing": counts["circle_uprights_standing"],
            "circle_uprights_total": 30,
            "circle_lintels_in_place": len(counts["circle_lintels_in_place"]),
            "trilithon_uprights_standing": len(counts["trilithon_uprights_standing"]),
            "trilithons_complete": len(counts["trilithon_lintels_in_place"]),
            "light_circle_uprights": sum(1 for p in light if p["group"] == "circle_upright"),
            "light_circle_lintels": sum(1 for p in light if p["group"] == "circle_lintel"),
        },
        "measured": sizes,
        "registration": data["registration"],
        "sources": data["sources"],
    }


if __name__ == "__main__":
    model = build_model()
    print(json.dumps({k: model[k] for k in ("plate", "counts", "measured", "pick_order")}, indent=1))
    print("matter prisms:", len(model["matter"]), "| light prisms:", len(model["light"]))
    for p in model["matter"]:
        if p["group"] in ("circle_lintel", "trilithon_lintel"):
            print("  lintel", p["id"], "base", p["base"], "top", p["top"])
    for p in model["light"]:
        if p["group"] != "circle_lintel":
            print("  light ", p["id"], p["group"], "base", p["base"], "top", p["top"], p.get("on_site"))
