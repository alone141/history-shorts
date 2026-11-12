"""Ten-second narrator samples: the same line in several Kokoro voices. Run with python3 synth.py."""
import json, os, time
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

HERE = os.path.dirname(os.path.abspath(__file__))
TEXT = ("Stonehenge, in Wiltshire, is about four and a half thousand years old. "
        "About half of its thirty circle stones still stand. "
        "The light shows where the others stood.")
VOICES = [  # letter, voice id, accent, description
    ("A", "bm_george", "en-gb", "British, male"),
    ("B", "bm_fable", "en-gb", "British, male"),
    ("C", "bf_emma", "en-gb", "British, female"),
    ("D", "bf_isabella", "en-gb", "British, female"),
    ("E", "am_michael", "en-us", "American, male"),
    ("F", "af_heart", "en-us", "American, female"),
]
k = Kokoro(os.path.join(HERE, "model", "kokoro-v1.0.onnx"), os.path.join(HERE, "model", "voices-v1.0.bin"))
have = set(k.get_voices())
out = []
for letter, vid, lang, desc in VOICES:
    assert vid in have, vid
    t = time.time()
    audio, sr = k.create(TEXT, voice=vid, speed=0.92, lang=lang)
    audio = np.asarray(audio, dtype=np.float32)
    path = os.path.join(HERE, "out", f"{letter}_{vid}.wav")
    sf.write(path, audio, sr)
    dur = len(audio) / sr
    out.append(dict(letter=letter, voice=vid, lang=lang, desc=desc, wav=path, seconds=round(dur, 2), peak=round(float(np.abs(audio).max()), 3)))
    print(letter, vid, desc, f"{dur:.2f} s", f"synth {time.time()-t:.1f} s", flush=True)
json.dump(dict(text=TEXT, speed=0.92, samples=out), open(os.path.join(HERE, "out", "samples.json"), "w"), indent=1)
print(len(TEXT.split()), "words; voices available:", len(have))
