"""Narration synthesis: the voice is the clock for the whole film.

Each sentence is synthesised on its own with Kokoro, trimmed, faded and placed
on a timeline. Picture events are keyed to times in narration.json, so the
timeline is computed from sample counts and nothing else.

Cue times use the prefix-duration method: a cue named in a sentence's "cues"
maps to a prefix of that sentence's text. The prefix is synthesised and trimmed
the same way, and the cue time is sentence start + prefix duration - 0.08 s.

Clips are cached under <out_dir>/cache, so a re-run with unchanged text is
instant and bit-identical.

Run the self-test from the repository root:  python -m engine.selftest_av
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from engine.files import fresh, write_text as save_text

CUE_METHOD = "sentence start + duration of synthesised prefix text - 0.08 s"
CUE_OFFSET_S = -0.08
TRIM_PAD_S = 0.012
FADE_S = 0.02
# Bump when trimming or fading changes, so stale cache entries are not reused.
CACHE_VERSION = "1"

_MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "kokoro"

_kokoro: Any = None


def _load_kokoro(model_dir: Path) -> Any:
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro

        _kokoro = Kokoro(str(model_dir / "kokoro-v1.0.onnx"), str(model_dir / "voices-v1.0.bin"))
    return _kokoro


def _cache_key(text: str, voice: str, lang: str, speed: float) -> str:
    payload = json.dumps([CACHE_VERSION, text, voice, lang, speed], ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def trim_silence(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """Cut leading and trailing silence, keeping TRIM_PAD_S either side.

    The threshold is relative to the clip's own peak (with a small floor) so a
    quiet voice and a loud one are trimmed alike.
    """
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    threshold = max(0.002, 0.01 * peak)
    loud = np.flatnonzero(np.abs(audio) > threshold)
    if loud.size == 0:
        raise ValueError("synthesised audio is silent")
    pad = int(round(TRIM_PAD_S * sample_rate))
    start = max(0, int(loud[0]) - pad)
    end = min(audio.size, int(loud[-1]) + 1 + pad)
    return audio[start:end].astype(np.float32, copy=True)


def _clip(text: str, voice: str, lang: str, speed: float, cache_dir: Path,
          model_dir: Path) -> tuple[np.ndarray, int]:
    """Return the trimmed clip for `text`, synthesising only on a cache miss."""
    path = cache_dir / f"{_cache_key(text, voice, lang, speed)}.wav"
    if path.exists():
        data, rate = sf.read(path, dtype="float32")
        return data, int(rate)
    samples, rate = _load_kokoro(model_dir).create(text, voice=voice, speed=speed, lang=lang)
    clip = trim_silence(np.asarray(samples, dtype=np.float32), int(rate))
    cache_dir.mkdir(parents=True, exist_ok=True)
    sf.write(fresh(path), clip, int(rate), subtype="FLOAT")
    return clip, int(rate)


def _write_float_wav(path: Path, samples: np.ndarray, sample_rate: int) -> None:
    """Write a mono float32 WAV with a fixed header.

    libsndfile stamps a PEAK chunk with the current time into float WAVs, which
    would make identical audio produce different files.
    """
    data = samples.astype("<f4").tobytes()
    fmt = struct.pack("<HHIIHHH", 3, 1, sample_rate, sample_rate * 4, 4, 32, 0)
    fact = struct.pack("<I", samples.size)
    body = (b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"fact" + struct.pack("<I", len(fact)) + fact
            + b"data" + struct.pack("<I", len(data)) + data)
    fresh(path).write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)


def _faded(clip: np.ndarray, sample_rate: int) -> np.ndarray:
    out = clip.copy()
    n = min(int(round(FADE_S * sample_rate)), out.size // 2)
    if n > 0:
        ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
        out[:n] *= ramp
        out[-n:] *= ramp[::-1]
    return out


def _validate(script: list[dict]) -> None:
    ids = [s["id"] for s in script]
    if not script:
        raise ValueError("script is empty")
    if len(set(ids)) != len(ids):
        raise ValueError("sentence ids must be unique")
    for s in script:
        if not str(s.get("text", "")).strip():
            raise ValueError(f"sentence {s.get('id')!r} has no text")


def synthesise(script: list[dict], out_dir: str | Path, *, voice: str = "bm_fable",
               lang: str = "en-gb", speed: float = 0.92, fps: int = 30,
               lead_in: float = 0.4, gap: float = 0.38, tail: float = 2.5,
               model_dir: str | Path | None = None) -> dict:
    """Synthesise `script`, write voice.wav and narration.json, return the narration dict.

    `model_dir` overrides the default models/kokoro location (an addition to the
    specified signature; it is keyword-only and optional).
    """
    _validate(script)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cache_dir = out / "cache"
    models = Path(model_dir) if model_dir else _MODEL_DIR

    placed: list[tuple[dict, np.ndarray, int]] = []  # (entry, faded clip, start sample)
    sample_rate = 0
    cursor = 0  # samples; end of the previous sentence
    for index, item in enumerate(script):
        # "say" is what the voice reads when it differs from the caption text
        # (for example years and figures written out as words)
        clip, rate = _clip(item.get("say", item["text"]), voice, lang, speed, cache_dir, models)
        if sample_rate and rate != sample_rate:
            raise RuntimeError("model sample rate changed between clips")
        sample_rate = rate
        if index == 0:
            start = int(round(lead_in * sample_rate))
        else:
            start = cursor + int(round(float(item.get("gap_before", gap)) * sample_rate))
        cues: dict[str, float] = {}
        for name, prefix in (item.get("cues") or {}).items():
            prefix_clip, _ = _clip(prefix, voice, lang, speed, cache_dir, models)
            offset = max(0.0, prefix_clip.size / sample_rate + CUE_OFFSET_S)
            cues[name] = round(start / sample_rate + offset, 3)
        entry = {
            "id": item["id"],
            "beat": item.get("beat"),
            "text": item["text"],
            "say": item.get("say", item["text"]),
            "start_s": round(start / sample_rate, 3),
            "end_s": round((start + clip.size) / sample_rate, 3),
            "cues": cues,
        }
        placed.append((entry, _faded(clip, sample_rate), start))
        cursor = start + clip.size

    end_s = cursor / sample_rate + tail
    frames = int(math.ceil(end_s * fps - 1e-6))
    duration = frames / fps
    buffer = np.zeros(int(round(duration * sample_rate)), dtype=np.float32)
    for _, clip, start in placed:
        buffer[start:start + clip.size] += clip
    _write_float_wav(out / "voice.wav", buffer, sample_rate)

    narration = {
        "voice": voice,
        "lang": lang,
        "speed": speed,
        "sample_rate": sample_rate,
        "fps": fps,
        "duration_s": round(duration, 4),
        "frames": frames,
        "word_count": sum(len(s.get("say", s["text"]).split()) for s in script),
        "cue_method": CUE_METHOD,
        "sentences": [entry for entry, _, _ in placed],
    }
    save_text(out / "narration.json", json.dumps(narration, indent=1) + "\n")
    return narration
