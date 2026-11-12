"""Sound mix for a narrated film: voice stem, room tone and code-made cues.

Everything is measured and reported as numbers (the film's author cannot
listen): voice loudness, true peak, room tone level and each cue's margin
below the voice. All cue sounds are generated here and are deterministic from
the seed. Cues are kept under the voice by scaling down, never by clipping.

Writes a stereo 48 kHz 24-bit WAV and a .levels.json report beside it.

Run the self-test from the repository root:  python -m engine.selftest_av
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Callable

import numpy as np
import pyloudnorm
import soundfile as sf
from scipy import ndimage, signal
from engine.files import fresh, write_text as save_text

TRUE_PEAK_CEILING_DBTP = -1.5
VOICE_LUFS_TOLERANCE = 0.3
ROOM_RMS_TOLERANCE_DB = 0.5
ROOM_FADE_S = 0.3
SHORT_TERM_WINDOW_S = 3.0
SHORT_TERM_HOP_S = 0.1
LIMITER_WINDOW_S = 0.01
# Small allowance for float rounding when comparing against a limit.
EPS_DB = 0.01

# Level of each cue type relative to its limit (dB, never positive): the hum
# and the swell are meant to sit further back than a tick or a thump.
TYPE_OFFSET_DB = {"tick": 0.0, "click": 0.0, "swell": -3.0, "thump": 0.0, "hum": -6.0, "lift": -3.0}
DEFAULT_DUR_S = {"tick": 0.05, "click": 0.14, "swell": 1.6, "thump": 0.6, "hum": 3.0, "lift": 1.2}


def db_to_lin(db: float) -> float:
    return 10.0 ** (db / 20.0)


def lin_to_db(x: float) -> float:
    return 20.0 * math.log10(max(x, 1e-12))


# ---------------------------------------------------------------- measurement

def sample_peak_dbfs(x: np.ndarray) -> float:
    return lin_to_db(float(np.max(np.abs(x))))


def true_peak_dbtp(x: np.ndarray) -> float:
    """True peak estimated with 4x oversampling (BS.1770 Annex 2 style)."""
    return lin_to_db(float(np.max(np.abs(signal.resample_poly(x, 4, 1, axis=0)))))


def rms_dbfs(x: np.ndarray) -> float:
    return lin_to_db(math.sqrt(float(np.mean(np.square(x, dtype=np.float64)))))


def integrated_lufs(stereo: np.ndarray, sample_rate: int) -> float:
    return float(pyloudnorm.Meter(sample_rate).integrated_loudness(stereo))


def short_term_lufs_max(stereo: np.ndarray, sample_rate: int) -> float:
    """Maximum short-term (3 s window) loudness, K-weighted per BS.1770.

    The signal is padded to at least one window so a brief cue is judged over
    a full 3 s, as a meter would show it.
    """
    window = int(SHORT_TERM_WINDOW_S * sample_rate)
    data = stereo.astype(np.float64)
    if data.shape[0] < window:
        data = np.pad(data, ((0, window - data.shape[0]), (0, 0)))
    meter = pyloudnorm.Meter(sample_rate)
    # The meter's own K-weighting stages; there is no public API for them.
    for stage in meter._filters.values():
        for ch in range(data.shape[1]):
            data[:, ch] = stage.apply_filter(data[:, ch])
    power = np.sum(np.square(data), axis=1)
    total = np.concatenate([[0.0], np.cumsum(power)])
    starts = np.arange(0, data.shape[0] - window + 1, max(1, int(SHORT_TERM_HOP_S * sample_rate)))
    mean_square = (total[starts + window] - total[starts]) / window
    return -0.691 + 10.0 * math.log10(max(float(np.max(mean_square)), 1e-20))


# ------------------------------------------------------------------ generators

def _lowpass(x: np.ndarray, cutoff: float, sr: int, order: int = 2) -> np.ndarray:
    return signal.sosfilt(signal.butter(order, cutoff, "low", fs=sr, output="sos"), x)


def _highpass(x: np.ndarray, cutoff: float, sr: int, order: int = 2) -> np.ndarray:
    return signal.sosfilt(signal.butter(order, cutoff, "high", fs=sr, output="sos"), x)


def _peak_normalised(x: np.ndarray) -> np.ndarray:
    return x / float(np.max(np.abs(x)))


def _edge_fade(x: np.ndarray, sr: int, fade_in: float, fade_out: float) -> np.ndarray:
    out = x.copy()
    n_in = max(1, min(int(fade_in * sr), out.size // 2))
    n_out = max(1, min(int(fade_out * sr), out.size // 2))
    out[:n_in] *= np.linspace(0.0, 1.0, n_in)
    out[-n_out:] *= np.linspace(1.0, 0.0, n_out)
    return out


def _tick(dur: float, rng: np.random.Generator, sr: int) -> np.ndarray:
    t = np.arange(int(dur * sr)) / sr
    x = np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 140) + 0.4 * np.sin(2 * np.pi * 950 * t) * np.exp(-t * 90)
    return _edge_fade(_peak_normalised(x), sr, 0.002, 0.01)


def _click(dur: float, rng: np.random.Generator, sr: int) -> np.ndarray:
    """Relay click: two sharp ticks close together, with a little body."""
    n_hit = int(0.09 * sr)
    t = np.arange(n_hit) / sr
    hit = rng.standard_normal(n_hit) * np.exp(-t * 600) * 0.7 + np.sin(2 * np.pi * 1300 * t) * np.exp(-t * 220)
    x = np.zeros(max(int(dur * sr), int(0.05 * sr) + n_hit))
    x[:n_hit] += hit
    second = int(0.05 * sr)
    x[second:second + n_hit] += 0.55 * hit
    return _edge_fade(_peak_normalised(x), sr, 0.002, 0.02)


def _swell(dur: float, rng: np.random.Generator, sr: int) -> np.ndarray:
    """Soft glassy swell: shimmering partials and a noise band under a bell envelope."""
    n = int(dur * sr)
    t = np.arange(n) / sr
    u = t / dur
    phase = 2 * np.pi * np.cumsum(1500 + 800 * u) / sr
    x = np.sin(phase) + 0.5 * np.sin(2.76 * phase + 0.7) + 0.3 * np.sin(4.1 * phase + 1.9)
    x *= 1 + 0.25 * np.sin(2 * np.pi * 7 * t)
    band = _lowpass(_highpass(rng.standard_normal(n), 900, sr), 3500, sr)
    x += 0.5 * band / float(np.std(band))
    x *= np.sin(np.pi * u) ** 2
    return _edge_fade(_peak_normalised(x), sr, 0.02, 0.06)


def _thump(dur: float, rng: np.random.Generator, sr: int) -> np.ndarray:
    """Low thump with a falling pitch and a short soft zap on top."""
    n = int(dur * sr)
    t = np.arange(n) / sr
    freq = 48 + 40 * np.exp(-t * 18)
    body = np.sin(2 * np.pi * np.cumsum(freq) / sr) * np.exp(-t * 7)
    zap = _lowpass(rng.standard_normal(n), 3000, sr) * np.exp(-t * 30) * 0.25
    return _edge_fade(_peak_normalised(body + zap), sr, 0.004, min(0.08, dur / 2))


def _hum(dur: float, rng: np.random.Generator, sr: int) -> np.ndarray:
    """Steady machine hum with a little air, faded in and out."""
    n = int(dur * sr)
    t = np.arange(n) / sr
    tone = sum(gain * np.sin(2 * np.pi * f * t + f) for f, gain in ((92, 1.0), (184, 0.5), (276, 0.25), (61, 0.5)))
    air = _lowpass(rng.standard_normal(n), 1400, sr)
    x = tone / float(np.std(tone)) + 0.5 * air / float(np.std(air))
    ramp = min(0.5, dur / 3)
    return _edge_fade(_peak_normalised(x), sr, ramp, ramp)


def _lift(dur: float, rng: np.random.Generator, sr: int) -> np.ndarray:
    """Rising tone and air that swells and then lets go quickly."""
    n = int(dur * sr)
    t = np.arange(n) / sr
    u = t / dur
    phase = 2 * np.pi * np.cumsum(300 * (6.0 ** u)) / sr
    tone = np.sin(phase) + 0.4 * np.sin(2 * phase + 0.5)
    air = _highpass(rng.standard_normal(n), 1500, sr)
    x = tone + 0.6 * air / float(np.std(air)) * u
    x *= u ** 2
    return _edge_fade(_peak_normalised(x), sr, 0.01, min(0.06, dur / 4))


GENERATORS: dict[str, Callable[[float, np.random.Generator, int], np.ndarray]] = {
    "tick": _tick, "click": _click, "swell": _swell, "thump": _thump, "hum": _hum, "lift": _lift,
}


# --------------------------------------------------------------------- stems

def _limit(stereo: np.ndarray, sr: int) -> tuple[np.ndarray, float]:
    """Lookahead true-peak limiter; returns the limited signal and the deepest gain cut in dB.

    The required gain comes from the 4x oversampled peak, then a windowed minimum
    followed by a moving average of the same length gives a smooth gain curve that
    is already down when the peak arrives (offline, so the window is centred).
    """
    ceiling = db_to_lin(TRUE_PEAK_CEILING_DBTP - 0.25)
    count = stereo.shape[0]
    over = np.abs(signal.resample_poly(stereo, 4, 1, axis=0)).max(axis=1)
    envelope = over[:4 * count].reshape(count, 4).max(axis=1)
    need = np.minimum(1.0, ceiling / np.maximum(envelope, 1e-12))
    width = int(LIMITER_WINDOW_S * sr) | 1
    gain = ndimage.uniform_filter1d(ndimage.minimum_filter1d(need, width), width)
    return stereo * gain[:, None], -lin_to_db(float(gain.min()))


def _voice_stem(voice_wav: str | Path, length: int, sr: int, target_lufs: float,
                peak_guard: str) -> tuple[np.ndarray, dict]:
    """Resample, place, normalise to `target_lufs` and guard the true peak.

    peak_guard "limit" (default) keeps the loudness target by limiting the few
    peaks that would exceed the ceiling; "attenuate" turns the whole voice down
    instead and so misses the loudness target. Either way the report says so.
    """
    mono, rate = sf.read(voice_wav, dtype="float64")
    if mono.ndim > 1:
        mono = mono.mean(axis=1)
    divisor = math.gcd(sr, int(rate))
    mono = signal.resample_poly(mono, sr // divisor, int(rate) // divisor)
    mono = np.pad(mono, (0, max(0, length - mono.size)))[:length]
    base = np.stack([mono, mono], axis=1)

    # Measured as dual-mono stereo, because that is what the listener receives.
    measured = integrated_lufs(base, sr)
    gain_db = target_lufs - measured
    stereo = base * db_to_lin(gain_db)
    info = {"voice_gain_db": gain_db, "true_peak_guard_mode": "none", "true_peak_guard_db": 0.0}
    if true_peak_dbtp(stereo) <= TRUE_PEAK_CEILING_DBTP:
        return stereo, info

    if peak_guard == "limit":
        for _ in range(8):  # limiting costs a little loudness; make it up and limit again
            stereo, reduction = _limit(base * db_to_lin(gain_db), sr)
            error = target_lufs - integrated_lufs(stereo, sr)
            if abs(error) < 0.05:
                break
            gain_db += error
        info.update(voice_gain_db=gain_db, true_peak_guard_mode="limiter", true_peak_guard_db=reduction)
    true_peak = true_peak_dbtp(stereo)
    if true_peak > TRUE_PEAK_CEILING_DBTP:
        cut = true_peak - TRUE_PEAK_CEILING_DBTP
        stereo = stereo * db_to_lin(-cut)
        info.update(true_peak_guard_mode="attenuation", true_peak_guard_db=info["true_peak_guard_db"] + cut)
    return stereo, info


def _room_tone(length: int, sr: int, rms_target_dbfs: float, rng: np.random.Generator) -> np.ndarray:
    """Low steady noise plus a faint hum; independent noise and hum phase per channel."""
    t = np.arange(length) / sr
    channels = []
    for ch in range(2):
        noise = _highpass(_lowpass(rng.standard_normal(length), 400, sr), 30, sr)
        noise /= float(np.std(noise))
        hum = sum(gain * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi))
                  for f, gain in ((55, 1.0), (110, 0.5), (165, 0.18)))
        hum = hum / float(np.std(hum)) * 0.45
        wobble = 1 + 0.04 * np.sin(2 * np.pi * 0.23 * t + ch)
        channels.append((noise * 0.8 + hum) * wobble)
    room = np.stack(channels, axis=1)
    n = int(ROOM_FADE_S * sr)
    room[:n] *= np.linspace(0, 1, n)[:, None]
    room[-n:] *= np.linspace(1, 0, n)[:, None]
    return room * (db_to_lin(rms_target_dbfs) / math.sqrt(float(np.mean(np.square(room)))))


def _cue_stem(cue: dict, index: int, length: int, sr: int, seed: int, voice_peak_db: float,
              voice_lufs: float, margin_db: float) -> tuple[np.ndarray, dict]:
    """Generate one cue, place it, and scale it down to meet both margins."""
    kind = cue["type"]
    if kind not in GENERATORS:
        raise ValueError(f"unknown cue type {kind!r}; expected one of {sorted(GENERATORS)}")
    extra_db = float(cue.get("gain_db", 0.0))
    if extra_db > 0:
        raise ValueError("gain_db may only attenuate (zero or negative)")
    start = int(round(float(cue["t"]) * sr))
    if not 0 <= start < length:
        raise ValueError(f"cue {index} ({kind}) at {cue['t']} s is outside the film")
    dur = float(cue.get("dur", DEFAULT_DUR_S[kind]))
    rng = np.random.default_rng([seed, index])
    sound = GENERATORS[kind](dur, rng, sr)

    peak_target_db = voice_peak_db - margin_db + TYPE_OFFSET_DB[kind] + extra_db
    sound = sound * db_to_lin(peak_target_db)
    sound = sound[:length - start]
    stem = np.zeros((length, 2))
    stem[start:start + sound.size, :] = sound[:, None]

    short_term = short_term_lufs_max(stem[start:start + sound.size], sr)
    excess = short_term - (voice_lufs - margin_db)
    if excess > 0:
        stem *= db_to_lin(-excess)
        short_term -= excess
    peak_db = sample_peak_dbfs(stem)
    row = {
        "type": kind, "t": float(cue["t"]), "dur": round(dur, 3),
        "peak_dbfs": peak_db, "margin_below_voice_peak_db": voice_peak_db - peak_db,
        "short_term_lufs": short_term, "margin_below_voice_lufs_db": voice_lufs - short_term,
        "scaled_for_loudness_db": max(excess, 0.0),
    }
    row["ok"] = (row["margin_below_voice_peak_db"] >= margin_db - EPS_DB
                 and row["margin_below_voice_lufs_db"] >= margin_db - EPS_DB)
    return stem, row


# ----------------------------------------------------------------------- mix

def _rounded(value):
    if isinstance(value, float):
        return round(value, 2)
    if isinstance(value, dict):
        return {k: _rounded(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_rounded(v) for v in value]
    return value


def mix(narration: dict | str | Path, voice_wav: str | Path, cues: list[dict], out_wav: str | Path, *,
        voice_lufs: float = -16.0, room_rms_dbfs: float = -48.0, cue_margin_db: float = 12.0,
        sample_rate: int = 48000, seed: int = 7, peak_guard: str = "limit") -> dict:
    """Mix voice, room tone and cues into out_wav; write and return the levels report.

    `peak_guard` ("limit" or "attenuate") chooses what happens when the voice at the
    loudness target would exceed the true-peak ceiling; see _voice_stem.
    """
    if not isinstance(narration, dict):
        narration = json.loads(Path(narration).read_text(encoding="utf-8"))
    if "frames" in narration and "fps" in narration:
        duration = narration["frames"] / narration["fps"]
    else:
        duration = float(narration["duration_s"])
    length = int(round(duration * sample_rate))
    out_path = Path(out_wav)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    voice, voice_info = _voice_stem(voice_wav, length, sample_rate, voice_lufs, peak_guard)
    voice_lufs_final = integrated_lufs(voice, sample_rate)
    voice_peak_db = sample_peak_dbfs(voice)
    room = _room_tone(length, sample_rate, room_rms_dbfs, np.random.default_rng([seed, 1000003]))

    bus = np.zeros((length, 2))
    rows = []
    for index, cue in enumerate(cues):
        stem, row = _cue_stem(cue, index, length, sample_rate, seed, voice_peak_db,
                              voice_lufs_final, cue_margin_db)
        bus += stem
        rows.append(row)

    mixed = voice + room + bus
    mix_guard_db = 0.0
    mix_true_peak = true_peak_dbtp(mixed)
    if mix_true_peak > TRUE_PEAK_CEILING_DBTP:
        # Room tone and cues add a little to the voice peak; scale the whole mix, and say so.
        mix_guard_db = mix_true_peak - TRUE_PEAK_CEILING_DBTP
        mixed = mixed * db_to_lin(-mix_guard_db)
    sf.write(fresh(out_path), mixed, sample_rate, subtype="PCM_24")

    written, written_rate = sf.read(out_path, dtype="float64")
    mix_lufs = integrated_lufs(written, written_rate)
    mix_tp = true_peak_dbtp(written)
    room_rms = rms_dbfs(room)
    cue_peak_ok = all(r["margin_below_voice_peak_db"] >= cue_margin_db - EPS_DB for r in rows)
    cue_loud_ok = all(r["margin_below_voice_lufs_db"] >= cue_margin_db - EPS_DB for r in rows)
    checks = {
        "voice_lufs_within_tolerance": abs(voice_lufs_final - voice_lufs) <= VOICE_LUFS_TOLERANCE,
        "true_peak_at_or_below_ceiling": mix_tp <= TRUE_PEAK_CEILING_DBTP + EPS_DB,
        "room_rms_within_tolerance": abs(room_rms - room_rms_dbfs) <= ROOM_RMS_TOLERANCE_DB,
        "cue_peak_margins": cue_peak_ok,
        "cue_loudness_margins": cue_loud_ok,
        "length_matches_narration": written.shape[0] == length and written_rate == sample_rate,
        "no_voice_peak_guard_needed": voice_info["true_peak_guard_mode"] == "none",
        "no_mix_peak_guard_needed": mix_guard_db == 0.0,
    }
    report = {
        "voice_lufs_target": voice_lufs,
        "voice_lufs": voice_lufs_final,
        "voice_peak_dbfs": voice_peak_db,
        "voice_true_peak_dbtp": true_peak_dbtp(voice),
        "voice_gain_db": voice_info["voice_gain_db"],
        "true_peak_guard_applied": voice_info["true_peak_guard_mode"] != "none",
        "true_peak_guard_mode": voice_info["true_peak_guard_mode"],
        "true_peak_guard_db": voice_info["true_peak_guard_db"],
        "mix_guard_db": mix_guard_db,
        "mix_lufs": mix_lufs,
        "mix_true_peak_dbtp": mix_tp,
        "room_rms_dbfs": room_rms,
        "cue_margin_db": cue_margin_db,
        "duration_s": length / sample_rate,
        "sample_rate": sample_rate,
        "cues": rows,
        "checks": checks,
    }
    # The two "no_*_guard_needed" checks are advisory: a guard that acted is
    # reported, and the hard checks above already judge the result.
    advisory = {"no_voice_peak_guard_needed", "no_mix_peak_guard_needed"}
    report["ok"] = all(v for k, v in checks.items() if k not in advisory) and all(r["ok"] for r in rows)
    report = _rounded(report)
    save_text(out_path.with_suffix(".levels.json"), json.dumps(report, indent=1) + "\n")
    return report
