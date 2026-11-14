"""Film: What did the Great Pyramid originally look like?  (phase model)

The finding: what stands today is a staircase of 203 courses of stone, 138.5 m to its
highest block, ending in a flat top. As finished it was smooth, cased in white limestone,
and came to a point 146.7 m high. The white model is built from the level of every course
as surveyed by Flinders Petrie in 1880-82 (The Pyramids and Temples of Gizeh, 1883,
Plate VIII); the casing and apex are drawn as light, from his base and face angle.

The facts behind every claim are in films/great-pyramid-original/FACTS.md.
"""
from __future__ import annotations

from topics.giza.model import build_model

MODEL = build_model()

# "text" is the caption; "say" is what the voice reads; "chunks" show the caption a few words at a time
SCRIPT = [
    {"id": "s0", "beat": 1, "text": "What did the Great Pyramid originally look like?", "caption": False},
    {"id": "s1", "beat": 2, "text": "What stands today is a staircase: 203 courses of stone.",
     "say": "What stands today is a staircase: two hundred and three courses of stone.",
     "chunks": ["What stands today", "is a staircase:", ["203 courses of stone.", "two hundred and three courses of stone."]]},
    {"id": "s2", "beat": 2, "text": "It ends in a flat top, about 11 metres across.",
     "say": "It ends in a flat top, about eleven metres across.",
     "chunks": ["It ends in a flat top,", ["about 11 metres across.", "about eleven metres across."]]},
    {"id": "s3", "beat": 3, "gap_before": 0.75, "text": "But it was finished smooth: cased in white limestone, rising to a point.",
     "chunks": ["But it was finished smooth:", "cased in white limestone,", "rising to a point."]},
    {"id": "s4", "beat": 4, "text": "Almost all of that casing was quarried away in the Middle Ages, much of it to build Cairo.",
     "chunks": ["Almost all of that casing", "was quarried away", "in the Middle Ages,", "much of it to build Cairo."]},
    {"id": "s5", "beat": 5, "text": "Its own capstone has never been found.",
     "chunks": ["Its own capstone", "has never been found."]},
]

FILM = {
    "id": "great-pyramid-original",
    "look": "phase",
    "title": "What did the Great Pyramid originally look like?",
    "eyebrow": "GREAT PYRAMID · GIZA · c. 2600-2500 BC",
    "hook": ["What did the Great Pyramid", "originally look like?"],
    "script": SCRIPT,
    "voice": {"lead_in_s": 0.15, "gap_s": 0.27, "tail_s": 1.5},
    "model": MODEL,
    "phase": {
        "label": "still standing · 203 courses",
        # the label follows the readout: none while the number runs up from today's highest stone, the second label
        # when it lands on the height as finished, and the first again when the casing goes
        "label_after": {"text": "as finished · casing and apex", "above": MODEL["levels_m"][-1] + 0.04,
                        "from": MODEL["original_height_m"] - 0.04, "until": "s4.chunk:1+0.2"},
        "figure": {"values": MODEL["levels_m"], "clip_top": MODEL["original_height_m"],
                   "follow_clip_from": "s3", "follow_clip_until": "s4.chunk:1+0.2",
                   "unit": "m", "decimals": 1, "second": {"factor": 3.28084, "unit": "ft", "decimals": 0}},
        "legend_matter": ["WHITE", "there today · 203 course levels, Petrie 1880-82"],
        "legend_light": ["LIGHT", "inferred · from the base and the slope"],
        "credit": "Levels and height: Petrie, The Pyramids and Temples of Gizeh (1883), pl. VIII and p. 43 · Synthetic voice",
        # house lights: a first glimpse of the answer, full for the count, cut for the projector, and back when the casing goes
        "house": [["start", 1.0], ["start+0.45", 1.0], ["start+0.62", 0.2], ["start+1.3", 0.2], ["start+1.75", 1.0],
                  ["s3-0.6", 1.0], ["s3-0.33", 0.04], ["s4.chunk:1", 0.05], ["s4.chunk:1+1.3", 1.0], ["end", 1.0]],
        "strike": ["start+0.55", "s3-0.2"],
        "projector": [["start", 1.0], ["start+1.2", 1.0], ["start+1.5", 0.0], ["s3-0.45", 0.0], ["s3-0.4", 1.0], ["end", 1.0]],
        # the casing climbs the core, then closes the missing top
        "clip": [["start", 1.0], ["start+1.55", 1.0], ["start+1.6", 0.0], ["s3+0.1", 0.0], ["s3+3.0", 0.9364], ["s3+4.3", 1.0], ["end", 1.0]],
        # "quarried away": the casing goes dark; the missing top stays lit until the film closes on its first frame
        "light_levels": {
            "casing": [["start", 1.0], ["s4.chunk:1", 1.0], ["s4.chunk:1+0.9", 0.0], ["end", 0.0]],
            "apex": [["start", 1.0], ["end-0.5", 1.0], ["end-0.08", 0.0]],
        },
        "pick": {"group": "course", "from": "s1+0.15", "to": "s2-0.3"},
        "figure_in": "s1",
        "legend": {"matter_in": "s1+0.5", "light_in": "s3+0.4", "matter_pulse": "s1+0.5", "light_pulse": "s3+0.4"},
        "reveal": [{"groups": ["casing", "apex"], "at": "start", "spread": 0.0, "rise_after": 0.0, "from_bearing": 0}],
        # one slow turn about the pyramid: whole, up to the flat top, back for the casing, in for the point, and round to the start
        "camera": [
            {"t": "start", "bearing": 138, "elevation": 15, "distance": 192, "target_y": 7.9},
            {"t": "s1", "bearing": 146, "elevation": 15, "distance": 186, "target_y": 8.0},
            {"t": "s2+0.3", "bearing": 160, "elevation": 13, "distance": 64, "target_y": 15.4},
            {"t": "s2.end", "bearing": 166, "elevation": 12, "distance": 44, "target_y": 16.5},
            {"t": "s3+1.1", "bearing": 176, "elevation": 14, "distance": 188, "target_y": 8.4},
            {"t": "s3+3.0", "bearing": 186, "elevation": 13, "distance": 120, "target_y": 13.0},
            {"t": "s3+4.3", "bearing": 192, "elevation": 11, "distance": 50, "target_y": 17.0},
            {"t": "s4+1.6", "bearing": 204, "elevation": 14, "distance": 190, "target_y": 8.4},
            {"t": "s5", "bearing": 216, "elevation": 14, "distance": 150, "target_y": 11.5},
            {"t": "s5.end", "bearing": 224, "elevation": 12, "distance": 60, "target_y": 16.9},
            {"t": "end", "bearing": 228, "elevation": 15, "distance": 192, "target_y": 7.9},
        ],
        "credit_in": "s5.end+0.2",
        "render": {"scale_bar_bearing": 180, "north_mark_bearing": 0, "key_bearing": 112, "near": 4.0, "aperture_at": 200.0,
                   "view_offset_y": 60, "pick_gain": 0.55, "pick_decay": 7.0, "clip_band": 0.7, "clip_lead": 2.4, "aa_width": 2.2, "spot_dark": 0.06, "rim_dark": 0.03},
    },
    "stills": {"01_first": "start", "02_glimpse": "start+1.0", "03_count": "s1+2.2", "04_flat_top": "s2.end-0.1",
               "05_rising": "s3+2.0", "06_point": "s3+4.3", "07_quarried": "s4.chunk:1+0.75", "08_capstone": "s5.end-0.2"},
    "sound": [
        {"type": "click", "at": "start+0.45"},                # house lights relay: the first glimpse
        {"type": "tick", "at": "pick", "every": 8},           # the count runs up the courses
        {"type": "click", "at": "s3-0.33"},                   # house lights relay
        {"type": "click", "at": "s4.chunk:1"},              # ... and back
    ],
}
