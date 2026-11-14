"""The narration clock.

Every picture and sound event in a film is written as a time expression on the
narration, never as a bare number, so re-recording the voice moves everything
with it.

    "s3"            start of sentence s3
    "s3.end"        end of sentence s3
    "s3.cue:name"   the moment inside s3 that the script marked as cue "name"
    "s3.chunk:1"    the start of caption chunk 1 of s3 (chunks count from 0)
    "start", "end"  first and last frame of the film
    any of these followed by +0.4 or -0.25 (seconds)

`resolve` turns an expression into seconds; `at_frame` gives the frame number.
Easing helpers are pure functions, so a frame is a pure function of its number.
"""
from __future__ import annotations

import math
import re

_EXPR = re.compile(r"^\s*([A-Za-z_][\w]*)(?:\.(end|cue:[\w-]+|chunk:\d+))?\s*([+-]\s*\d+(?:\.\d+)?)?\s*$")


def resolve(expr: str | float | int, narration: dict) -> float:
    """Seconds on the film clock for a time expression (numbers pass through)."""
    if isinstance(expr, (int, float)):
        return float(expr)
    match = _EXPR.match(expr)
    if not match:
        raise ValueError(f"bad time expression: {expr!r}")
    name, part, offset = match.groups()
    shift = float(offset.replace(" ", "")) if offset else 0.0
    if name == "start" and part is None:
        return shift
    if name == "end" and part is None:
        return float(narration["duration_s"]) + shift
    sentence = next((s for s in narration["sentences"] if s["id"] == name), None)
    if sentence is None:
        raise KeyError(f"no sentence {name!r} in the narration (expression {expr!r})")
    if part is None:
        return float(sentence["start_s"]) + shift
    if part == "end":
        return float(sentence["end_s"]) + shift
    if part.startswith("chunk:"):
        chunks, index = sentence.get("chunks") or [], int(part.split(":", 1)[1])
        if index >= len(chunks):
            raise KeyError(f"sentence {name!r} has no chunk {index} (expression {expr!r})")
        return float(chunks[index]["start_s"]) + shift
    cue = part.split(":", 1)[1]
    if cue not in sentence.get("cues", {}):
        raise KeyError(f"sentence {name!r} has no cue {cue!r} (expression {expr!r})")
    return float(sentence["cues"][cue]) + shift


def at_frame(expr, narration: dict) -> int:
    return int(round(resolve(expr, narration) * narration.get("fps", 30)))


def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def ramp(t: float, t0: float, t1: float) -> float:
    """0 before t0, 1 after t1, linear between."""
    if t1 <= t0:
        return 1.0 if t >= t1 else 0.0
    return clamp01((t - t0) / (t1 - t0))


def ease_out(u: float) -> float:
    return 1 - (1 - clamp01(u)) ** 3


def ease_in_out(u: float) -> float:
    u = clamp01(u)
    return u * u * (3 - 2 * u)


def ease_cos(u: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * clamp01(u))
