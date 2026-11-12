"""One command per film.

A topic is one data module in topics/ (plus its sources). Everything else is
here:

    python -m engine.film <topic> voice      narration audio and the clock
    python -m engine.film <topic> sound      voice + room tone + cues, with a levels report
    python -m engine.film <topic> stills     the frames listed in FILM["stills"]
    python -m engine.film <topic> accents    one still in every accent option
    python -m engine.film <topic> check      layout and safe-area problems
    python -m engine.film <topic> render     the finished MP4 in films/<id>/, stills and contact sheet
    python -m engine.film <topic> estimate   time 30 frames and estimate the full render

Options: --accent NAME|#HEX   --samples N (phase look)   --workers N (table look)
"""
from __future__ import annotations

import argparse
import importlib
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Iterator

import numpy as np
from PIL import Image

from engine import encode, sound, voice
from engine.timeline import resolve
from engine.files import fresh, write_text as save_text

ROOT = Path(__file__).resolve().parents[1]
TOKENS = json.loads((ROOT / "engine" / "tokens.json").read_text(encoding="utf-8"))


def load_topic(name: str) -> dict:
    return importlib.import_module(f"topics.{name}").FILM


def build_dir(film: dict) -> Path:
    return ROOT / "build" / film["id"]


def film_dir(film: dict) -> Path:
    return ROOT / "films" / film["id"]


def narrate(film: dict) -> dict:
    """Synthesise the script (cached per sentence) and return the narration clock."""
    v = TOKENS["voice"]
    return voice.synthesise(film["script"], build_dir(film) / "voice", voice=v["voice"], lang=v["lang"],
                            speed=v["speed"], fps=TOKENS["frame"]["fps"], lead_in=v["lead_in_s"], gap=v["gap_s"], tail=v["tail_s"])


def cues(film: dict, narration: dict) -> list[dict]:
    """The film's sound cues with times in seconds."""
    out = []
    for cue in film.get("sound", []):
        if cue["at"] == "pick":                      # one cue per counted stone (phase look)
            from engine import phase
            from engine.phase.render import pick_schedule
            desc = phase.describe(film, narration)
            pick = desc["timeline"]["pick"]
            for t in pick_schedule(pick["t0"], pick["t1"], len(desc["model"]["pick_order"])):
                out.append({"type": cue["type"], "t": round(t, 3), "gain_db": cue.get("gain_db", -4.0)})
            continue
        item = {"type": cue["type"], "t": round(resolve(cue["at"], narration), 3)}
        if "until" in cue:
            item["dur"] = round(resolve(cue["until"], narration) - item["t"], 3)
        if "gain_db" in cue:
            item["gain_db"] = cue["gain_db"]
        out.append(item)
    return sorted(out, key=lambda c: c["t"])


def mix(film: dict, narration: dict) -> dict:
    s = TOKENS["sound"]
    audio = build_dir(film) / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    return sound.mix(narration, build_dir(film) / "voice" / "voice.wav", cues(film, narration), audio / "mix.wav",
                     voice_lufs=s["voice_lufs"], room_rms_dbfs=s["room_rms_dbfs"], cue_margin_db=s["cue_margin_db"])


def check(film: dict, narration: dict) -> list[str]:
    if film["look"] == "phase":
        from engine import phase
        scene = phase.Scene(film, narration, samples=1)
        problems = scene.validate()
        scene.close()
        return problems
    from engine import table
    return table.validate(table.load(film, narration))


def stills(film: dict, narration: dict, out_dir: Path, *, accent: str | None = None, names: list[str] | None = None,
           suffix: str = "") -> list[Path]:
    wanted = {k: v for k, v in film["stills"].items() if not names or k in names}
    out_dir.mkdir(parents=True, exist_ok=True)
    if film["look"] == "phase":
        from engine import phase
        phase.stills(film, narration, wanted, out_dir, accent=accent, suffix=suffix)
    else:
        from engine import table
        scene = table.load(film, narration, accent=accent)
        fps = narration["fps"]
        for name, when in wanted.items():
            n = max(0, min(narration["frames"] - 1, int(round(resolve(when, narration) * fps))))
            table.frame(scene, n).save(fresh(out_dir / f"{name}{suffix}.png"))
    return [out_dir / f"{name}{suffix}.png" for name in wanted]


def frames(film: dict, narration: dict, *, accent: str | None = None, samples: int | None = None,
           workers: int = 4, start: int = 0, stop: int | None = None) -> Iterator[np.ndarray]:
    if film["look"] == "phase":
        from engine import phase
        yield from phase.frames(film, narration, accent=accent, samples=samples, start=start, stop=stop)
    else:
        from engine import table
        yield from table.frames(film, narration, accent=accent, workers=workers, start=start, stop=stop)


def contact_sheet(paths: list[Path], out: Path, *, columns: int = 4, width: int = 360) -> None:
    tiles = [Image.open(p).convert("RGB") for p in paths]
    height = round(width * tiles[0].height / tiles[0].width)
    rows = -(-len(tiles) // columns)
    sheet = Image.new("RGB", (columns * width, rows * height), (10, 12, 15))
    for i, tile in enumerate(tiles):
        sheet.paste(tile.resize((width, height), Image.LANCZOS), ((i % columns) * width, (i // columns) * height))
    sheet.save(fresh(out), quality=90)


def render(film: dict, *, accent: str | None = None, samples: int | None = None, workers: int = 4) -> dict:
    """Voice, sound, picture, MP4, stills and contact sheet for one film."""
    narration = narrate(film)
    problems = check(film, narration)
    if problems:
        raise SystemExit("layout problems, not rendering:\n  " + "\n  ".join(problems))
    levels = mix(film, narration)
    if not levels.get("ok", False):
        raise SystemExit("sound levels are outside the limits: see " + str(build_dir(film) / "audio" / "mix.levels.json"))
    out = film_dir(film)
    out.mkdir(parents=True, exist_ok=True)
    started, total = time.time(), narration["frames"]

    def progress() -> Iterator[np.ndarray]:
        for n, frame in enumerate(frames(film, narration, accent=accent, samples=samples, workers=workers)):
            if n % 150 == 0:
                print(f"  frame {n}/{total}  {time.time() - started:.0f} s", flush=True)
            yield frame

    target = out / f"{film['id']}.mp4"
    info = encode.encode(progress(), build_dir(film) / "audio" / "mix.wav", target,
                         fps=TOKENS["frame"]["fps"], size=(TOKENS["frame"]["width"], TOKENS["frame"]["height"]))
    still_paths = stills(film, narration, out / "stills", accent=accent)
    contact_sheet(still_paths, out / "contact_sheet.jpg")
    shutil.copyfile(build_dir(film) / "voice" / "narration.json", fresh(out / "narration.json"))
    shutil.copyfile(build_dir(film) / "audio" / "mix.levels.json", fresh(out / "sound_levels.json"))
    save_text(out / "render.json", json.dumps({"video": info, "seconds": round(time.time() - started, 1)}, indent=1))
    return info


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("topic")
    parser.add_argument("step", choices=["voice", "sound", "stills", "accents", "check", "render", "estimate"])
    parser.add_argument("--accent")
    parser.add_argument("--samples", type=int)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    film = load_topic(args.topic)
    narration = narrate(film)

    if args.step == "voice":
        print(f"{narration['duration_s']} s, {narration['frames']} frames, {narration['word_count']} spoken words")
        for s in narration["sentences"]:
            print(f"  {s['id']:<4} {s['start_s']:6.2f} - {s['end_s']:6.2f}  {s['text']}")
        print("voice:", build_dir(film) / "voice" / "voice.wav")
    elif args.step == "sound":
        levels = mix(film, narration)
        print(json.dumps({k: v for k, v in levels.items() if k != "cues"}, indent=1))
        for cue in levels.get("cues", []):
            print("  cue", cue)
        print("mix:", build_dir(film) / "audio" / "mix.wav")
    elif args.step == "check":
        problems = check(film, narration)
        print("\n".join(problems) if problems else "no layout problems")
    elif args.step == "stills":
        paths = stills(film, narration, build_dir(film) / "look", accent=args.accent, names=args.only)
        contact_sheet(paths, build_dir(film) / "look" / "contact_sheet.jpg")
        print("\n".join(str(p) for p in paths))
    elif args.step == "accents":
        names = args.only or list(film["stills"])[-1:]
        for name in TOKENS["accent"]["options"]:
            stills(film, narration, build_dir(film) / "accents", accent=name, names=names, suffix=f"_{name}")
        print(build_dir(film) / "accents")
    elif args.step == "estimate":
        started = time.time()
        count = sum(1 for _ in frames(film, narration, accent=args.accent, samples=args.samples, workers=args.workers, start=300, stop=330))
        per = (time.time() - started) / count
        print(f"{per:.2f} s per frame including start-up; about {per * narration['frames'] / 60:.1f} minutes for {narration['frames']} frames")
    elif args.step == "render":
        info = render(film, accent=args.accent, samples=args.samples, workers=args.workers)
        print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
