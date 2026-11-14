"""Film: Napoleon did not shoot the nose off the Sphinx.  (archive light table)

The finding: plate XLVI of Norden's "Voyage d'Egypte et de Nubie" (Copenhagen,
1755) shows the Sphinx from the front with the nose damaged. Plate XLV, the same
head with the three pyramids, is engraved "F. L. Norden del.; 1737": Norden drew
it in 1737. Napoleon Bonaparte was born on 15 August 1769, 32 years later.

Scans: Getty Research Institute copy, Internet Archive gri_33125008624443
(plates), not in copyright. The plates are stored sideways; "rotate": 270 turns
them upright. Scan coordinates below are pixels of the upright full page
(3000 x 2048). The painting is Jean-Leon Gerome, "Bonaparte Before the Sphinx",
from Wikimedia Commons (public domain).

Sources, quotes and what must not be claimed: topics/sphinx/research.md.
"""
from __future__ import annotations

D = "data/sphinx/"
PLATE_CROP = [110, 50, 2900, 1680]          # the leaf, without the book's edge and the dark table

SCRIPT = [
    {"id": "s0", "beat": 1, "text": "Napoleon did not shoot the nose off the Sphinx."},
    {"id": "s1", "beat": 1, "text": "And one old drawing proves it."},
    {"id": "s2", "beat": 2, "text": "A Danish naval officer, Frederic Norden, drew the Sphinx in Egypt."},
    {"id": "s3", "beat": 3, "gap_before": 0.25, "text": "Look at the face. The nose is already damaged."},
    {"id": "s4", "beat": 4, "gap_before": 0.25, "text": "Same head, another plate. Read the corner: Norden drew it, 1737.",
     "say": "Same head, another plate. Read the corner: Norden drew it, seventeen thirty-seven."},
    {"id": "s5", "beat": 5, "gap_before": 0.5, "text": "Napoleon was born in 1769. Thirty-two years later.",
     "say": "Napoleon was born in seventeen sixty-nine. Thirty-two years later."},
    {"id": "s6", "beat": 6, "text": "So who did it?"},
    {"id": "s7", "beat": 6, "gap_before": 0.2, "text": "One medieval writer says a man attacked its face, around 1378.",
     "say": "One medieval writer says a man attacked its face, around thirteen seventy-eight."},
    {"id": "s8", "beat": 6, "gap_before": 0.2, "text": "Nobody can prove it."},
    {"id": "s9", "beat": 7, "text": "Who told you it was Napoleon?"},
]

# plate XLVI, front view: the broken nose
NOSE_BOX = [1457, 460, 1586, 622]
NOSE_AT = [1521, 541]
# plate XLV: the engraved line "F. L. Norden del.; 1737", lower left under the picture
SIGNED_BOX = [296, 1434, 530, 1466]
SIGNED_AT = [413, 1450]

FILM = {
    "id": "sphinx-nose",
    "look": "table",
    "title": "Napoleon did not shoot the nose off the Sphinx",
    "script": SCRIPT,
    "hook": {"lines": ["Napoleon didn't break", "the Sphinx's nose."], "x": 60, "y": 200},
    "objects": [
        {"id": "painting", "scan": D + "gerome_bonaparte_sphinx_3071.jpg", "rotate": 0,
         "centre": [330, 532], "width": 500, "tilt": -1.6, "z": 1},
        {"id": "front", "scan": D + "norden1755_pl46_sphinx_face.jp2", "rotate": 270, "crop": PLATE_CROP,
         "centre": [600, 760], "width": 700, "tilt": 1.0, "z": 2},
        {"id": "dated", "scan": D + "norden1755_pl45_sphinx_pyramides.jp2", "rotate": 270, "crop": PLATE_CROP,
         "centre": [520, 912], "width": 560, "tilt": -0.8, "z": 3},
    ],
    "loupe": {
        "radius": 215, "magnification": 5.0,
        "fade_in": {"at": "s2+1.5", "dur": 0.4}, "fade_out": {"at": "s5.end-0.3", "dur": 0.6},
        "enter": [300, 620],
        "stops": [
            {"object": "front", "at": NOSE_AT, "arrive": "s3+0.1", "travel": 1.6, "bulge": 0.18},
            {"object": "dated", "at": SIGNED_AT, "arrive": "s4+2.4", "travel": 1.8, "bulge": 0.1},
        ],
    },
    "marks": [
        {"id": "nose", "type": "ellipse", "object": "front", "box": NOSE_BOX, "draw": "s3+1.3", "dur": 0.7, "width": 2.6},
        {"id": "signed", "type": "underline", "object": "dated", "box": SIGNED_BOX, "draw": "s4+3.3", "dur": 0.8, "width": 2.6},
    ],
    "plate": {
        "label": "DRAWN 1737 · NAPOLEON BORN 1769",
        "reading": "32 years",
        "text": ["The nose was damaged before he was born."],
        "source": "Norden, Voyage d'Egypte et de Nubie, 1755, pl. XLV-XLVI",
        "ours": "The marks and the 5x loupe are ours.",
        "x": 60, "y": 1098, "width": 820,
        "in": {"at": "s5+0.1", "dur": 0.9}, "rise": 12,
        "leader": {"from": "signed", "at": "s5+0.5", "dur": 0.6},
    },
    "camera": {"scale": [1.0, 1.045], "focus": [540, 880],
               "moves": [{"at": "s2", "dur": 3.0, "focus": [560, 820]}]},
    "credit": {"text": "Getty Research Institute · Wikimedia · Synthetic voice",
               "at": "s9.end+0.3", "dur": 0.6, "x": 60, "bottom": 1524},
    "stills": {"01_table": "s1+0.8", "02_loupe_arrives": "s3+0.3", "03_nose": "s3.end", "04_signed": "s4.end",
               "05_plate": "s5+2.4", "06_who": "s7+2.5", "07_question": "s9+0.8", "08_hold": "end-0.3"},
    "sound": [
        {"type": "tick", "at": "s3+2.0"},              # the ring round the nose closes
        {"type": "tick", "at": "s4+4.1"},              # the underline closes
    ],
}
