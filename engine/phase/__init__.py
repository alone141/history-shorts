"""Phase model look: a white model of what exists today, on a plate in a dark
room, with a projector painting what is inferred as light.

    from engine import phase
    phase.stills(film, narration, {"hold": "end-0.6"}, out_dir)     # look checks
    for frame in phase.frames(film, narration): ...                 # numpy frames in order

`film` is a topic's FILM dict (see topics/stonehenge_standing.py) and
`narration` the dict written by engine.voice. Times in the film are
expressions on the narration clock (engine.timeline); they are resolved to
seconds here. The picture is drawn off-screen with OpenGL (render.py) and the
text with Pillow (overlay.py); a frame is a pure function of its number.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterator

import numpy as np
from PIL import Image

from engine.timeline import resolve
from engine.files import fresh, write_text as save_text

ROOT = Path(__file__).resolve().parents[2]
TOKENS = json.loads((ROOT / "engine" / "tokens.json").read_text(encoding="utf-8"))

# How the look is lit and graded. A topic may override any of these in film["phase"]["render"].
RENDER_DEFAULTS = {
    "fov": 22, "view_offset_y": 150, "samples": 10, "msaa": 0, "aperture": 0.5,
    "exposure": 1.18, "vignette": 0.45,
    "bloom_strength": 0.42, "bloom_radius": 0.5, "bloom_threshold": 1.15,
    "key": 2.9, "hemi": 0.42, "rim": 0.9, "fill": 0.22, "floor_spot": 2.2,
    "key_bearing": 118, "key_elevation_deg": 46,
    "light_body": 0.42, "light_edge": 2.6, "light_edge_px": 3.2, "light_foot": 1.5, "light_pool": 0.05, "light_pulse": 0.5,
    "scale_bar_bearing": 180, "north_mark_bearing": 0,
    "near": 20.0, "clip_band": 0.5, "clip_lead": 1.4, "pick_gain": 1.0, "pick_decay": 3.0, "aa_width": 1.0, "spot_dark": 0.5, "rim_dark": 0.12,
}


def accent_hex(accent: str | None) -> str:
    """A name from tokens.json, a hex string, or None for the current token."""
    options = TOKENS["accent"]["options"]
    if accent is None:
        return options[TOKENS["accent"]["current"]]
    return options.get(accent, accent)


def describe(film: dict, narration: dict, accent: str | None = None) -> dict:
    """Everything the renderer needs, with every time resolved to seconds."""
    spec = film["phase"]
    at = lambda expr: round(resolve(expr, narration), 4)
    model = film["model"]() if callable(film["model"]) else film["model"]
    model["pick_group"] = spec["pick"]["group"]
    strikes = spec["strike"] if isinstance(spec["strike"], list) else [spec["strike"]]
    figure = spec.get("figure")
    timeline = {
        "house": [[at(t), v] for t, v in spec["house"]],
        "projector": [[at(t), v] for t, v in spec["projector"]],
        "strikes": sorted(at(s) for s in strikes),
        # optional: light volumes drawn only up to a rising level (0..1 of the tallest), and a readout in real units
        "clip": [[at(t), v] for t, v in spec["clip"]] if spec.get("clip") else None,
        "figure": {"values": figure["values"], "clip_top": figure["clip_top"],
                   "follow_clip_from": at(figure["follow_clip_from"]),
                   "follow_clip_until": at(figure["follow_clip_until"]) if figure.get("follow_clip_until") else None} if figure else None,
        "label_after": {"t": at(spec["label_after"]["at"]),
                        "until": at(spec["label_after"]["until"]) if spec["label_after"].get("until") else None} if spec.get("label_after") else None,
        "light_levels": {name: [[at(t), v] for t, v in keys] for name, keys in spec.get("light_levels", {}).items()},
        "pick": {"t0": at(spec["pick"]["from"]), "t1": at(spec["pick"]["to"])},
        "figure_in": at(spec["figure_in"]), "of_in": at(spec["of_in"]) if "of_in" in spec else None,
        "legend": {key: at(value) for key, value in spec["legend"].items()},
        "reveal": [{"groups": r["groups"], "t": at(r["at"]), "spread": r["spread"],
                    "rise_after": r.get("rise_after", 0.45), "from_bearing": r.get("from_bearing", 0)}
                   for r in spec["reveal"]],
        "camera": [{"t": at(k["t"]), "bearing": k["bearing"], "elevation": k["elevation"],
                    "distance": k["distance"], "target_y": k.get("target_y", 1.5)} for k in spec["camera"]],
        "credit_in": at(spec["credit_in"]),
    }
    return {
        "id": film["id"],
        "tokens": TOKENS,
        "accent": accent_hex(accent),
        "text": {"eyebrow": film["eyebrow"], "hook": film["hook"], "label": spec["label"],
                 "figure_total": spec.get("figure_total"), "legend_matter": spec["legend_matter"],
                 "legend_light": spec["legend_light"], "credit": spec.get("credit", ""),
                 "figure": {k: v for k, v in figure.items() if k not in ("values", "clip_top", "follow_clip_from", "follow_clip_until")} if figure else None,
                 "label_after": spec["label_after"]["text"] if spec.get("label_after") else None},
        "narration": narration,
        "model": model,
        "timeline": timeline,
        "render": {**RENDER_DEFAULTS, **spec.get("render", {})},
    }


class Scene:
    """One film, ready to draw any frame."""

    def __init__(self, film: dict, narration: dict, *, accent: str | None = None, samples: int | None = None):
        from engine.phase.overlay import Overlay
        from engine.phase.render import Renderer

        self.narration = narration
        self.desc = describe(film, narration, accent)
        self.renderer = Renderer(self.desc, samples=samples)
        self.overlay = Overlay(self.desc, self.desc["accent"])
        self.info = dict(self.renderer.info)

    def frame(self, n: int) -> np.ndarray:
        """Frame n as (H, W, 3) uint8. Pure function of n."""
        picture, state = self.renderer.picture(n)
        return self.overlay.apply(picture, state["t"], state["count"], state["value"])

    def frame_at(self, when: str | float) -> int:
        n = int(round(resolve(when, self.narration) * self.narration["fps"]))
        return max(0, min(self.narration["frames"] - 1, n))

    def validate(self) -> list[str]:
        return list(self.overlay.problems)

    def close(self) -> None:
        self.renderer.close()


def stills(film: dict, narration: dict, whens: dict[str, str | float], out_dir: Path, *,
           accent: str | None = None, samples: int = 32, suffix: str = "") -> dict:
    """Write one PNG per named time. Returns renderer info and timings."""
    out_dir.mkdir(parents=True, exist_ok=True)
    scene = Scene(film, narration, accent=accent, samples=samples)
    info = scene.info
    info["problems"] = scene.validate()
    info["seconds"] = {}
    for name, when in whens.items():
        started = time.time()
        Image.fromarray(scene.frame(scene.frame_at(when))).save(fresh(out_dir / f"{name}{suffix}.png"))
        info["seconds"][name] = round(time.time() - started, 2)
    scene.close()
    return info


def frames(film: dict, narration: dict, *, accent: str | None = None, samples: int | None = None,
           start: int = 0, stop: int | None = None) -> Iterator[np.ndarray]:
    """Frames start..stop-1 in order, as numpy arrays, for engine.encode."""
    scene = Scene(film, narration, accent=accent, samples=samples)
    try:
        for n in range(start, narration["frames"] if stop is None else stop):
            yield scene.frame(n)
    finally:
        scene.close()
