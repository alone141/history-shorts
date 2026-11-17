"""End-to-end self-test of the voice, sound and encode modules.

Synthesises a two-sentence script with one cue, mixes it with three code-made
cues, encodes 90 generated frames with that audio, and prints a PASS/FAIL table
of every numeric check. It also checks the pitch engine: the editable copy of
the voice model gives the stock model's samples when nothing is set, a question
ends on a measured rise, an accent lands on its word, and a narration made with
"prosody" is repeatable. Output goes under build/selftest/.

Run from the repository root:  python -m engine.selftest_av
The exit status is 0 only if every check passes.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from engine import encode, sound, voice
from engine.files import fresh, write_text as save_text

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "selftest"
FPS = 30
FRAMES = 90
SIZE = (1080, 1920)

SCRIPT = [
    {"id": "s1", "beat": 1, "text": "Dawn breaks.", "cues": {"breaks": "Dawn"}},
    {"id": "s2", "beat": 2, "text": "Quiet."},
]


def moving_gradient_frames(count: int):
    """Yield RGB frames: a diagonal gradient that drifts, with the frame number drawn in."""
    width, height = SIZE
    xs = np.arange(width, dtype=np.int32)[None, :]
    ys = np.arange(height, dtype=np.int32)[:, None]
    font = ImageFont.load_default(size=240)
    for n in range(count):
        shift = n * 6
        frame = np.empty((height, width, 3), dtype=np.uint8)
        frame[..., 0] = ((xs + shift) % 256)
        frame[..., 1] = ((ys // 8 + shift // 2) % 256)
        frame[..., 2] = ((xs // 2 + ys // 4 + 2 * shift) % 256)
        image = Image.fromarray(frame)
        ImageDraw.Draw(image).text((60, 800), f"{n:03d}", font=font, fill=(255, 255, 255),
                                   stroke_width=8, stroke_fill=(0, 0, 0))
        yield np.asarray(image)


def digest(*paths: Path) -> str:
    h = hashlib.sha256()
    for path in paths:
        h.update(path.read_bytes())
    return h.hexdigest()[:12]


def main() -> int:
    started = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    rows: list[tuple[str, str, str, bool]] = []  # name, measured, requirement, passed

    def check(name: str, measured: str, requirement: str, passed: bool) -> None:
        rows.append((name, measured, requirement, bool(passed)))

    # --- voice
    # Pick the tail so the narration is exactly FRAMES frames long (the second call is cached).
    probe_run = voice.synthesise(SCRIPT, OUT / "voice", fps=FPS, tail=0.0)
    tail = FRAMES / FPS - probe_run["sentences"][-1]["end_s"] - 0.005
    narration = voice.synthesise(SCRIPT, OUT / "voice", fps=FPS, tail=tail)
    first = digest(OUT / "voice" / "voice.wav", OUT / "voice" / "narration.json")
    cache_started = time.time()
    voice.synthesise(SCRIPT, OUT / "voice", fps=FPS, tail=tail)
    cache_seconds = time.time() - cache_started
    second = digest(OUT / "voice" / "voice.wav", OUT / "voice" / "narration.json")
    s1, s2 = narration["sentences"]
    check("voice: rerun identical (cached)", f"{first}/{second} {cache_seconds:.2f}s", "same hash, < 2 s",
          first == second and cache_seconds < 2.0)
    check("voice: cue inside its sentence", f"{s1['cues']['breaks']:.3f}s in [{s1['start_s']}, {s1['end_s']}]",
          "start <= cue <= end", s1["start_s"] <= s1["cues"]["breaks"] <= s1["end_s"])
    check("voice: sentences ordered, gap", f"{s2['start_s'] - s1['end_s']:.3f}s", "0.38 +/- 0.002",
          abs(s2["start_s"] - s1["end_s"] - 0.38) < 0.002)
    check("voice: narration frame count", f"{narration['frames']} frames", str(FRAMES), narration["frames"] == FRAMES)

    # --- pitch (engine/pitch.py): the narrator's intonation is set and then measured
    from engine import pitch

    models = ROOT / "models" / "kokoro"
    settings = {k: v for k, v in json.loads((ROOT / "engine" / "tokens.json").read_text(encoding="utf-8"))["prosody"].items()
                if not k.startswith("_")}
    question = "Can you see the piers?"

    def speak(text: str, own: dict, prosody: dict):
        return pitch.speak(text, voice="af_heart", lang="en-us", speed=1.15, plan=pitch.plan_for({"id": "t", "pitch": own}, prosody),
                           model_dir=models)

    alone = speak(question, {"ends": ["keep"]}, {"range": 1.0, "stretch": 1.0, "rise_stretch": 1.0})
    kokoro = voice._load_kokoro(models)
    tokens = kokoro.tokenizer.tokenize(kokoro.tokenizer.phonemize(question, "en-us"))
    stock, _ = kokoro._infer(tokens, kokoro._style_for(kokoro.voices["af_heart"], len(tokens)), 1.15)
    same = stock.size == alone.audio.size and float(np.abs(stock - alone.audio).max()) < 1e-3
    check("pitch: editable model, nothing set", f"{stock.size}/{alone.audio.size} samples, max diff "
          f"{float(np.abs(stock - alone.audio).max()) if stock.size == alone.audio.size else float('nan'):.1e}", "the stock model's samples", same)
    asked = pitch.measure(speak(question, {}, settings))
    rise = next((p for p in asked["phrases"] if p["end"] == "rise"), {})
    check("pitch: a question ends on a rise", f"{rise.get('got_st')} st, {rise.get('voiced')} of it cleanly voiced",
          f">= {pitch.HEARD_RISE_ST} st and clean", bool(rise.get("ok")))
    heard, follows = pitch.follow(alone)
    tail = heard[-80:][follows[-80:]]
    check("pitch: the model alone, same question", f"{12 * np.log2(tail[-3:].mean() / tail.min()):+.1f} st at the end" if tail.size > 4 else "no pitch at the end",
          "info only", True)
    accent = pitch.measure(speak("The Romans tied the blocks with iron clamps.", {"focus": ["iron"]}, settings))
    check("pitch: an accent lands on its word", f"{accent['focus'][0].get('got_st')} st over the line", f">= {settings['focus_st'] - 1.0} st",
          bool(accent["focus"][0].get("ok")) and accent["ok"])
    lines = [{"id": "p1", "text": question}, {"id": "p2", "text": "Those dark dots are holes.", "pitch": {"focus": ["holes"]}}]
    spoken = dict(voice="af_heart", lang="en-us", speed=1.15, fps=FPS, prosody=settings)
    pitched = voice.synthesise(lines, OUT / "voice_pitch", **spoken)
    once = digest(OUT / "voice_pitch" / "voice.wav", OUT / "voice_pitch" / "narration.json")
    voice.synthesise(lines, OUT / "voice_pitch", **spoken)
    check("pitch: narration rerun identical", f"{once}/{digest(OUT / 'voice_pitch' / 'voice.wav', OUT / 'voice_pitch' / 'narration.json')}",
          "same hash", once == digest(OUT / "voice_pitch" / "voice.wav", OUT / "voice_pitch" / "narration.json"))
    words = pitched["sentences"][0]["words"]
    starts = [w["start_s"] for w in words]
    check("pitch: word times", f"{len(words)} words, {starts[0]:.2f} to {starts[-1]:.2f} s", "5 words, in order, inside the sentence",
          len(words) == 5 and starts == sorted(starts) and pitched["sentences"][0]["start_s"] - 0.06 <= starts[0]
          and words[-1]["end_s"] <= pitched["sentences"][0]["end_s"] + 0.3)
    check("pitch: sheet drawn", "pitch.png", "exists", (OUT / "voice_pitch" / "pitch.png").exists())

    # --- sound
    cues = [
        {"type": "tick", "t": s1["cues"]["breaks"]},
        {"type": "swell", "t": 0.1, "dur": 0.3, "gain_db": -2.0},
        {"type": "thump", "t": s2["start_s"] - 0.2},
    ]
    mix_path = OUT / "mix.wav"
    report = sound.mix(narration, OUT / "voice" / "voice.wav", cues, mix_path)
    mix_hash_a = digest(mix_path)
    sound.mix(narration, OUT / "voice" / "voice.wav", cues, mix_path)
    check("sound: rerun identical", f"{mix_hash_a}/{digest(mix_path)}", "same hash", mix_hash_a == digest(mix_path))
    check("sound: voice LUFS", f"{report['voice_lufs']:.2f}", "-16.0 +/- 0.3", abs(report["voice_lufs"] + 16.0) <= 0.3)
    check("sound: voice peak guard", f"{report['true_peak_guard_mode']} {report['true_peak_guard_db']:.2f} dB",
          "reported if it acts", True)
    check("sound: mix true peak dBTP", f"{report['mix_true_peak_dbtp']:.2f}", "<= -1.5", report["mix_true_peak_dbtp"] <= -1.49)
    check("sound: mix integrated LUFS", f"{report['mix_lufs']:.2f}", "info only", True)
    check("sound: room RMS dBFS", f"{report['room_rms_dbfs']:.2f}", "-48.0 +/- 0.5", abs(report["room_rms_dbfs"] + 48.0) <= 0.5)
    for cue in report["cues"]:
        label = f"{cue['type']}@{cue['t']:.2f}"
        check(f"cue {label}: peak margin dB", f"{cue['margin_below_voice_peak_db']:.1f}", ">= 12", cue["margin_below_voice_peak_db"] >= 11.99)
        check(f"cue {label}: loudness margin dB", f"{cue['margin_below_voice_lufs_db']:.1f}", ">= 12", cue["margin_below_voice_lufs_db"] >= 11.99)
    check("sound: report ok flag", str(report["ok"]), "True", report["ok"])
    check("sound: levels.json written", mix_path.with_suffix(".levels.json").name, "exists", mix_path.with_suffix(".levels.json").exists())

    # Stress: a hotter target forces the true-peak limiter to act, so that path is exercised too.
    hot = sound.mix(narration, OUT / "voice" / "voice.wav", [], OUT / "mix_hot.wav", voice_lufs=-13.0)
    check("limiter: guard mode", f"{hot['true_peak_guard_mode']} {hot['true_peak_guard_db']:.2f} dB", "limiter acts at -13 LUFS",
          hot["true_peak_guard_mode"] == "limiter")
    check("limiter: voice LUFS kept", f"{hot['voice_lufs']:.2f}", "-13.0 +/- 0.3", abs(hot["voice_lufs"] + 13.0) <= 0.3)
    check("limiter: mix true peak dBTP", f"{hot['mix_true_peak_dbtp']:.2f}", "<= -1.5", hot["mix_true_peak_dbtp"] <= -1.49)

    # --- encode
    mp4 = OUT / "selftest.mp4"
    info = encode.encode(moving_gradient_frames(FRAMES), mix_path, mp4, fps=FPS, size=SIZE, preset="medium")
    save_text(OUT / "probe.json", json.dumps(info, indent=1))
    video, audio = info["video"], info["audio"]
    frame_s = 1.0 / FPS
    check("mp4: size", f"{video['width']}x{video['height']}", "1080x1920", (video["width"], video["height"]) == SIZE)
    check("mp4: pixel format", video["pix_fmt"], "yuv420p", video["pix_fmt"] == "yuv420p")
    check("mp4: codec / profile", f"{video['codec']} {video['profile']}", "h264 High", (video["codec"], video["profile"]) == ("h264", "High"))
    check("mp4: fps", f"{video['fps']:.3f}", "30", abs(video["fps"] - FPS) < 1e-6)
    check("mp4: constant frame timestamps", str(video["constant_frame_rate"]), "True", video["constant_frame_rate"])
    check("mp4: frame count", str(video["frames"]), str(FRAMES), video["frames"] == FRAMES)
    check("mp4: max keyframe interval", str(video["max_keyframe_interval"]), "<= 60", video["max_keyframe_interval"] <= 60)
    tags = (video["color_primaries"], video["color_trc"], video["colorspace"], video["color_range"])
    check("mp4: colour tags", "/".join(map(str, tags)), "bt709/bt709/bt709/tv", tags == ("bt709", "bt709", "bt709", "tv"))
    check("mp4: faststart (moov before mdat)", " ".join(info["top_level_atoms"]), "moov first", info["faststart"])
    check("mp4: audio codec / profile", f"{audio['codec']} {audio['profile']}", "aac LC", (audio["codec"], audio["profile"]) == ("aac", "LC"))
    check("mp4: audio rate / channels", f"{audio['sample_rate']} Hz x{audio['channels']}", "48000 Hz x2", (audio["sample_rate"], audio["channels"]) == (48000, 2))
    check("mp4: audio bit rate", str(audio["bit_rate"]), "192000 +/- 15%", abs(audio["bit_rate"] - 192000) <= 0.15 * 192000)
    check("mp4: container duration s", f"{info['duration_s']:.3f}", f"{FRAMES / FPS:.3f} +/- 1 frame", abs(info["duration_s"] - FRAMES / FPS) <= frame_s)
    gap = abs(video["duration_s"] - audio["duration_s"])
    check("mp4: video vs audio duration", f"{video['duration_s']:.3f} / {audio['duration_s']:.3f}", "within 1 frame (0.033 s)", gap <= frame_s + 1e-6)

    # --- table
    width = max(len(r[0]) for r in rows)
    width_m = max(len(r[1]) for r in rows)
    print(f"{'check'.ljust(width)}  {'measured'.ljust(width_m)}  requirement                result")
    for name, measured, requirement, passed in rows:
        print(f"{name.ljust(width)}  {measured.ljust(width_m)}  {requirement.ljust(24)}  {'PASS' if passed else 'FAIL'}")
    failed = [r[0] for r in rows if not r[3]]
    elapsed = time.time() - started
    print(f"\n{len(rows) - len(failed)}/{len(rows)} passed in {elapsed:.1f} s" + (f"; FAILED: {', '.join(failed)}" if failed else ""))
    if elapsed > 120:
        print("FAIL: self-test took longer than 2 minutes")
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
