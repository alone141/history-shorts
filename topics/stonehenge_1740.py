"""Film: What did Stonehenge look like in 1740?  (archive light table)

The finding: on page 19 of his 1740 book William Stukeley counts the outer
circle: 17 uprights standing, 6 lintels in place, 2 on the ground, 22 carried
off. A survey published in 2022 gives the same four numbers.

Scans: Stukeley, "Stonehenge, a temple restor'd to the British Druids" (London,
1740), Wellcome Collection copy, Internet Archive b30448554, Public Domain Mark.
Scan coordinates below are pixels of the upright full-resolution page.
"""
from __future__ import annotations

# read straight from the downloaded archive (topics/stonehenge/sources.json); no unpacking needed
SCANS = "data/stonehenge/stukeley/b30448554_jp2.zip!b30448554_jp2/b30448554_{:04d}.jp2"

SCRIPT = [
    {"id": "s1", "beat": 1, "text": "William Stukeley surveyed Stonehenge in the 1720s.",
     "say": "William Stukeley surveyed Stonehenge in the seventeen twenties."},
    {"id": "s2", "beat": 2, "text": "His book of 1740 counts the outer circle:",
     "say": "His book of seventeen forty counts the outer circle:"},
    {"id": "s3", "beat": 2, "gap_before": 0.25, "text": "seventeen uprights left standing,"},
    {"id": "s4", "beat": 3, "gap_before": 0.25, "text": "six lintels in place, two on the ground, twenty-two carried off."},
    {"id": "s5", "beat": 4, "gap_before": 0.6, "text": "A study published in 2022 gives the same four numbers.",
     "say": "A study published in twenty twenty-two gives the same four numbers."},
    {"id": "s6", "beat": 5, "text": "In the circle, three stones fell and were put back, and more were straightened."},
    {"id": "s7", "beat": 6, "text": "The scans are real. The mark and the lens are ours."},
]

# The words "17 left ſtanding." (the box excludes "viz.") and the end of the same paragraph,
# on printed page 19 (scan 0057)
WORDS_17 = [292, 2694, 680, 2762]
LINE_17 = [486, 2728]
LINE_22 = [1230, 3044]

FILM = {
    "id": "stonehenge-1740",
    "look": "table",
    "title": "What did Stonehenge look like in 1740?",
    "script": SCRIPT,
    "hook": {"lines": ["What did Stonehenge", "look like in 1740?"], "x": 60, "y": 200},
    "objects": [
        {"id": "prospect", "scan": SCANS.format(67), "rotate": 0, "centre": [815, 556], "width": 440, "tilt": 1.6, "z": 1},
        {"id": "front", "scan": SCANS.format(35), "rotate": 0, "centre": [815, 818], "width": 440, "tilt": -1.2, "z": 2},
        {"id": "page19", "scan": SCANS.format(57), "rotate": 0, "centre": [390, 750], "width": 380, "tilt": -0.6, "z": 3},
    ],
    "loupe": {
        "radius": 215, "magnification": 5.0,
        "fade_in": {"at": "s2", "dur": 0.4}, "fade_out": {"at": "s5-0.15", "dur": 0.6},
        "enter": [600, 1040],
        "stops": [
            {"object": "page19", "at": LINE_17, "arrive": "s3+0.05", "travel": 1.9, "bulge": 0.18},
            {"object": "page19", "at": LINE_22, "arrive": "s4+2.6", "travel": 2.4, "bulge": 0.0},
        ],
    },
    "marks": [
        {"id": "seventeen", "type": "underline", "object": "page19", "box": WORDS_17, "draw": "s3+0.25", "dur": 0.8, "width": 2.6},
    ],
    "plate": {
        "label": "OUTER CIRCLE · PRINTED 1740 AND 2022",
        "reading": "17 · 6 · 2 · 22",
        "text": ["uprights standing · lintels in place, fallen, gone"],
        "source": "Stukeley, p. 19 · Darvill, Antiquity 96: 320",
        "ours": "The mark and the 5x loupe are ours.",
        "x": 60, "y": 1098, "width": 800,
        "in": {"at": "s5+0.1", "dur": 0.9}, "rise": 12,
        "leader": {"from": "seventeen", "at": "s5+0.5", "dur": 0.6},
    },
    "camera": {"scale": [1.0, 1.05], "focus": [540, 880],
               "moves": [{"at": "s2", "dur": 3.0, "focus": [450, 850]}]},
    "credit": {"text": "Wellcome Collection, Public Domain Mark · Synthetic voice",
               "at": "s7.end+0.4", "dur": 0.6, "x": 60, "bottom": 1524},
    "stills": {"01_table": "s1+1.0", "02_loupe_arrives": "s2.end-0.3", "03_seventeen": "s3.end+0.2", "04_carried_off": "s4.end-0.1",
               "05_plate": "s5+2.0", "06_put_back": "s6+1.5", "07_ours": "s7+1.0", "08_hold": "end-0.6"},
    "sound": [
        {"type": "tick", "at": "s3+1.05"},             # the underline closes
        {"type": "lift", "at": "s5+0.1"},              # the caption plate
    ],
}


