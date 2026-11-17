"""Film: Why is the Colosseum full of holes?  (archive light table)

The finding: the travertine blocks of the outer wall were tied to one another
with iron clamps set in lead; after antiquity the metal was dug out, and most
of the holes in the piers are what that left. Middleton printed it in 1892
(The Remains of Ancient Rome, vol. 2, p. 87 and note 3); in 1651 Suaresius
still listed barbarians, an earthquake and market-stall poles among the causes.

Pictures (all in data/colosseum/, listed in topics/colosseum/sources.json):
  Piranesi, Veduta dell'Anfiteatro Flavio detto il Colosseo, 1776, Met 59.570.426, CC0.
  Jane Martha St. John, The Colosseum, 1856, Met 2005.100.382 (68), CC0.
  Suaresius, Diatriba de foraminibus lapidum in priscis aedificiis, p. 4, Internet Archive.
  Middleton, The Remains of Ancient Rome, vol. 2 (1892), p. 87, Internet Archive.
Scan coordinates are pixels of the full image; none needs rotating.

Sources, quotes and what must not be claimed: topics/colosseum/research.md,
pictures.md and factcheck.md.
"""
from __future__ import annotations

D = "data/colosseum/"
PIRANESI = D + "met_piranesi_1776_veduta_colosseo_360270.jpg"
STJOHN = D + "met_stjohn_1856_colosseum_287727.jpg"
SUARESIUS = D + "suaresius1651_p4_colosseum_holes.jpg"
MIDDLETON = D + "middleton1892_vol2_p87_colosseum_clamps.jpg"

# Each line carries its pitch plan (engine/pitch.py): "focus" words get a pitch accent, and a phrase ends by its
# punctuation unless "ends" says otherwise (a yes/no question rises, a statement or a what-question falls).
SCRIPT = [
    # Conversational: each line leads into the next (the owner asked for "a more natural flowing dialogue").
    # The opening ends on "man-made" because that word carries a clean rise; "... people made most of the
    # Colosseum's holes?" was tried first and its rise broke up on "holes" (a 50 ms step, not a glide).
    {"id": "s0", "beat": 1, "text": "Did you know most of the Colosseum's holes are man-made?"},
    {"id": "s1", "beat": 2, "gap_before": 0.5, "text": "Look at this old photo. Can you see the piers?",
     "pitch": {"ends": ["keep", "rise"]}},
    {"id": "s2", "beat": 2, "gap_before": 0.2, "text": "Those dark dots are holes, and they've puzzled people for centuries.",
     "pitch": {"focus": ["holes"]}},
    {"id": "s3", "beat": 3, "gap_before": 0.6, "text": "In 1651, this page asked: was it barbarians, or market stalls?",
     "say": "In sixteen fifty-one, this page asked: was it barbarians, or market stalls?",
     # a choice between two ends like a statement: up on the first, down on the second
     "pitch": {"focus": ["barbarians", "market"], "ends": ["keep", "keep", "continue", "fall"]}},
    {"id": "s4", "beat": 4, "gap_before": 0.4, "text": "So what's the accepted answer?"},
    {"id": "s5", "beat": 4, "gap_before": 0.6, "text": "It's right here: iron clamps tied each block to the next.",
     "pitch": {"focus": ["iron"]}},
    {"id": "s6", "beat": 5, "gap_before": 0.5, "text": "After Rome fell, iron was valuable,",
     "pitch": {"ends": ["keep", "continue"]}},
    {"id": "s7", "beat": 5, "gap_before": 0.25, "text": "so people dug the clamps out, one by one.",
     "pitch": {"focus": ["dug"]}},
    {"id": "s8", "beat": 6, "gap_before": 0.5, "text": "By one estimate, about 300 tons of metal went into the building.",
     "say": "By one estimate, about three hundred tons of metal went into the building.",
     "pitch": {"focus": ["hundred"]}},
    {"id": "s9", "beat": 6, "gap_before": 0.7, "text": "Most of the clamps are gone now. The holes never left.",
     "pitch": {"focus": ["clamps", "holes"]}},
]

WALL_AT = [1500, 2080]                      # Piranesi: the outer arcades at the front
PIER_AT = [2050, 1790]                      # St. John: a second-storey pier face, pitted
PIER_BOX = [1975, 1650, 2125, 1930]
PIER2_BOX = [2265, 1680, 2395, 1930]        # the next pier along, in the closing close view
BARBARORUM_AT = [1100, 1570]                # Suaresius p. 4: "ad feritatem Barbarorum"
BARBARORUM_BOX = [900, 1540, 1225, 1602]
CLAMPS_AT = [1240, 1455]                    # Middleton p. 87: "heavy iron clamps, run with lead."
CLAMPS_BOX = [955, 1415, 1940, 1492]
NOTE_BOX = [960, 2985, 1885, 3046]          # note 3: "to extract the then valuable iron of the"

FILM = {
    "id": "colosseum-holes",
    "look": "table",
    "title": "Why is the Colosseum full of holes?",
    "script": SCRIPT,
    "voice": {"voice": "af_heart", "lang": "en-us", "speed": 1.15},
    "prosody": {},                              # pitch planned and measured line by line, with the settings of tokens.json
    "hook": {"lines": ["Why is the Colosseum", "full of holes?"], "x": 60, "y": 200},
    "objects": [
        {"id": "view", "scan": PIRANESI, "rotate": 0, "crop": [20, 20, 3740, 2330],
         "centre": [530, 720], "width": 860, "tilt": -1.6, "z": 1,
         "enter": {"at": 0.0, "dur": 0.6, "from": [-140, 420], "tilt_from": -7, "scale_from": 1.12}},
        {"id": "photo", "scan": STJOHN, "rotate": 0, "crop": [40, 30, 3790, 2960],
         "centre": [545, 752], "width": 820, "tilt": 1.2, "z": 2,
         "enter": {"at": "s1-0.3", "dur": 0.6, "from": [160, 440], "tilt_from": 6, "scale_from": 1.12}},
        {"id": "book", "scan": SUARESIUS, "rotate": 0, "crop": [740, 1130, 2330, 2060],
         "centre": [530, 740], "width": 840, "tilt": -1.4, "z": 3,
         "enter": {"at": "s3-0.2", "dur": 0.6, "from": [-130, 460], "tilt_from": -6, "scale_from": 1.12}},
        {"id": "page", "scan": MIDDLETON, "rotate": 0, "crop": [150, 650, 2040, 1690],
         "centre": [540, 652], "width": 860, "tilt": 1.0, "z": 4,
         "enter": {"at": "s4-0.15", "dur": 0.6, "from": [150, 460], "tilt_from": 6, "scale_from": 1.12}},
        {"id": "note", "scan": MIDDLETON, "rotate": 0, "crop": [150, 2895, 2040, 3270],
         "centre": [535, 972], "width": 860, "tilt": -0.8, "z": 5,
         "enter": {"at": "s6-0.2", "dur": 0.6, "from": [-130, 300], "tilt_from": -5, "scale_from": 1.12}},
        {"id": "close", "scan": STJOHN, "rotate": 0, "crop": [1350, 1250, 2850, 2400],
         "centre": [545, 745], "width": 840, "tilt": 1.0, "z": 6,
         "enter": {"at": "s8-0.2", "dur": 0.6, "from": [150, 460], "tilt_from": 6, "scale_from": 1.12}},
    ],
    # picture events are tied to the word the voice is saying ("s2.word:dots"), so they land on it
    "loupe": {
        "radius": 215, "magnification": 2.0,           # the owner found 3x too much (17 November 2026)
        "fade_in": {"at": 0.35, "dur": 0.4}, "fade_out": {"at": "s6-0.1", "dur": 0.4},
        "enter": [800, 560],
        "stops": [
            {"object": "view", "at": WALL_AT, "arrive": 1.6, "travel": 1.2, "bulge": 0.18},
            {"object": "photo", "at": PIER_AT, "arrive": "s1.word:piers+0.15", "travel": 1.0, "bulge": 0.12},
            {"object": "book", "at": BARBARORUM_AT, "arrive": "s3.word:barbarians", "travel": 1.2, "bulge": 0.1},
            {"object": "page", "at": CLAMPS_AT, "arrive": "s5-0.1", "travel": 1.4, "bulge": 0.0},
        ],
    },
    "marks": [
        {"id": "pier", "type": "ellipse", "object": "photo", "box": PIER_BOX, "draw": "s2.word:dots", "dur": 0.6,
         "fade": {"at": "s3-0.2", "dur": 0.2}, "width": 2.6},
        {"id": "barbarians", "type": "underline", "object": "book", "box": BARBARORUM_BOX, "draw": "s3.word:barbarians+0.15",
         "dur": 0.6, "fade": {"at": "s4-0.15", "dur": 0.2}, "width": 2.6},
        {"id": "clamps", "type": "underline", "object": "page", "box": CLAMPS_BOX, "draw": "s5.word:clamps", "dur": 0.8,
         "fade": {"at": "s8-0.2", "dur": 0.2}, "width": 2.6},
        {"id": "dugout", "type": "underline", "object": "note", "box": NOTE_BOX, "draw": "s7.word:dug", "dur": 0.8,
         "fade": {"at": "s8-0.2", "dur": 0.2}, "width": 2.6},
        {"id": "pier2", "type": "ellipse", "object": "close", "box": PIER2_BOX, "draw": "s8.word:three", "dur": 0.7,
         "width": 2.6},
    ],
    "plate": {
        "label": "COLOSSEUM · METAL USED TO BUILD IT",
        "reading": "about 300 tons",
        "text": ["A modern estimate, not a measured figure."],
        "source": "Middleton 1892 · Suaresius 1651 · The Met",
        "ours": "The marks and the 2x loupe are ours.",
        "x": 60, "y": 1098, "width": 820,
        "in": {"at": "s8.word:three+0.2", "dur": 0.9}, "rise": 12,
        "leader": {"from": "pier2", "at": "s8.word:three+0.9", "dur": 0.6},
    },
    "camera": {"scale": [1.0, 1.05], "focus": [540, 860],
               "moves": [{"at": "s1", "dur": 3.0, "focus": [560, 800]}]},
    "credit": {"text": "The Met · Internet Archive · Synthetic voice",
               "at": "s9.end+0.3", "dur": 0.6, "x": 60, "bottom": 1524},
    "stills": {"01_landing": 0.75, "02_view": 1.9, "03_photo": "s1.end", "04_pier": "s2.end-0.05",
               "05_book": "s3.end-0.3", "06_page": "s5.end-0.1", "07_note": "s7.end-0.1",
               "08_plate": "s8.end+0.2", "09_hold": "end-0.3"},
    # placeholder for the mock until the owner picks a track; "Suonatore di Liuto" by Kevin MacLeod, CC BY 4.0
    "music": {"file": "data/music/suonatore_di_liuto_kevin_macleod.mp3", "start": 0.2, "lufs": -30.0,
              "fade_in": 0.3, "fade_out": 1.5},
    "sound": [
        {"type": "tick", "at": "s2.word:dots+0.6"},        # the ring round the pier closes
        {"type": "tick", "at": "s5.word:clamps+0.8"},      # the line under the clamps is drawn
        {"type": "tick", "at": "s8.word:three+0.7"},       # the ring round the second pier closes
    ],
}
