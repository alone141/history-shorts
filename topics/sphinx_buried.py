"""Film: The Sphinx was buried to its neck for about 1,500 years.  (archive light table)

The finding: after its cult ended in the 4th century AD the Great Sphinx "was
soon buried up to the neck in the sand, in which state it remained until recent
times" (Selim Hassan, The Sphinx, 1949, p. 9). Norden drew it like that in 1737,
Teynard photographed it like that in 1851-52, and the body, about 73 m long,
was only cleared completely in the 1930s.

Pictures (all in data/sphinx/, listed in topics/sphinx/sources.json):
  Norden, Voyage d'Egypte et de Nubie (Copenhagen, 1755), plates XLVII and XLVI,
    Getty Research Institute copy, Internet Archive; stored sideways, "rotate": 270
    turns them upright (3000 x 2048).
  Felix Teynard, salted paper print, 1851-52, Metropolitan Museum of Art 1976.607.8, CC0.
  Matson Collection, Library of Congress, matpc.17957, between 1934 and 1939.
Scan coordinates are pixels of the upright full image.

Sources, quotes and what must not be claimed: topics/sphinx/research.md ("Angle 2").
"""
from __future__ import annotations

D = "data/sphinx/"
PLATE_CROP = [110, 50, 2900, 1680]          # the leaf, without the book's edge and the dark table

SCRIPT = [
    {"id": "s0", "beat": 1, "text": "For about 1,500 years, the Sphinx was buried up to its neck.",
     "say": "For about fifteen hundred years, the Sphinx was buried up to its neck."},
    {"id": "s1", "beat": 2, "text": "A traveller drew it like this in 1737.",
     "say": "A traveller drew it like this in seventeen thirty-seven."},
    {"id": "s2", "beat": 2, "gap_before": 0.2, "text": "Look at the rider. He is level with its chest."},
    {"id": "s3", "beat": 3, "gap_before": 0.3, "text": "A photograph from 1851. Still buried.",
     "say": "A photograph from eighteen fifty-one. Still buried."},
    {"id": "s4", "beat": 4, "gap_before": 0.3, "text": "Under the sand was a lion's body, 73 metres long.",
     "say": "Under the sand was a lion's body, seventy-three metres long."},
    {"id": "s5", "beat": 5, "text": "It was only dug out completely in the 1930s.",
     "say": "It was only dug out completely in the nineteen thirties."},
    {"id": "s6", "beat": 6, "text": "Did you know it had a body?"},
]

RIDER_BOX = [1270, 960, 1480, 1240]         # plate XLVI: the man on a donkey in front of the chest
RIDER_AT = [1375, 1090]
SAND_BOX = [2050, 2400, 2960, 2610]         # Teynard: where the sand meets the chest
HEAD_AT = [2400, 1750]                      # Teynard: head and neck
PAWS_BOX = [1750, 2450, 4150, 2950]         # Matson: the forepaws

FILM = {
    "id": "sphinx-buried",
    "look": "table",
    "title": "The Sphinx was buried up to its neck",
    "script": SCRIPT,
    "hook": {"lines": ["The Sphinx was buried", "to its neck for 1,500 years."], "x": 60, "y": 200},
    "objects": [
        {"id": "profile", "scan": D + "norden1755_pl47_profil_sphinx.jp2", "rotate": 270, "crop": PLATE_CROP,
         "centre": [470, 640], "width": 760, "tilt": -2.0, "z": 1,
         "enter": {"at": 0.0, "dur": 0.6, "from": [-140, 420], "tilt_from": -7, "scale_from": 1.12}},
        {"id": "front", "scan": D + "norden1755_pl46_sphinx_face.jp2", "rotate": 270, "crop": PLATE_CROP,
         "centre": [570, 800], "width": 880, "tilt": 1.0, "z": 2,
         "enter": {"at": 0.45, "dur": 0.6, "from": [160, 420], "tilt_from": 6, "scale_from": 1.12}},
        {"id": "photo", "scan": D + "teynard_1851_met_261882_sphinx_chest.jpg", "rotate": 0, "crop": [60, 50, 3724, 2930],
         "centre": [520, 740], "width": 800, "tilt": -1.4, "z": 3,
         "enter": {"at": "s3-0.15", "dur": 0.6, "from": [-120, 460], "tilt_from": -6, "scale_from": 1.12}},
        {"id": "dug", "scan": D + "matson_1934-39_loc_17957_sphinx_paws.jpg", "rotate": 0, "crop": [370, 345, 4300, 3240],
         "centre": [550, 750], "width": 880, "tilt": 1.2, "z": 4,
         "enter": {"at": "s4-0.2", "dur": 0.6, "from": [140, 460], "tilt_from": 6, "scale_from": 1.12}},
    ],
    "loupe": {
        "radius": 215, "magnification": 3.0,
        "fade_in": {"at": "s1+0.2", "dur": 0.4}, "fade_out": {"at": "s4-0.6", "dur": 0.4},
        "enter": [330, 700],
        "stops": [
            {"object": "front", "at": RIDER_AT, "arrive": "s2+0.1", "travel": 1.6, "bulge": 0.18},
            {"object": "photo", "at": HEAD_AT, "arrive": "s3+1.5", "travel": 1.2, "bulge": 0.1},
        ],
    },
    "marks": [
        {"id": "rider", "type": "ellipse", "object": "front", "box": RIDER_BOX, "draw": "s2+0.5", "dur": 0.7,
         "fade": {"at": "s3-0.15", "dur": 0.2}, "width": 2.6},
        {"id": "sand", "type": "underline", "object": "photo", "box": SAND_BOX, "draw": "s3+1.8", "dur": 0.7,
         "fade": {"at": "s4-0.3", "dur": 0.2}, "width": 2.6},
        {"id": "paws", "type": "box", "object": "dug", "box": PAWS_BOX, "draw": "s4+1.0", "dur": 0.9, "width": 2.6},
    ],
    "plate": {
        "label": "GREAT SPHINX · CLEARED IN THE 1930s",
        "reading": "73 m long",
        "text": ["Head and neck above the sand. The rest below."],
        "source": "Hassan 1949 · Norden 1755 · Teynard 1851 · Matson",
        "ours": "The marks and the 3x loupe are ours.",
        "x": 60, "y": 1098, "width": 820,
        "in": {"at": "s4+1.4", "dur": 0.9}, "rise": 12,
        "leader": {"from": "paws", "at": "s4+1.9", "dur": 0.6},
    },
    "camera": {"scale": [1.0, 1.05], "focus": [540, 860],
               "moves": [{"at": "s1", "dur": 3.0, "focus": [560, 800]}]},
    "credit": {"text": "Getty · The Met · Library of Congress · Synthetic voice",
               "at": "s6.end+0.3", "dur": 0.6, "x": 60, "bottom": 1524},
    "stills": {"01_landing": 0.75, "02_plates": "s1+0.6", "03_rider": "s2.end-0.3", "04_photo": "s3.end-0.1",
               "05_body": "s4+0.9", "06_plate": "s5+1.5", "07_question": "s6+0.8", "08_hold": "end-0.3"},
    "sound": [
        {"type": "tick", "at": "s2+1.2"},              # the ring round the rider closes
        {"type": "tick", "at": "s4+1.9"},              # the box round the paws closes
    ],
}
