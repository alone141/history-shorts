"""Narration synthesis: the voice is the clock for the whole film.

Each sentence is synthesised on its own with Kokoro, trimmed, faded and placed
on a timeline. Picture events are keyed to times in narration.json, so the
timeline is computed from sample counts and nothing else.

Cue times use the prefix-duration method: a cue named in a sentence's "cues"
maps to a prefix of that sentence's text. The prefix is synthesised and trimmed
the same way, and the cue time is sentence start + prefix duration - 0.08 s.

A sentence may also list "chunks": the caption shown a few words at a time.
Each chunk starts where the voice reaches it. The words before the chunk are
synthesised on their own and that clip is matched against the start of the
sentence's audio (dynamic time warping on the two spectra), which follows the
voice even where it says the same words faster or slower inside the sentence;
the result is then moved to the nearest pause when there is one within reach.

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
PAUSE_REACH_S = 0.12       # a caption chunk may move this far to land on a pause
PAUSE_DEPTH = 0.3          # ... if the level there is under this share of the clip's median level
ALIGN_HOP_S = 0.01         # spectra for matching a prefix against its sentence: one column every 10 ms
ALIGN_BANDS = 32
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


def _snap_to_pause(clip: np.ndarray, sample_rate: int, estimate: float, reach: float = PAUSE_REACH_S) -> float:
    """Move a time inside a clip to the quietest moment within `reach`, if that moment is a real dip."""
    hop = max(1, int(round(0.005 * sample_rate)))
    width = max(hop, int(round(0.02 * sample_rate)))
    if clip.size < 4 * width:
        return estimate
    power = np.convolve(clip.astype(np.float64) ** 2, np.ones(width) / width, mode="same")[::hop]
    level = np.sqrt(power)
    lo = max(0, int(round((estimate - reach) / 0.005)))
    hi = min(level.size, int(round((estimate + reach) / 0.005)) + 1)
    if hi - lo < 3:
        return estimate
    quietest = lo + int(np.argmin(level[lo:hi]))
    if level[quietest] > PAUSE_DEPTH * float(np.median(level[level > 0.0])):
        return estimate
    return quietest * 0.005


def _spectrum(clip: np.ndarray, sample_rate: int) -> np.ndarray:
    """Log energy in ALIGN_BANDS bands (rows are 10 ms steps), each band scaled to zero mean and unit spread."""
    from scipy.signal import stft

    hop = int(round(ALIGN_HOP_S * sample_rate))
    window = int(round(0.025 * sample_rate))
    freqs, _, z = stft(clip.astype(np.float64), fs=sample_rate, nperseg=window, noverlap=window - hop, padded=False, boundary=None)
    power = np.abs(z) ** 2
    edges = np.geomspace(90.0, min(7600.0, sample_rate / 2 - 1), ALIGN_BANDS + 1)
    bands = np.stack([power[(freqs >= lo) & (freqs < hi)].sum(axis=0) for lo, hi in zip(edges[:-1], edges[1:])])
    logs = np.log(bands + 1e-9).T
    return (logs - logs.mean(axis=0)) / (logs.std(axis=0) + 1e-6)


def _reach_of_prefix(sentence: np.ndarray, prefix: np.ndarray, sample_rate: int) -> float | None:
    """Seconds into `sentence` at which the words of `prefix` (the same words, spoken alone) have been said.

    Both clips start at the same word. The prefix is warped onto the opening of the sentence, the end of the
    match left free; the best end is where the sentence has just finished saying the prefix.
    """
    a, b = _spectrum(prefix, sample_rate), _spectrum(sentence, sample_rate)
    m, n = len(a), len(b)
    if m < 5 or n < 5:
        return None
    # distance between every pair of columns
    cost = np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).mean(axis=2))
    total = np.full((m, n), np.inf)
    total[0, 0] = cost[0, 0]
    for j in range(1, n):
        total[0, j] = total[0, j - 1] + cost[0, j]
    for i in range(1, m):
        row, above = total[i], total[i - 1]
        row[0] = above[0] + cost[i, 0]
        best = np.minimum(above[1:], above[:-1])           # from the column below-left or straight below
        for j in range(1, n):
            row[j] = cost[i, j] + min(best[j - 1], row[j - 1])
    # a prefix spoken alone ends more slowly than inside the sentence, so look from 55 % to 115 % of its own length
    lo, hi = max(1, int(0.55 * m)), min(n - 1, int(1.15 * m) + 1)
    if hi <= lo:
        return None
    ends = np.arange(lo, hi + 1)
    end = int(ends[np.argmin(total[m - 1, lo:hi + 1] / (m + ends))])
    return (end + 1) * ALIGN_HOP_S


def _chunk_parts(item: dict) -> tuple[list[str], list[str]]:
    """Caption text and spoken text of each chunk; a chunk is "words" or ["words", "as spoken"]."""
    texts, says = [], []
    for chunk in item["chunks"]:
        text, say = (chunk, chunk) if isinstance(chunk, str) else (chunk[0], chunk[1] or chunk[0])
        texts.append(text)
        says.append(say)
    return texts, says


def _validate(script: list[dict]) -> None:
    ids = [s["id"] for s in script]
    if not script:
        raise ValueError("script is empty")
    if len(set(ids)) != len(ids):
        raise ValueError("sentence ids must be unique")
    for s in script:
        if not str(s.get("text", "")).strip():
            raise ValueError(f"sentence {s.get('id')!r} has no text")
        if s.get("chunks"):
            texts, says = _chunk_parts(s)
            if " ".join(texts) != s["text"] or " ".join(says) != s.get("say", s["text"]):
                raise ValueError(f"sentence {s['id']!r}: its chunks do not add up to its text and spoken text")


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
        if item.get("chunks"):
            texts, says = _chunk_parts(item)
            offsets = [0.0]
            for count in range(1, len(says)):
                prefix_clip, _ = _clip(" ".join(says[:count]), voice, lang, speed, cache_dir, models)
                estimate = _reach_of_prefix(clip, prefix_clip, sample_rate)
                if estimate is None:
                    estimate = max(0.0, prefix_clip.size / sample_rate + CUE_OFFSET_S)
                offsets.append(max(offsets[-1] + 0.1, _snap_to_pause(clip, sample_rate, estimate)))
            edges = [round(start / sample_rate + o, 3) for o in offsets] + [entry["end_s"]]
            entry["chunks"] = [{"text": text, "start_s": a, "end_s": b} for text, a, b in zip(texts, edges[:-1], edges[1:])]
        if item.get("caption") is False:
            entry["caption"] = False
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
