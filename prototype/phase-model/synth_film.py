"""Synthesise each sentence with Kokoro (bm_fable, en-gb, 0.92), lay them out, write narration.json and audio/voice24k.wav.
Run: python3 -I synth_film.py"""
import json, os
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
HERE = os.path.dirname(os.path.abspath(__file__))
M = "/tmp/claude-0/-home-user-lumieralight/34561104-772d-5286-9a85-b273e18c62c0/scratchpad/history/voice/model/"
SENT = [  # id, beat, text
 ("s1", 1, "Stonehenge, in Wiltshire, is about four and a half thousand years old."),
 ("s2a", 2, "Thirty tall stones once made its outer circle."),
 ("s2b", 2, "Sixteen still stand."),
 ("s4", 4, "The light shows where the others stood, and the ring of lintels they carried."),
 ("s5", 5, "Inside stood five great trilithons, each two uprights and a lintel."),
 ("s6a", 6, "White is stone that stands today."),
 ("s6b", 6, "Light is what we infer."),
]
PREFIX_S4 = "The light shows where the others stood, and"
GAP = 0.38          # between sentences in the same beat (>= 0.35)
GAP_B = {"s2b>s4": 2.25, "s6a>s6b": 0.38}  # beat 3 is silent (about 2 s) before s4
START = 0.4
k = Kokoro(M + "kokoro-v1.0.onnx", M + "voices-v1.0.bin")
def synth(t):
    a, sr = k.create(t, voice="bm_fable", speed=0.92, lang="en-gb")
    a = np.asarray(a, np.float32)
    idx = np.where(np.abs(a) > 0.006)[0]
    pad = int(0.012 * sr)
    return a[max(0, idx[0] - pad): idx[-1] + pad], sr
clips = {}
for i, b, t in SENT:
    clips[i], sr = synth(t)
pre, _ = synth(PREFIX_S4)
os.makedirs(os.path.join(HERE, "audio"), exist_ok=True)
t = START; out = []; prev = None
for i, b, text in SENT:
    if prev:
        t += GAP_B.get(prev + ">" + i, GAP)
    d = len(clips[i]) / sr
    out.append(dict(id=i, beat=b, text=text, start_s=round(t, 3), end_s=round(t + d, 3)))
    prev = i; t += d
for o in out:
    if o["id"] == "s4":
        o["lintels_s"] = round(o["start_s"] + max(0.0, len(pre) / sr - 0.08), 3)
END = out[-1]["end_s"] + 2.5          # beat 7: hold 2.5 s of silence
dur = round(END * 30) / 30
nar = dict(voice="bm_fable", lang="en-gb", speed=0.92, sample_rate=sr, duration_s=round(dur, 4), frames=round(dur * 30), sentences=out)
json.dump(nar, open(os.path.join(HERE, "narration.json"), "w"), indent=1)
buf = np.zeros(int(round(dur * sr)) + sr, np.float32)
for o in out:
    c = clips[o["id"]].copy(); n = int(0.02 * sr)
    c[:n] *= np.linspace(0, 1, n); c[-n:] *= np.linspace(1, 0, n)
    s = int(round(o["start_s"] * sr)); buf[s:s + len(c)] += c
sf.write(os.path.join(HERE, "audio", "voice24k.wav"), buf[:int(round(dur * sr))], sr)
for o in out: print(o)
print("duration", dur, "frames", round(dur * 30))
