"""Film: How much of Stonehenge is still standing?  (phase model)

One data module per film. Everything the engine needs is in FILM: the words,
the model, and when each picture and sound event happens on the narration
clock. The facts behind every claim are in films/stonehenge-standing/FACTS.md.
"""
from __future__ import annotations

from topics.stonehenge.model import build_model

# "text" is the caption; "say" is what the voice reads when figures are written out
SCRIPT = [
    {"id": "s1", "beat": 1, "text": "The great stones were raised about 4,500 years ago.",
     "say": "The great stones were raised about four and a half thousand years ago."},
    {"id": "s2", "beat": 2, "text": "The outer circle most likely had thirty uprights."},
    {"id": "s3", "beat": 2, "text": "But of those thirty, only seventeen still stand.",
     "cues": {"seventeen": "But of those thirty, only"}},
    {"id": "s4", "beat": 4, "gap_before": 2.0,
     "text": "Here we show where the others stood, and the missing lintels.",
     "cues": {"lintels": "Here we show where the others stood, and the missing"}},
    {"id": "s5", "beat": 4, "text": "Last century, engineers re-set or secured thirteen of the seventeen."},
    {"id": "s6", "beat": 5, "text": "Inside, three of the five trilithons still stand complete."},
    {"id": "s7", "beat": 6, "text": "Here is what survives today."},
    {"id": "s8", "beat": 6, "text": "And here is what we infer."},
]

FILM = {
    "id": "stonehenge-standing",
    "look": "phase",
    "title": "How much of Stonehenge is still standing?",
    "eyebrow": "STONEHENGE · WILTSHIRE",
    "hook": ["How much of Stonehenge", "is still standing?"],
    "script": SCRIPT,
    "model": build_model,
    "phase": {
        "label": "circle uprights still stand",
        "figure_total": 30,
        "legend_matter": ["WHITE", "survives today · airborne laser scan 2021"],
        "legend_light": ["LIGHT", "inferred · sarsens set up c. 2500 BC"],
        "credit": "Plan after Nash et al. 2021, CC BY 4.0 · Heights: Environment Agency LIDAR 2021, OGL v3.0 · Synthetic voice",
        # house lights: full for the count, cut for the projector, up for "white", down for "light"
        "house": [["start", 1.0], ["s3.end+0.45", 1.0], ["s3.end+0.72", 0.20], ["s5", 0.25],
                  ["s7-0.25", 0.27], ["s7+0.9", 0.80], ["s8-0.15", 0.80], ["s8+0.7", 0.25], ["end", 0.30]],
        "strike": "s3.end+1.1",
        "projector": [["start", 1.0], ["s7-0.25", 1.0], ["s7+0.9", 0.5], ["s8-0.15", 0.5], ["s8+0.55", 1.0], ["end", 1.0]],
        "pick": {"group": "circle_upright", "from": "s2+0.55", "to": "s3.cue:seventeen+0.28"},
        "figure_in": "s2+0.1",
        "of_in": "s4+0.9",
        "legend": {"matter_in": "s2+0.9", "light_in": "s4+0.9", "matter_pulse": "s7", "light_pulse": "s8"},
        "reveal": [
            {"groups": ["circle_upright"], "at": "s4+0.1", "spread": 1.3, "rise_after": 0.45, "from_bearing": 120},
            {"groups": ["circle_lintel"], "at": "s4.cue:lintels", "spread": 1.1, "rise_after": 0.0, "from_bearing": 120},
            {"groups": ["trilithon_upright"], "at": "s6+0.15", "spread": 0.5, "rise_after": 0.4, "from_bearing": 180},
            {"groups": ["trilithon_lintel"], "at": "s6+1.0", "spread": 0.4, "rise_after": 0.0, "from_bearing": 180},
        ],
        # the camera circles from the south-east to the south-west and never stops; lowest and closest for the trilithons
        "camera": [
            {"t": "start", "bearing": 150, "elevation": 38, "distance": 212, "target_y": 1.2},
            {"t": "s3.end", "bearing": 160, "elevation": 38, "distance": 206, "target_y": 1.2},
            {"t": "s5", "bearing": 174, "elevation": 36, "distance": 190, "target_y": 1.6},
            {"t": "s6", "bearing": 184, "elevation": 33, "distance": 172, "target_y": 2.0},
            {"t": "s7", "bearing": 192, "elevation": 36, "distance": 186, "target_y": 1.6},
            {"t": "end", "bearing": 204, "elevation": 38, "distance": 204, "target_y": 1.2},
        ],
        "credit_in": "s8.end+0.4",
        "render": {"scale_bar_bearing": 128, "north_mark_bearing": 0, "key_bearing": 118},
    },
    # frames to show for approval and to keep with the film
    "stills": {"01_house": "s1+1.5", "02_count": "s3.cue:seventeen+0.35", "03_strike": "s3.end+1.3", "04_light": "s4.end+0.3",
               "05_reset": "s5+1.5", "06_trilithons": "s6.end+0.2", "07_white": "s7+1.3", "08_hold": "end-0.6"},
    # sound cues, on the narration clock (all made by code; see engine/sound.py)
    "sound": [
        {"type": "tick", "at": "pick"},                       # one soft tick per counted stone
        {"type": "click", "at": "s3.end+0.45"},               # house lights relay
    ],
}
