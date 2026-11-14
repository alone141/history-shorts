"""Petrie 1883, Plate VIII: from the readings of the plate to the course table.

    python -m topics.giza.build_courses        # writes topics/giza/courses.json and prints the checks

Input: topics/giza/plate_readings.json, the record of how the plate was read. Every
numeral was read twice, independently, from the tiles cut by plate_tiles.py; rows on
which the two readings differed, or either reader was unsure, were read a third time.

The plate carries three independent checks on those readings, and all are used here:

  1. The strips of the fold-out overlap, so some courses were read from two scans.
  2. The upright line of each course is drawn at 1/200 scale along the plate, so its
     position gives the level again, to about two inches (the paper has stretched a
     little, so each line is compared with its neighbours, not with the whole strip).
  3. Each course's thickness is drawn as cross-lines at 1/10 scale ("the readings at
     the four corners"), so the difference between one level and the next must sit
     on one of them, to about half an inch.

A tenth of an inch can only be checked by the double reading. Rows that fail a check
are listed; nothing is corrected silently. The few readings settled against the drawing
(two are slips on the plate itself) are in FIXES below, each with its reason.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from engine.files import write_text as save_text
from topics.giza.plate_tiles import PX_PER_10IN, STRIPS, level_y, scan, upright_lines

ROOT = Path(__file__).resolve().parents[2]
READINGS = ROOT / "topics" / "giza" / "plate_readings.json"
OUT = ROOT / "topics" / "giza" / "courses.json"
INCH = 0.0254
POSITION_LIMIT_IN = 2.5        # check 2: how far a level may sit from its upright line
THICKNESS_LIMIT_IN = 0.6       # check 3: how far a thickness may sit from a drawn cross-line

# (strip, line index, corner) -> (value, reason): the few readings settled against the plate's own drawing and text.
FIXES: dict[tuple[str, int, str], tuple[str, str]] = {
    ("lower", 2, "sw"): ("111.2", "the plate's brace reads 110.0 and 110.2; Petrie's text (p. 41) prints +111.2 for the S.W. "
                                  "second course, and the plate's own cross-lines for courses 2 and 3 (53.5 and 44.2 in) fit 111.2"),
    ("lower", 70, "ne"): ("2237.7", "the plate prints 2337.7, a slip of the pen: the line stands between 2209.9 and 2266.5, "
                                    "and its position and its cross-line (27.8 in) give 2237.7"),
    ("lower", 70, "sw"): ("2237.9", "the plate prints 2337.9; as for the N.E. figure, position and cross-line (28.1 in) give 2237.9"),
    ("middle", 45, "sw"): ("3472.8", "the last digit is nearly filled with ink (8, 0 or 6 by the outline); the cross-line of the "
                                     "course above (23.2 in, to 3496.0) fits 3472.8 only"),
    ("middle", 61, "sw"): ("3888.9", "the last digit is a filled blob, a 0 by its outline; but the cross-lines of courses 132 and "
                                     "133 (23.05 and 22.02 in) put the level at 3888.9, and 3888.0 fits neither"),
}


def settled() -> dict[str, dict[int, dict]]:
    """Per strip: line index -> {"ne", "sw", "how"}; how is "agreed", "referee" or "fixed"."""
    data = json.loads(READINGS.read_text(encoding="utf-8"))
    out: dict[str, dict[int, dict]] = {name: {} for name in STRIPS}
    for batch in data["batches"]:
        a = {(r["strip"], r["k"]): r for r in batch["a"]}
        b = {(r["strip"], r["k"]): r for r in batch["b"]}
        ref = {(r["strip"], r["k"]): r for r in (batch.get("referee") or [])}
        for key in sorted(set(a) | set(b)):
            if key in ref:
                row, how = ref[key], "referee"
            else:
                row, how = a.get(key) or b[key], "agreed"
                other = b.get(key)
                if other is None or key not in a or other["ne"] != row["ne"] or other["sw"] != row["sw"]:
                    how = "unsettled"
            out[key[0]][key[1]] = {"ne": row["ne"].strip(), "sw": row["sw"].strip(), "how": how,
                                   "doubt": bool(row.get("doubt")) and how == "referee"}
    for (strip, k, corner), (value, _reason) in FIXES.items():
        out[strip][k][corner] = value
        out[strip][k]["how"] = "fixed"
        out[strip][k]["doubt"] = False
    return out


def number(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


def cross_lines(pixels: np.ndarray, strip: dict, x0: float, x1: float) -> list[tuple[float, float]]:
    """Thicknesses (inches, as low-high ranges) of the cross-lines drawn in the bar between two upright lines."""
    a, b = int(round(x0)) + 3, int(round(x1)) - 2
    if b - a < 6:
        return []
    mid = (a + b) / 2
    top, bottom = int(level_y(strip, mid, 62.0)), int(level_y(strip, mid, 14.6))
    dark = pixels[max(0, top):bottom, a:b] < 128
    share = dark.mean(axis=1)
    rows = [max(0, top) + int(y) for y in np.flatnonzero(share > 0.3)]     # some cross-lines are fine or broken
    groups: list[list[int]] = []
    for y in rows:
        if groups and y - groups[-1][-1] <= 2:
            groups[-1].append(y)
        else:
            groups.append([y])
    zero = level_y(strip, mid, 0.0)
    scale = PX_PER_10IN / 10.0
    return [(round((zero - g[-1]) / scale, 2), round((zero - g[0]) / scale, 2)) for g in groups]


def build() -> dict:
    rows = settled()
    geometry = {name: {"pixels": scan(strip["leaf"])} for name, strip in STRIPS.items()}
    for name, strip in STRIPS.items():
        geometry[name]["lines"] = upright_lines(geometry[name]["pixels"], strip)

    # --- per strip: the rows that carry a level, in order
    per_strip: dict[str, list[dict]] = {}
    for name in STRIPS:
        found = []
        for k in sorted(rows[name]):
            row = rows[name][k]
            ne, sw = number(row["ne"]), number(row["sw"])
            if ne is None and sw is None:
                continue
            found.append({"strip": name, "k": k, "ne": ne, "sw": sw, "how": row["how"], "doubt": row["doubt"],
                          "x": geometry[name]["lines"][k]})
        per_strip[name] = found

    problems: list[str] = []

    # --- check 2: position along the plate against the level (one straight line per strip)
    for name, found in per_strip.items():
        usable = [r for r in found if r["ne"] is not None]
        x = np.array([r["x"] for r in usable])
        level = np.array([r["ne"] for r in usable])
        slope, origin = np.polyfit(level, x, 1)
        off = (x - (origin + slope * level)) / slope             # inches, including the slow stretch of the paper
        for i, r in enumerate(usable):
            near = np.r_[off[max(0, i - 5):i], off[i + 1:i + 6]]
            local = float(off[i] - np.median(near))
            r["position_error_in"] = round(local, 1)
            if abs(local) > POSITION_LIMIT_IN:
                problems.append(f"{name} line {r['k']}: level {r['ne']} sits {local:+.1f} in from its upright line")
        geometry[name]["px_per_inch"] = float(slope)

    # --- number the courses: the lower strip starts at course 1; the others are joined on their overlap
    def join(lower: list[dict], upper: list[dict], offset_lower: int) -> int:
        """Course number of the first row of `upper`, from the best match of its first levels in `lower`."""
        first = upper[0]["ne"]
        best = min(range(len(lower)), key=lambda i: abs(lower[i]["ne"] - first))
        if abs(lower[best]["ne"] - first) > 0.05:
            problems.append(f"strips do not join: {first} not found in the strip below (nearest {lower[best]['ne']})")
        return offset_lower + best

    start = {"lower": 1}
    start["middle"] = join(per_strip["lower"], per_strip["middle"], start["lower"])
    start["upper"] = join(per_strip["middle"], per_strip["upper"], start["middle"])
    courses: dict[int, dict] = {}
    for name in ("lower", "middle", "upper"):
        for i, r in enumerate(per_strip[name]):
            n = start[name] + i
            r["course"] = n
            if n in courses:                                   # check 1: read twice from two scans
                for corner in ("ne", "sw"):
                    if courses[n][corner] != r[corner]:
                        problems.append(f"course {n} {corner.upper()}: {courses[n][corner]} on the {courses[n]['strip']} strip, "
                                        f"{r[corner]} on the {name} strip")
                courses[n]["also"] = name
            else:
                courses[n] = r

    numbers = sorted(courses)
    if numbers != list(range(1, numbers[-1] + 1)):
        problems.append("course numbers are not continuous")

    # --- check 3: thickness against the drawn cross-lines; and plain sanity
    previous = {"ne": 0.0, "sw": 0.0}
    for n in numbers:
        r = courses[n]
        strip = STRIPS[r["strip"]]
        lines = geometry[r["strip"]]["lines"]
        drawn = cross_lines(geometry[r["strip"]]["pixels"], strip, lines[r["k"] - 1], lines[r["k"]]) if r["k"] > 0 else []
        on_a_line = lambda t: any(lo - THICKNESS_LIMIT_IN <= t <= hi + THICKNESS_LIMIT_IN for lo, hi in drawn)
        r["drawn_in"] = drawn
        for corner in ("ne", "sw"):
            if r[corner] is None:
                continue
            thick = round(r[corner] - previous[corner], 1)
            r[f"{corner}_thick"] = thick
            if not 18.0 <= thick <= 60.0:
                problems.append(f"course {n} {corner.upper()}: thickness {thick} in is outside 18 to 60")
            elif drawn and not on_a_line(thick):
                problems.append(f"course {n} {corner.upper()}: thickness {thick} in is not on a drawn cross-line {drawn}")
            previous[corner] = r[corner]
        if r["ne"] is not None and r["sw"] is not None and abs(r["ne"] - r["sw"]) > 10:
            problems.append(f"course {n}: N.E. {r['ne']} and S.W. {r['sw']} differ by more than 10 in")
        if r["how"] == "unsettled" or r["doubt"]:
            problems.append(f"course {n}: reading not settled ({r['how']})")

    table = [{"n": n, "ne_in": courses[n]["ne"], "sw_in": courses[n]["sw"]} for n in numbers]
    top_ne = max(c["ne_in"] for c in table if c["ne_in"] is not None)
    top_sw = max(c["sw_in"] for c in table if c["sw_in"] is not None)
    result = {
        "source": "W. M. Flinders Petrie, The Pyramids and Temples of Gizeh (London, 1883), Plate VIII: levels of the courses "
                  "of the Great Pyramid at the N.E. and S.W. corners, in inches above the pavement. Cornell University Library "
                  "copy, Internet Archive cu31924012038927, leaves 0306, 0290, 0291. Public domain.",
        "method": "Read twice independently from enlarged tiles, third reading on disagreement; checked against the plate's own "
                  "drawing (see topics/giza/build_courses.py).",
        "unit": "inches above the pavement",
        "courses": table,
        "summary": {"courses_ne": sum(1 for c in table if c["ne_in"] is not None),
                    "courses_sw": sum(1 for c in table if c["sw_in"] is not None),
                    "top_ne_in": top_ne, "top_ne_m": round(top_ne * INCH, 2),
                    "top_sw_in": top_sw, "top_sw_m": round(top_sw * INCH, 2)},
        "checks": {
            "read_from_two_scans": sum(1 for n in numbers if "also" in courses[n]),
            "settled_by_third_reading": sum(1 for n in numbers if courses[n]["how"] == "referee"),
            "settled_against_the_drawing": [f"{strip} line {k} {corner}: {value} ({reason})" for (strip, k, corner), (value, reason) in FIXES.items()],
            "largest_position_error_in": max(abs(courses[n].get("position_error_in", 0.0)) for n in numbers),
            "problems": problems,
        },
    }
    return result


if __name__ == "__main__":
    result = build()
    save_text(OUT, json.dumps(result, indent=1) + "\n")
    print(json.dumps(result["summary"], indent=1))
    print(json.dumps({k: v for k, v in result["checks"].items() if k != "problems"}, indent=1))
    print(f"{len(result['checks']['problems'])} problems")
    for line in result["checks"]["problems"]:
        print("  ", line)
