"""The Great Pyramid: the white model and its projected light, as plain geometry.

Reads topics/giza/courses.json (the course levels of Petrie 1883, Plate VIII; see
build_courses.py) and returns the generic model the phase look draws:

  matter  the courses of core masonry that are there today. White.
  light   the casing and apex, which are not. Projected light.

Frame: model units, x east, y north, origin on the pyramid's axis at pavement level.
One model unit is UNIT_M metres, so that the pyramid fits the plate the renderer was
built round. A prism is {"id", "group", "poly" [[x, y], ...], "base", "top", "taper"}.

What is measured and what is a modelling choice is set out in the film's FACTS.md.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COURSES = ROOT / "topics" / "giza" / "courses.json"     # written by build_courses.py, kept in the repository

INCH = 0.0254
UNIT_M = 8.2                   # metres per model unit
PLATE_RADIUS = 22.0            # model units (180 m of ground)

# Petrie 1883, sections 20 to 26 (inches); every figure checked on the page scans (pp. 38 to 44)
CASING_BASE = 9068.8           # mean side of the casing at the pavement, +/- .5 (p. 43)
ORIGINAL_HEIGHT = 5776.0       # +/- 7.0, from the base and the face angle 51 deg 52 min +/- 2 min (p. 43)
CORE_INSIDE_CASING = 33.7      # mean of the eight corner values on Plate X (27.7 to 39.4): the plane sighted over
                               # the edges of the core masonry stands this far inside the casing line, on the pavement
SUMMIT_LEVEL = 5408.55         # mean of 5407.9 (N.E.) and 5409.2 (S.W.): the flat top, top of course 201 (p. 43)
SUMMIT = {"n": 224.5, "e": 214.1, "s": 215.0, "w": 217.6}    # the same planes from the pyramid's axis at that level (p. 43)

# Modelling choices (not measurements)
STEP_BEVEL = 0.012             # model units: a hair of chamfer so each step edge catches the light
# Courses 202 and 203 are a remnant of stones in the middle of the flat top. Petrie gives their levels (N.E. only)
# but not their outline, so they are drawn as two small slabs at the centre: this share of the plane's width.
SUMMIT_REMNANT = {202: 0.62, 203: 0.34}


def _unit(inches: float) -> float:
    return inches * INCH / UNIT_M


def core_half_width(side: str, level_in: float) -> float:
    """Distance (inches) from the axis to the mean plane of the core masonry on one side, at a level."""
    base = CASING_BASE / 2 - CORE_INSIDE_CASING
    return base + (SUMMIT[side] - base) * level_in / SUMMIT_LEVEL


def build_model() -> dict:
    data = json.loads(COURSES.read_text(encoding="utf-8"))
    matter, levels_m = [], []
    below = 0.0
    for course in data["courses"]:
        both = [v for v in (course["ne_in"], course["sw_in"]) if v is not None]
        top = sum(both) / len(both)                     # mean of the two corners; N.E. alone for the last two
        # each course is a flat-sided slab whose top edge touches, on each side, the plane Petrie sighted over
        # the prominent edges of the core masonry (drawn straight between the base and the flat top)
        n, e, s, w = (core_half_width(side, top) for side in "nesw")
        share = SUMMIT_REMNANT.get(course["n"], 1.0)
        n, e, s, w = (v * share for v in (n, e, s, w))
        poly = [[-_unit(w), -_unit(s)], [_unit(e), -_unit(s)], [_unit(e), _unit(n)], [-_unit(w), _unit(n)]]
        matter.append({"id": str(course["n"]), "group": "course", "state": "standing",
                       "poly": [[round(x, 4), round(y, 4)] for x, y in poly],
                       "base": round(_unit(below), 4), "top": round(_unit(top), 4), "taper": 1.0, "bevel": STEP_BEVEL})
        levels_m.append(round(top * INCH, 2))
        below = top
    # the part of each course's top that the next course stands on is hidden, and is not drawn
    for lower, upper in zip(matter[:-1], matter[1:]):
        lower["cap_hole"] = [[round(x * 0.999, 4), round(y * 0.999, 4)] for x, y in upper["poly"]]

    # the casing as built: one square pyramid, in two volumes so that the film can light them apart.
    # "casing" runs from the pavement to the level of today's flat top; "apex" is everything above that.
    half = _unit(CASING_BASE / 2)
    square = lambda h: [[-h, -h], [h, -h], [h, h], [-h, h]]
    left = 1 - SUMMIT_LEVEL / ORIGINAL_HEIGHT            # share of the base width still left at the summit level
    light = [
        {"id": "casing", "group": "casing", "on_site": True, "poly": square(half),
         "base": 0.0, "top": round(_unit(SUMMIT_LEVEL), 4), "taper": left, "bevel": 1e-4, "cap": False, "rings": (True, False)},
        {"id": "apex", "group": "apex", "on_site": True, "poly": square(half * left),
         "base": round(_unit(SUMMIT_LEVEL), 4), "top": round(_unit(ORIGINAL_HEIGHT), 4), "taper": 0.004, "bevel": 0.01,
         "rings": (False, False)},
    ]

    return {
        "frame": "model units of %.1f m; x east, y north; origin on the axis at pavement level" % UNIT_M,
        "plate": {"radius": PLATE_RADIUS, "scale_bar_m": 100, "unit_m": UNIT_M, "axis_azimuth_deg": 0},
        "matter": matter,
        "light": light,
        "pick_order": [p["id"] for p in matter],
        "levels_m": levels_m,
        "original_height_m": round(ORIGINAL_HEIGHT * INCH, 2),
        "counts": {"courses": len(matter), "present_top_m": levels_m[-1],
                   "platform_m": round(SUMMIT_LEVEL * INCH, 2),
                   "missing_m": round(ORIGINAL_HEIGHT * INCH - levels_m[-1], 2)},
        "sources": data["source"],
    }


if __name__ == "__main__":
    model = build_model()
    print(json.dumps({k: model[k] for k in ("plate", "counts", "original_height_m")}, indent=1))
    print("matter prisms:", len(model["matter"]), "| light prisms:", len(model["light"]))
    for p in model["matter"][:2] + model["matter"][-3:]:
        print("  course", p["id"], "base", p["base"], "top", p["top"], "half-width east", p["poly"][1][0])
