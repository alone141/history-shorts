"""Build audio/mix.m4a: voice (loudnorm -16 LUFS) + room tone + cues, all numpy. Run: python3 -I sound_film.py
Needs narration.json + audio/voice24k.wav (from synth_film.py) and the picks times printed by scene_film.html (recomputed here)."""
import json, os, subprocess, math
import numpy as np, soundfile as sf
H = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(H, "audio")
N = json.load(open(os.path.join(H, "narration.json"))); SR = 48000
T = N["duration_s"]; L = int(round(T * SR)); S = {o["id"]: o for o in N["sentences"]}
rng = np.random.default_rng(7)
db = lambda x: 10 ** (x / 20)
def rms_db(x): return 20 * math.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
def fade(x, a=0.005, b=0.01):
    x = x.copy(); na, nb = max(1, int(a * SR)), max(1, int(b * SR)); x[:na] *= np.linspace(0, 1, na); x[-nb:] *= np.linspace(1, 0, nb); return x
def lp(x, fc):  # one-pole lowpass, repeated
    a = math.exp(-2 * math.pi * fc / SR); y = np.zeros_like(x); s = 0.0
    for i, v in enumerate(x): s = (1 - a) * v + a * s; y[i] = s
    return y
def put(buf, x, t):
    i = int(round(t * SR)); x = x[:max(0, len(buf) - i)]; buf[i:i + len(x)] += x
# ---- voice: loudnorm to -16 LUFS
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(A, "voice24k.wav"), "-af", "aresample=48000,pan=stereo|c0=c0|c1=c0,loudnorm=I=-16:TP=-3:LRA=7:linear=true", "-ar", "48000", "-ac", "2", os.path.join(A, "voice.wav")], check=True)
v, _ = sf.read(os.path.join(A, "voice.wav")); v = v[:, 0]; v = np.pad(v, (0, max(0, L - len(v))))[:L]
vpeak = np.abs(v).max(); cue_max = vpeak * db(-14)   # cues peak >= 14 dB under the voice peak
# ---- room tone (-48 dBFS RMS), faded in and out
room = lp(lp(rng.standard_normal(L), 400), 400); room *= db(-48) / np.sqrt(np.mean(room ** 2))
room *= np.minimum(1, np.minimum(np.arange(L) / (0.6 * SR), (L - np.arange(L)) / (0.6 * SR)))
# ---- cues
cues = np.zeros(L)
def tick(t, g=1.0):
    n = int(0.05 * SR); tt = np.arange(n) / SR
    x = np.sin(2 * np.pi * 1900 * tt) * np.exp(-tt * 140) + 0.4 * np.sin(2 * np.pi * 950 * tt) * np.exp(-tt * 90)
    put(cues, fade(x / np.abs(x).max() * g * db(-32), 0.002, 0.01), t)
# stone ticks: same schedule as scene_film.html (16 stones, smooth non-linear spacing, last on "Sixteen")
PK0 = S["s2a"]["start_s"] + 0.7; PK1 = S["s2b"]["start_s"] + 0.30
ct = [PK0 + (PK1 - PK0) * (0.8 * u + 0.2 * (0.5 - 0.5 * math.cos(math.pi * u))) for u in [i / 15 for i in range(16)]]
for i, t in enumerate(ct): tick(t, 0.8 + 0.2 * ((i * 7) % 5) / 4)
B3 = S["s2b"]["end_s"] + 0.3; CUT = B3 + 0.2; STRIKE = B3 + 0.75
# relay click: two sharp ticks + a small body
n = int(0.09 * SR); tt = np.arange(n) / SR
rel = (rng.standard_normal(n) * np.exp(-tt * 600)) * 0.7 + np.sin(2 * np.pi * 1300 * tt) * np.exp(-tt * 220)
rel2 = np.zeros(int(0.12 * SR)); rel2[:n] += rel; rel2[int(0.055 * SR):int(0.055 * SR) + n] += 0.5 * rel[:n][:len(rel2) - int(0.055 * SR)] if False else 0
r = np.zeros(int(0.14 * SR)); r[:n] += rel; r[int(0.05 * SR):int(0.05 * SR) + n] += 0.55 * rel
put(cues, fade(r / np.abs(r).max() * db(-27), 0.002, 0.02), CUT)
# lamp strike: low thump (pitch drop) + short soft zap through the flicker
n = int(0.6 * SR); tt = np.arange(n) / SR
f = 48 + 40 * np.exp(-tt * 18); th = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 7)
z = lp(rng.standard_normal(n), 3000) * np.exp(-tt * 30) * 0.25
th = th + z; put(cues, fade(th / np.abs(th).max() * db(-25), 0.004, 0.08), STRIKE)
# fan hum: from the strike to the end, faint, rising over 1.5 s
fan = np.zeros(L); tt = np.arange(L) / SR
for fr, g in [(92, 1.0), (184, 0.5), (276, 0.25), (61, 0.5)]: fan += g * np.sin(2 * np.pi * fr * tt + fr)
air = lp(rng.standard_normal(L), 1400) * 0.5; fan = fan / np.sqrt(np.mean(fan ** 2)) + air / np.sqrt(np.mean(air ** 2)) * 0.5
env = np.clip((tt - STRIKE) / 1.5, 0, 1) ** 2 * np.clip((T - tt) / 0.6, 0, 1)
fan *= env; fan *= db(-52) / np.sqrt(np.mean(fan[int(STRIKE * SR) + SR * 2:] ** 2))
cues_peak = np.abs(cues).max()
if cues_peak > cue_max: cues *= cue_max / cues_peak
mix = v + room + cues + fan
mix[:int(0.01 * SR)] *= np.linspace(0, 1, int(0.01 * SR)); mix[-int(0.3 * SR):] *= np.linspace(1, 0, int(0.3 * SR))
sf.write(os.path.join(A, "mix48k.wav"), np.stack([mix, mix], 1).astype(np.float32), SR, subtype="FLOAT")
print(f"voice peak {20*math.log10(vpeak):.1f} dBFS; cue peak {20*math.log10(np.abs(cues).max()):.1f} dBFS (limit {20*math.log10(cue_max):.1f}); room rms {rms_db(room):.1f}; fan rms (after strike+2s) {rms_db(fan[int(STRIKE*SR)+2*SR:-SR]):.1f}")
print("mix peak", f"{20*math.log10(np.abs(mix).max()):.2f} dBFS")
