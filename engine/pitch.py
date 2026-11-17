"""Pitch: the narrator's intonation, set on purpose and then measured.

Kokoro predicts a pitch curve for a clip and renders the audio from it. The
stock model keeps that curve to itself, and on its own it ends most questions
flat. `editable_model` writes a copy of the model with three more inputs (a
multiplier for the pitch curve, one for the energy curve, one for the length of
each phoneme) and three more outputs (the predicted pitch, the energy and the
frames each phoneme takes). With every multiplier at 1 the copy gives the same
samples as the original.

A clip is made in two passes. The first returns the model's own pitch curve and
where every phoneme falls, so words can be found in time. A plan is then laid
over that curve, in semitones:

    range      the model's own movement about the line's median, scaled (1.3 = livelier)
    level      the whole line moved up or down
    focus      a pitch accent on chosen words: the stressed syllable is lifted to
               at least `focus_st` above the words around it
    ends       what each phrase does at its end:
                 "rise"      low on the last stressed syllable, then up by `rise_st`
                             (a yes/no question)
                 "fall"      down to `fall_st` below the median (a statement)
                 "continue"  a small rise of `continue_st` (more is coming)
                 "keep"      the model's own ending

The second pass renders the audio from the planned curve: the model's own
decoder makes the sound, so there is no pitch-shifting of finished audio.

Two things measured on this model shape the code. The sound runs about 50 ms
ahead of the frames the model reports for a phoneme (17 fricatives: median 4
curve points, spread 2), so every word position is moved that much earlier.
And at the end of a phrase the model often predicts no pitch at all for the
last word and lets it trail off in a whisper, which is why its questions do not
sound like questions; a rise therefore gives those syllables a pitch and enough
energy to carry it, where scaling the model's curve would change nothing. The
result is then measured from the audio itself with Praat's pitch tracker, and
every asked-for movement is reported next to what came out (`ok` false when it
fell short). `sheet` draws the curves so they can be looked at.

What a pass means. A rise passes only as a glide: at least HEARD_RISE_ST
semitones over at least MIN_GLIDE_MS of unbroken clean voice; a short step
after a gap fails, whatever the first and last values say. An accent passes if
its vowel holds the height for 40 ms over the words around it. A fall is
reported as heard only where there is voice to hear: the model ends most
statements in a creak that no tracker follows, shaped or not, and those are
reported as set, not heard. Nothing here measures how natural the voice sounds.

A script line carries its plan under "pitch"; a film switches the engine on with
a "prosody" dictionary (its values override tokens.json "prosody"):

    {"id": "s2", "text": "Can you see the piers?", "pitch": {"focus": ["see"], "ends": ["rise"]}}

Without "ends" a phrase ending is chosen from its punctuation: "?" rises unless
the sentence opens with a question word (what, why, how ...), which falls; "."
and "!" fall; ":" continues; "," keeps what the model did.
"""
from __future__ import annotations

import difflib
import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

RATE = 24000
FRAME_S = 0.025            # one duration frame of the model is 600 samples
F0_STEP_S = FRAME_S / 2    # the pitch curve has two points per duration frame
VOICED_HZ = 50.0           # the model writes 0 where there is no voice
LEAD = 4                   # curve points by which the sound runs ahead of the reported phoneme frames
SOUND_BELOW_PEAK_DB = 32.0 # quieter than this under the clip's loudest moment is not speech
HISS_SHARE = 0.35          # more of the energy than this above 4 kHz is a hiss (s, f, sh), not a voice
ENGINE_VERSION = "18"       # part of the clip cache key: bump when the shaping changes
MODEL_NAME, EDITABLE_NAME = "kokoro-v1.0.onnx", "kokoro-v1.0-pitch.onnx"

STRESS = "ˈˌ"
VOWELS = set("aeiouyɑɐɒæəɘɚɛɜɝɞɨɪʊʌɔøœɶʉɯɤʏᵻᵊAIOWYQ")
SONORANT = VOWELS | set("ɹlmnŋwjɾrɫ") | {"ː"} | set(STRESS)
MAJOR, MINOR = ".?!", ",;:—…"
WH_WORDS = {"what", "why", "who", "whom", "whose", "where", "when", "how", "which"}
END_KINDS = ("rise", "fall", "continue", "keep")

DEFAULTS = {
    "range": 1.0, "level": 0.0,
    "focus_st": 4.0, "stretch": 1.0,
    "rise_st": 7.0, "rise_low_st": -1.5, "rise_floor_st": -4.0, "rise_top_min_st": 4.0, "rise_stretch": 1.0, "rise_energy": -1.0,
    "fall_st": 4.0, "continue_st": 2.5, "continue_energy": -1.0,
    "floor_st": -8.0, "ceiling_st": 10.0,       # about as low and as high as this voice goes by itself
}
# The settings were tested inside these limits; outside them the voice gets rough (rises over about 9
# semitones, movement scaled over 1.6) or the setting stops meaning anything.
LIMITS = {"range": (0.5, 1.6), "focus_st": (0.0, 8.0), "stretch": (1.0, 1.3), "rise_st": (4.0, 9.0), "rise_stretch": (1.0, 1.3),
          "fall_st": (0.0, 8.0), "continue_st": (0.0, 5.0)}
OPENERS = {"so", "and", "but", "then", "well", "now", "ok", "okay"}
# how far a measured movement may fall short of what was asked and still pass
TOLERANCE = {"rise": 0.75, "fall_st": 1.0, "continue": 0.6, "focus_st": 1.0}
HEARD_RISE_ST = 4.0        # under this a final rise is too small to be heard as a question
ACCENT_MARGIN_ST = 0.5     # short peaks are heard a little under the pitch set, so an accent is set this much over
MIN_GLIDE_MS = 100         # a question's rise has to climb over at least this long a stretch of unbroken clean voice
CLEAN_RISE_SHARE = 0.55    # at least this share of a question's rise has to be cleanly voiced
FOLLOW_ST = 1.5            # the audio "follows" the curve it was rendered from when it is this close to it

# tensors of the stock export that the editable copy taps
_F0, _N = "/encoder/Reshape_output_0", "/encoder/Reshape_1_output_0"
_DUR, _DUR_IN = "/encoder/Clip_output_0", "/encoder/Div_output_0"
_REWIRE = {"/decoder/decoder/Unsqueeze": (_F0, "f0"), "/decoder/decoder/Unsqueeze_1": (_N, "n"), "/encoder/Round": (_DUR_IN, "dur")}
_INPUTS = ("f0_mul", "f0_add", "n_mul", "n_add", "dur_mul")


# ------------------------------------------------------------------ the model
def editable_model(model_dir: str | Path) -> Path:
    """The copy of the model whose pitch, energy and phoneme lengths can be set; built once."""
    model_dir = Path(model_dir)
    src, dst = model_dir / MODEL_NAME, model_dir / EDITABLE_NAME
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return dst
    import onnx
    from onnx import TensorProto, helper

    model = onnx.load(str(src))
    graph, nodes, found = model.graph, [], set()

    def control(name: str) -> str:
        graph.input.append(helper.make_tensor_value_info(name, TensorProto.FLOAT, [1, name + "_length"]))
        return name

    for node in graph.node:
        if node.name in _REWIRE:
            tensor, key = _REWIRE[node.name]
            if node.input[0] != tensor:
                raise RuntimeError(f"{src.name}: node {node.name} does not read {tensor}; this is not the export the pitch engine knows")
            nodes.append(helper.make_node("Mul", [tensor, control(key + "_mul")], [key + "_scaled"], name=f"/pitch/{key}_mul"))
            last = key + "_scaled"
            if key != "dur":
                nodes.append(helper.make_node("Add", [last, control(key + "_add")], [key + "_set"], name=f"/pitch/{key}_add"))
                last = key + "_set"
            node.input[0] = last
            found.add(node.name)
        nodes.append(node)
    if found != set(_REWIRE):
        raise RuntimeError(f"{src.name}: nodes {sorted(set(_REWIRE) - found)} not found; this is not the export the pitch engine knows")
    for name, tensor in (("f0", _F0), ("n", _N), ("duration", _DUR)):
        nodes.append(helper.make_node("Identity", [tensor], [name], name="/pitch/out_" + name))
        graph.output.append(helper.make_empty_tensor_value_info(name))
    del graph.node[:]
    graph.node.extend(nodes)
    part = dst.with_name(f"{dst.name}.{os.getpid()}.part")       # its own name, so two builders cannot cut across each other
    onnx.save(model, str(part))
    os.replace(part, dst)
    return dst


_loaded: dict[str, Any] = {}


def _load(model_dir: Path) -> tuple[Any, Any]:
    """(onnx session of the editable model, kokoro_onnx object for its tokenizer and voices)."""
    key = str(model_dir)
    if key not in _loaded:
        import onnxruntime as rt
        from kokoro_onnx import Kokoro

        session = rt.InferenceSession(str(editable_model(model_dir)), providers=["CPUExecutionProvider"])
        if {i.name for i in session.get_inputs()} != {"tokens", "style", "speed", *_INPUTS}:     # a copy from an older engine
            del session
            (model_dir / EDITABLE_NAME).unlink()
            session = rt.InferenceSession(str(editable_model(model_dir)), providers=["CPUExecutionProvider"])
        _loaded[key] = (session, Kokoro.from_session(session, str(model_dir / "voices-v1.0.bin")))
    return _loaded[key]


# ------------------------------------------------------------------ words in time
@dataclass
class Word:
    text: str                      # as written in the line
    span: tuple[int, int]          # phoneme positions [a, b)
    stress: int                    # phoneme position where the stressed syllable starts
    vowel: tuple[int, int]         # phoneme positions of the stressed vowel
    primary: bool                  # the word carries a primary stress


@dataclass
class Phrase:
    span: tuple[int, int]          # phoneme positions [a, b), punctuation included
    mark: str                      # the punctuation that ends it ("" at the end of an unpunctuated line)
    words: list[int] = field(default_factory=list)
    first_of_sentence: int = 0     # index of the word that opens the sentence this phrase belongs to


def _plain(word: str) -> str:
    return re.sub(r"[^\w'-]", "", word.lower().replace("’", "'")).strip("-'")


def _strip(phonemes: str) -> str:
    return "".join(c for c in phonemes if c not in STRESS and c not in MAJOR and c not in MINOR and c != " ")


def _word_spans(phonemes: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in re.finditer(r"[^ ]+", phonemes)]


def align_words(text: str, phonemes: str, phonemize) -> list[tuple[int, int]]:
    """Phoneme span of every written word.

    Usually the phonemizer gives one group of phonemes per written word. It runs some pairs together ("in the"),
    reads a figure as several words ("1651"), and drops a dash that stands alone; those cases are matched by how
    each written word sounds on its own. If nothing fits, the groups are shared out in order: word times are
    then approximate, and nothing stops.
    """
    written, spans = text.split(), _word_spans(phonemes)
    real = [i for i, w in enumerate(written) if re.search(r"\w", w)]       # a lone dash or quote mark makes no sound
    n, m = len(real), len(spans)
    placed: list[tuple[int, int]] = [(0, 0)] * n
    if n == m:
        placed = list(spans)
    elif n and m:
        alone = [_strip(phonemize(written[i])) or "?" for i in real]
        heard = [_strip(phonemes[a:b]) for a, b in spans]
        unlike = lambda x, y: 1.0 - difflib.SequenceMatcher(None, x, y).ratio()
        cost = np.full((n + 1, m + 1), np.inf)
        back = np.zeros((n + 1, m + 1, 2), dtype=int)
        cost[0, 0] = 0.0
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                steps = [(k, 1) for k in range(1, min(3, i) + 1)] + [(1, g) for g in range(2, min(6, j) + 1)]
                for k, g in steps:               # k written words in one spoken group, or one written word in g groups
                    if np.isfinite(cost[i - k, j - g]):
                        c = cost[i - k, j - g] + unlike("".join(alone[i - k:i]), "".join(heard[j - g:j]))
                        if c < cost[i, j]:
                            cost[i, j], back[i, j] = c, (k, g)
        if np.isfinite(cost[n, m]):
            i, j = n, m
            while i > 0:
                k, g = (int(v) for v in back[i, j])
                a, b = spans[j - g][0], spans[j - 1][1]
                sizes = [len(alone[x]) for x in range(i - k, i)]
                shares = np.cumsum([0] + sizes) / max(1, sum(sizes))
                for step, x in enumerate(range(i - k, i)):
                    placed[x] = (a + int(round(shares[step] * (b - a))), a + int(round(shares[step + 1] * (b - a))))
                i, j = i - k, j - g
        else:
            edges = np.linspace(0, m, n + 1).round().astype(int)
            for x in range(n):
                first, last = min(edges[x], m - 1), min(max(edges[x + 1], edges[x] + 1), m) - 1
                placed[x] = (spans[first][0], spans[last][1])
    out, end = [], 0
    by_index = dict(zip(real, placed))
    for i in range(len(written)):
        span = by_index.get(i, (end, end))       # a mark without sound sits where the word before it ends
        out.append(span)
        end = span[1]
    return out


def _stress_of(phonemes: str, span: tuple[int, int]) -> tuple[int, tuple[int, int], bool]:
    """Where the word's main stressed syllable starts, its vowel, and whether the stress is primary."""
    a, b = span
    chunk = phonemes[a:b]
    at = chunk.rfind("ˈ")
    primary = at >= 0
    if at < 0:
        at = chunk.rfind("ˌ")
    start = a + max(at, 0)
    i = start
    while i < b and phonemes[i] not in VOWELS:
        i += 1
    if i >= b:                                   # no vowel after the mark: take the first vowel of the word
        i = next((x for x in range(a, b) if phonemes[x] in VOWELS), a)
        start = min(start, i)
    j = i
    while j < b and (phonemes[j] in VOWELS or phonemes[j] == "ː"):
        j += 1
    return start, (i, max(j, i + 1)), primary


def lay_out(text: str, phonemes: str, phonemize) -> tuple[list[Word], list[Phrase]]:
    spans = align_words(text, phonemes, phonemize)
    words = []
    for written, span in zip(text.split(), spans):
        stress, vowel, primary = _stress_of(phonemes, span)
        words.append(Word(written, span, stress, vowel, primary))
    phrases, start, opener = [], 0, 0
    for i, c in enumerate(phonemes):
        last = i == len(phonemes) - 1
        if c in MAJOR or c in MINOR or last:
            mark = c if (c in MAJOR or c in MINOR) else ""
            # punctuation can come doubled ("?!"); the phrase takes the first mark
            if phrases and not any(start <= w.span[0] < i + 1 for w in words):
                phrases[-1].span = (phrases[-1].span[0], i + 1)
                start = i + 1
                continue
            inside = [n for n, w in enumerate(words) if start <= w.span[0] < i + 1]
            phrases.append(Phrase((start, i + 1), mark, inside, opener))
            if mark in MAJOR and inside:
                opener = inside[-1] + 1
            start = i + 1
    return words, phrases


# ------------------------------------------------------------------ the plan
def plan_for(item: dict, prosody: dict | None) -> dict:
    """The full plan of one script line: the film's settings, then the line's own "pitch"."""
    settings = {k: v for k, v in (prosody or {}).items() if not k.startswith("_")}
    own = dict(item.get("pitch") or {})
    where = f"line {item.get('id')!r}"
    for name, given in (("the film's prosody", settings), (f"{where} pitch", {k: v for k, v in own.items() if k not in ("focus", "ends", "end")})):
        unknown = sorted(set(given) - set(DEFAULTS))
        if unknown:
            raise ValueError(f"{name}: unknown setting {unknown}; a line may give focus, ends and {sorted(DEFAULTS)}")
    plan = {**DEFAULTS, **{k: float(v) for k, v in settings.items()}}
    for key in DEFAULTS:
        if key in own:
            plan[key] = float(own[key])
    for key, (low, high) in LIMITS.items():
        if not low <= plan[key] <= high:
            raise ValueError(f"{where}: {key} is {plan[key]}; it was only tested from {low} to {high}")
    focus = []
    for f in own.get("focus", []):
        f = {"word": f} if isinstance(f, str) else dict(f)
        entry = {"word": f["word"], "nth": int(f.get("nth", 1)), "st": float(f.get("st", plan["focus_st"])),
                 "stretch": float(f.get("stretch", plan["stretch"]))}
        if entry["nth"] < 1 or not LIMITS["focus_st"][0] <= entry["st"] <= LIMITS["focus_st"][1]:
            raise ValueError(f"{where}: focus {f!r}: nth counts from 1 and st runs from {LIMITS['focus_st'][0]} to {LIMITS['focus_st'][1]}")
        focus.append(entry)
    plan["focus"] = focus
    ends = own.get("ends", own.get("end"))
    if isinstance(ends, str):
        ends = [ends]
    for e in ends or []:
        if e is not None and e not in END_KINDS:
            raise ValueError(f"line {item.get('id')!r}: unknown phrase ending {e!r}; use one of {END_KINDS}")
    plan["ends"] = list(ends) if ends else None
    return plan


def _default_end(phrase: Phrase, words: list[Word]) -> str:
    if phrase.mark == "?":
        # a question that opens on a question word falls ("So what is the answer?"); every other one rises,
        # also one with such a word inside it ("Is this what the clamps did?")
        opening = [re.sub(r"'(s|re|d|ll|ve)$", "", _plain(w.text)) for w in words[phrase.first_of_sentence:phrase.first_of_sentence + 3]]
        while len(opening) > 1 and opening[0] in OPENERS:              # "what's" counts as "what"
            opening = opening[1:]
        return "fall" if opening and opening[0] in WH_WORDS else "rise"
    if phrase.mark in (".", "!"):
        return "fall"
    if phrase.mark == ":":
        return "continue"
    return "keep"


def _find_word(words: list[Word], wanted: str, nth: int) -> int:
    hits = [i for i, w in enumerate(words) if _plain(w.text) == _plain(wanted)]
    if len(hits) < nth:
        raise ValueError(f"focus word {wanted!r} (occurrence {nth}) is not in the line: {' '.join(w.text for w in words)!r}")
    return hits[nth - 1]


def endings_of(words: list[Word], phrases: list[Phrase], plan: dict) -> list[tuple[Phrase, str, int | None]]:
    """For each phrase: how it ends, and the word whose stressed syllable the ending hangs on."""
    focused_all = [_find_word(words, f["word"], f["nth"]) for f in plan["focus"]]
    out = []
    for n, phrase in enumerate(phrases):
        asked = plan["ends"][n] if plan["ends"] and n < len(plan["ends"]) else None
        kind = asked or _default_end(phrase, words)
        focused = [i for i in focused_all if i in phrase.words]
        stressed = [i for i in phrase.words if words[i].primary]
        last_stressed = stressed[-1] if stressed else (phrase.words[-1] if phrase.words else None)
        # a fall starts from the last word in focus, so what follows it stays low; a rise always hangs on the
        # last stressed word, and a focus word earlier in the phrase keeps its own accent
        nuclear = focused[-1] if focused and kind == "fall" else last_stressed
        out.append((phrase, kind, nuclear))
    return out


# ------------------------------------------------------------------ shaping the curve
def _ease(u: np.ndarray | float, power: float = 1.25):
    return np.clip(u, 0.0, 1.0) ** power


def _median(values: np.ndarray, default: float) -> float:
    values = values[np.isfinite(values)]
    return float(np.median(values)) if values.size else default


def listen(audio: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """For every point of the pitch curve: the level of the sound in dB, and the share of it above 4 kHz."""
    from scipy.signal import stft

    hop = int(RATE * F0_STEP_S)
    freqs, _, z = stft(np.asarray(audio, np.float64), fs=RATE, nperseg=2 * hop, noverlap=hop, boundary=None, padded=False)
    power = np.abs(z) ** 2
    level = 10.0 * np.log10(power.sum(axis=0) + 1e-12)
    share = power[freqs > 4000].sum(axis=0) / (power.sum(axis=0) + 1e-12)
    # column k is centred on curve point k + 1
    return np.concatenate([[level[0]], level]), np.concatenate([[share[0]], share])


@dataclass
class Shaping:
    f0_mul: np.ndarray
    f0_add: np.ndarray
    n_add: np.ndarray
    planned: dict

    @property
    def changes_nothing(self) -> bool:
        return bool(np.allclose(self.f0_mul, 1.0, atol=1e-4) and np.allclose(self.f0_add, 0.0, atol=0.05)
                    and np.allclose(self.n_add, 0.0, atol=1e-3))


def shape(base_hz: np.ndarray, energy: np.ndarray, audio: np.ndarray, phonemes: str, words: list[Word],
          phrases: list[Phrase], frames: np.ndarray, plan: dict) -> Shaping:
    """What to do to the model's pitch and energy curves to carry out `plan`, and what was planned.

    `frames` is the cumulative frame count at the start of every phoneme position (length len(phonemes) + 1);
    `audio` is the first pass, used to hear where there is a voice to move.
    """
    total = base_hz.size
    still = Shaping(np.ones(total, np.float32), np.zeros(total, np.float32), np.zeros(total, np.float32),
                    {"ref_hz": None, "phrases": [], "focus": []})
    voiced = base_hz > VOICED_HZ
    if not voiced.any():
        return still
    ref = float(np.median(base_hz[voiced]))
    base = np.full(total, np.nan)
    base[voiced] = 12.0 * np.log2(base_hz[voiced] / ref)

    def at(position: int) -> int:                # curve point where a phoneme position starts to sound
        return int(np.clip(2 * frames[min(position, len(phonemes))] - LEAD, 0, total))

    level_db, hiss = listen(audio)
    level_db, hiss = level_db[:total], hiss[:total]
    if level_db.size < total:
        level_db = np.pad(level_db, (0, total - level_db.size), constant_values=-120.0)
        hiss = np.pad(hiss, (0, total - hiss.size))
    speech = level_db > level_db.max() - SOUND_BELOW_PEAK_DB
    near_vowel = np.zeros(total, bool)           # within 40 ms of a vowel or another sound that can carry a pitch
    for i, c in enumerate(phonemes):
        if c in SONORANT:
            near_vowel[max(0, at(i) - 3):at(i + 1) + 3] = True
    voice = speech & (hiss < HISS_SHARE) & near_vowel    # a vowel or the like, a whispered one included
    # only a stretch of voice at least 50 ms long can carry a movement; the fading end of a hiss cannot
    edges = np.flatnonzero(np.diff(np.concatenate([[0], voice.astype(int), [0]])))
    for start, stop in zip(edges[::2], edges[1::2]):
        if stop - start < 4:
            voice[start:stop] = False
    loud_n = float(np.median(energy[voiced & voice])) if (voiced & voice).any() else float(np.max(energy))

    def vowel_of(word: Word) -> tuple[int, int]:
        """Curve points [a, b) where the word's stressed vowel is heard: the stretch of voice that lies on it.

        The reported phoneme frames are only right to within a few points, and a vowel after "st" or "p" starts
        late; an accent or a rise has to sit on the sound itself.
        """
        v0, v1 = at(word.stress), max(at(word.vowel[1]), at(word.stress) + 2)
        best, most, run = (v0, v1), 0, None
        for i in range(max(0, v0 - 6), min(total, v1 + 8) + 1):
            if i < min(total, v1 + 8) and voice[i]:
                run = i if run is None else run
            elif run is not None:
                overlap = min(i, v1 + 2) - max(run, v0 - 2)
                if overlap > most:
                    best, most = (run, i), overlap
                run = None
        # voice often runs on from the word before and into the next: keep to this word
        a, b = max(best[0], at(word.span[0]) - 2), min(best[1], at(word.span[1]) + 2)
        return (a, b) if b - a >= 3 else best

    level = float(plan["level"])
    target = base * float(plan["range"]) + level
    given = np.zeros(total, bool)                # points that get a pitch although the model predicted none
    n_add = np.zeros(total)
    planned: dict = {"ref_hz": round(ref, 1), "phrases": [], "focus": []}
    t = np.arange(total, dtype=float)

    focus_words = [(_find_word(words, f["word"], f["nth"]), f) for f in plan["focus"]]
    endings = endings_of(words, phrases, plan)

    # pitch accents on the focus words
    for index, f in focus_words:
        word = words[index]
        entry = {"word": word.text, "index": index, "asked_st": f["st"]}
        carries = next((kind for _, kind, nuclear in endings if nuclear == index and kind in ("rise", "continue")), None)
        if carries:
            entry.update(asked_st=None, note="starts the rise: held low, not accented" if carries == "rise"
                         else "carries the small rise that says more is coming")
            planned["focus"].append(entry)
            continue
        a, b = at(word.span[0]), at(word.span[1])
        v0, v1 = vowel_of(word)
        if not np.isfinite(target[v0:v1]).any():
            entry["note"] = "the model gives the stressed syllable no pitch"
            planned["focus"].append(entry)
            continue
        # The model's own accent keeps its shape (a peak early in the vowel, then down) and is raised as a
        # whole: by as much as it takes for the vowel to stay at the asked height for 40 ms, since a peak of a
        # single point is not heard. The lift is full over the first half of the vowel and eases off around it.
        # An accent is heard against the words around it, so its height counts from their level (the median
        # of the half second either side), not from the line's.
        near = [[max(0, min(a, v0) - 40), max(0, min(a, v0) - 2)], [min(total, max(b, v1) + 2), min(total, max(b, v1) + 40)]]
        around = _median(np.concatenate([target[i:j] for i, j in near]), level)
        goal = min(around + f["st"] + ACCENT_MARGIN_ST, plan["ceiling_st"])
        half, left, right = v0 + 0.5 * (v1 - v0), v0 - 5, v1 + 3
        weight = np.where(t < v0, (t - left) / max(1.0, v0 - left), np.where(t > half, (right - t) / max(1.0, right - half), 1.0))
        weight = 0.5 - 0.5 * np.cos(np.pi * np.clip(weight, 0.0, 1.0))

        def held(lift: float) -> float:          # the height the vowel keeps for 40 ms with this much lift
            values = np.sort((target + lift * weight)[v0:v1])
            values = values[np.isfinite(values)]
            return float(values[-min(3, values.size)])

        low_lift, need = 0.0, 0.0
        if held(0.0) < goal:
            need = 14.0
            for _ in range(24):                  # the smallest lift that gets there
                middle = (low_lift + need) / 2
                low_lift, need = (middle, need) if held(middle) < goal else (low_lift, middle)
            target = target + need * weight
        entry.update(added_st=round(need, 2), frames=[v0, v1], near=near)
        planned["focus"].append(entry)

    # phrase endings
    for n, (phrase, kind, nuclear) in enumerate(endings):
        entry = {"end": kind, "mark": phrase.mark, "on": words[nuclear].text if nuclear is not None else None, "index": nuclear}
        if kind == "keep" or nuclear is None:
            planned["phrases"].append(entry)
            continue
        word = words[nuclear]
        a = at(phrase.span[0])
        b = at(phrases[n + 1].span[0]) if n + 1 < len(phrases) else total      # up to where the next phrase starts to sound
        first, vowel_end = vowel_of(word)        # where the stressed vowel is heard
        sounding = np.flatnonzero(voice[first:b]) + first
        if sounding.size < 4:
            entry["note"] = "no voice after the stressed syllable to move"
            planned["phrases"].append(entry)
            continue
        last = int(sounding[-1])

        def lift(first: int, low: float, high: float, low_until: float, energy_below: float) -> int:
            """Set the pitch from `first` to `last` to a curve that stays at `low`, then climbs to `high`.

            Points the model left without a pitch are given one, and a whispered ending is brought up to within
            `energy_below` of the line's spoken level, or it could not carry the movement. Returns how many
            points were given a pitch.
            """
            nonlocal target, given, n_add
            top_from = last - 3                  # the top is reached 40 ms early: the last points fade into what follows
            low_until = min(max(low_until, first + 1), top_from - 3)
            curve = low + (high - low) * _ease((t - low_until) / max(1.0, top_from - low_until))
            lead_in = max(a, first - 5)          # glide into the low over the points before
            blend = np.clip((t - lead_in) / max(1.0, first - lead_in), 0.0, 1.0)
            glide = (t >= lead_in) & (t < first) & np.isfinite(target)
            target = np.where(glide, target * (1 - blend) + curve * blend, target)
            tail = (t >= first) & (t <= last)
            carry = tail & (voiced | voice)      # every point of the tail that has, or can have, a pitch
            target = np.where(carry, curve, target)
            given |= carry & ~voiced
            target = np.where((t > last) & (t < b) & voiced, high, target)
            n_add = np.where(tail & voice, np.maximum(n_add, loud_n - energy_below - energy), n_add)
            return int((carry & ~voiced).sum())

        if kind == "rise":
            now = _median(target[max(a, first - 2):first + 4], level)
            # low on the stressed syllable, but not so low that the voice creaks and the start of the rise is lost
            low = max(min(now, level + plan["rise_low_st"]), level + plan["rise_floor_st"])
            high = max(low + plan["rise_st"], level + plan["rise_top_min_st"])
            low_until = vowel_end if last - vowel_end >= 8 else first + 0.3 * (last - first)
            count = lift(first, low, high, low_until, plan["rise_energy"])
            entry.update(asked_st=round(high - low, 2), low_st=round(low, 2), high_st=round(high, 2), given_pitch=count)
        elif kind == "continue":                 # more is coming: the last 150 ms of voice end a little up, not down
            # an accented last word carries the rise over its whole vowel, if the vowel is near the end
            accented = any(i == nuclear for i, _ in focus_words) and last - first <= 28
            first = first if accented else max(a, last - 12)
            now = _median(target[max(a, first - 6):first + 1], level)
            low = float(np.clip(now, level - 3.0, level + 2.0))
            count = lift(first, low, low + plan["continue_st"], first + 2, plan["continue_energy"])
            entry.update(asked_st=plan["continue_st"], low_st=round(low, 2), high_st=round(low + plan["continue_st"], 2), given_pitch=count)
        else:                                    # fall
            heard = sounding[voiced[sounding]]
            if heard.size < 3:
                entry["note"] = "the model lets the ending trail off without a pitch"
                planned["phrases"].append(entry)
                continue
            last = int(heard[-1])
            if any(i == nuclear for i, _ in focus_words):          # accented: fall from the peak, not through it
                first = min(int(first + 0.6 * (vowel_end - first)) + 1, last - 3)
            now = _median(target[max(first, last - 3):last + 1], level)
            add = min(0.0, level - plan["fall_st"] - now)
            ramp = add * _ease((t - first) / max(1.0, last - first), 1.3)
            entry.update(asked_st=-plan["fall_st"], added_st=round(add, 2))
            target = np.where((t >= first) & (t < b) & np.isfinite(target), target + ramp, target)
        entry["frames"] = [int(first), int(last)]
        planned["phrases"].append(entry)

    # the plan may not push the voice beyond its limits, but where the model itself goes beyond them (a creaky
    # ending far below the floor) the model's own value stands: with nothing asked, nothing is changed
    lowest = np.where(voiced, np.fmin(plan["floor_st"], base), plan["floor_st"])       # points given a pitch have no value of the model's
    highest = np.where(voiced, np.fmax(plan["ceiling_st"], base), plan["ceiling_st"])
    target = np.clip(target, lowest, highest)
    delta = np.where(voiced, target - base, np.nan)
    known = np.flatnonzero(np.isfinite(delta))
    delta = np.interp(np.arange(total), known, delta[known])        # carry the change across unvoiced stretches
    delta = np.convolve(np.pad(delta, 1, mode="edge"), [0.25, 0.5, 0.25], mode="valid")
    f0_mul = np.where(given, 0.0, 2.0 ** (delta / 12.0))
    f0_add = np.where(given, ref * 2.0 ** (np.nan_to_num(target) / 12.0), 0.0)
    n_add = np.convolve(np.pad(np.maximum(n_add, 0.0), 2, mode="edge"), np.ones(5) / 5.0, mode="valid")
    return Shaping(f0_mul.astype(np.float32), f0_add.astype(np.float32), n_add.astype(np.float32), planned)


# ------------------------------------------------------------------ speaking
@dataclass
class Take:
    text: str
    phonemes: str
    audio: np.ndarray              # as the model gives it: silence at both ends still on
    words: list[Word]
    phrases: list[Phrase]
    frames: np.ndarray             # cumulative frame count at each phoneme position
    base_hz: np.ndarray            # the model's own pitch curve
    set_hz: np.ndarray             # the curve the audio was rendered from
    plan: dict
    planned: dict

    def time_of(self, position: int) -> float:
        """Seconds into the clip at which a phoneme position starts to sound."""
        return max(0.0, float(self.frames[min(position, len(self.phonemes))]) * FRAME_S - LEAD * F0_STEP_S)


def speak(text: str, *, voice: str, lang: str, speed: float, plan: dict, model_dir: str | Path) -> Take:
    session, kokoro = _load(Path(model_dir))
    phonemes = kokoro.tokenizer.phonemize(text, lang)
    tokens = kokoro.tokenizer.tokenize(phonemes)
    if len(tokens) != len(phonemes):
        raise ValueError(f"phonemes outside the model's vocabulary in {phonemes!r}")
    words, phrases = lay_out(text, phonemes, lambda w: kokoro.tokenizer.phonemize(w, lang))
    style = np.asarray(kokoro.voices[voice][min(len(tokens), len(kokoro.voices[voice])) - 1], np.float32).reshape(1, 256)

    lengths = np.ones(len(tokens) + 2, np.float32)       # one per token, the pad at each end included
    for f in plan["focus"]:
        if f["stretch"] != 1.0:
            w = words[_find_word(words, f["word"], f["nth"])]
            lengths[1 + w.vowel[0]:1 + w.vowel[1]] *= f["stretch"]
    if plan["rise_stretch"] != 1.0:                      # a question's rise gets a little more room
        for phrase, kind, nuclear in endings_of(words, phrases, plan):
            if kind == "rise" and nuclear is not None:
                for i in range(words[nuclear].vowel[0], phrase.span[1]):
                    if phonemes[i] in SONORANT and phonemes[i] not in STRESS:
                        lengths[1 + i] *= plan["rise_stretch"]
    one, zero = np.ones((1, 1), np.float32), np.zeros((1, 1), np.float32)
    feed = {"tokens": np.array([[0, *tokens, 0]], np.int64), "style": style, "speed": np.array([speed], np.float32),
            "n_mul": one, "dur_mul": lengths.reshape(1, -1)}

    audio, base_hz, energy, duration = session.run(None, {**feed, "f0_mul": one, "f0_add": zero, "n_add": zero})
    audio = np.asarray(audio, np.float32).ravel()
    frames = np.cumsum(np.asarray(duration).ravel())[:len(phonemes) + 1]   # entry i: frames before phoneme i (entry 0 is the lead-in pad)
    base_hz = np.asarray(base_hz, np.float64).ravel()
    shaping = shape(base_hz, np.asarray(energy, np.float64).ravel(), audio, phonemes, words, phrases, frames, plan)
    set_hz = base_hz
    if not shaping.changes_nothing:
        row = lambda values: values.reshape(1, -1)
        audio = np.asarray(session.run(["audio"], {**feed, "f0_mul": row(shaping.f0_mul), "f0_add": row(shaping.f0_add),
                                                   "n_add": row(shaping.n_add)})[0], np.float32).ravel()
        set_hz = base_hz * shaping.f0_mul + shaping.f0_add
    return Take(text, phonemes, audio, words, phrases, frames, base_hz, set_hz, plan, shaping.planned)


# ------------------------------------------------------------------ measuring
def track(audio: np.ndarray, rate: int, ref_hz: float, step: float = 0.005) -> tuple[np.ndarray, np.ndarray]:
    """(times, Hz) of the voiced frames of a clip, from the audio (Praat's autocorrelation tracker).

    The search is kept to the band a plan can ask for (10 semitones under the line's median to 13 over), which
    removes most octave errors on creaky syllables.
    """
    import parselmouth

    sound = parselmouth.Sound(np.asarray(audio, np.float64), sampling_frequency=rate)
    pitch = sound.to_pitch_ac(time_step=step, pitch_floor=ref_hz * 0.56, pitch_ceiling=ref_hz * 2.12,
                              voicing_threshold=0.3, silence_threshold=0.02, octave_jump_cost=0.6)
    hz, times = pitch.selected_array["frequency"], pitch.xs()
    keep = hz > 0
    return times[keep], hz[keep]


def follow(take: Take) -> tuple[np.ndarray, np.ndarray]:
    """Per point of the pitch curve: the pitch heard in the audio (nan where none), and whether it is the pitch set.

    A point follows when the audio is within FOLLOW_ST semitones of the curve the audio was rendered from. A creaky
    syllable shows up as no pitch, or as a pitch an octave off; neither counts as following.
    """
    times, hz = track(take.audio, RATE, take.planned["ref_hz"])
    total = take.set_hz.size
    heard = np.full(total, np.nan)
    index = np.rint(times / F0_STEP_S).astype(int)
    for i in np.unique(index[(index >= 0) & (index < total)]):
        heard[i] = float(np.median(hz[index == i]))
    with np.errstate(divide="ignore", invalid="ignore"):
        off = np.abs(12.0 * np.log2(heard / np.where(take.set_hz > VOICED_HZ, take.set_hz, np.nan)))
    return heard, off <= FOLLOW_ST


def _st(hz: float, ref: float) -> float:
    return 12.0 * math.log2(hz / ref)


def measure(take: Take) -> dict:
    """What the audio of a take does, phrase by phrase and focus word by focus word, next to what was asked."""
    planned = take.planned
    if not planned.get("ref_hz"):
        return {"ok": True, "note": "no voiced speech"}
    heard, follows = follow(take)
    good = heard[follows]
    if good.size < 5:
        return {"ok": False, "note": "the pitch tracker found no voice that follows the curve"}
    line = planned["ref_hz"] * 2.0 ** (float(take.plan["level"]) / 12.0)     # the level the plan counts from
    low, high = np.percentile(good, [5, 95])
    wanted = take.set_hz > VOICED_HZ
    out = {"median_hz": round(float(np.median(good)), 1), "range_st": round(_st(high, low), 2),
           "model_range_st": round(_st(*np.percentile(take.base_hz[take.base_hz > VOICED_HZ], [95, 5])), 2),
           "followed": round(float(follows[wanted].mean()), 2),          # share of the pitched points heard at the pitch set
           "phrases": [], "focus": [], "ok": True}

    def pitches(a: int, b: int) -> np.ndarray:
        a, b = max(0, a), min(heard.size, b)
        return heard[a:b][follows[a:b]]

    def glide(first: int, last: int) -> tuple[float, float]:
        """The last unbroken stretch of clean voice in [first, last]: its length in ms and how far it climbs (st)."""
        idx = np.flatnonzero(follows[max(0, first - 1):last + 2]) + max(0, first - 1)
        if idx.size < 3:
            return 0.0, 0.0
        start = idx.size - 1
        while start > 0 and idx[start] - idx[start - 1] <= 2:        # a single missing point does not break it
            start -= 1
        run = heard[idx[start:]]
        return float((idx[-1] - idx[start] + 1) * F0_STEP_S * 1000.0), _st(float(np.median(run[-3:])), float(run.min()))

    for entry in planned["phrases"]:
        got = {k: entry.get(k) for k in ("end", "mark", "on", "asked_st")}
        if "frames" not in entry:
            if entry["end"] == "keep":
                out["phrases"].append({**got, "note": "left as the model spoke it"})
            else:                                 # asked for, and there was nothing to carry it
                out["phrases"].append({**got, "ok": False, "note": entry.get("note", "could not be carried out")})
                out["ok"] = False
            continue
        first, last = entry["frames"]
        tail, end = pitches(first - 1, last + 2), pitches(max(first, last - 6), last + 2)       # the end: the last 90 ms
        if entry["end"] == "fall":
            set_end = take.set_hz[max(first, last - 3):last + 1]
            got["set_st"] = round(_st(float(np.median(set_end[set_end > VOICED_HZ])), line), 2) if (set_end > VOICED_HZ).any() else None
            end = pitches(max(first, last - 3), last + 2)     # a fall is heard only if the voice holds to the very end
            if end.size:
                got["got_st"] = round(_st(float(np.median(end)), line), 2)
                got["ok"] = got["got_st"] <= entry["asked_st"] + TOLERANCE["fall_st"]
            else:
                # The model ends most statements in a creak that no tracker follows, shaped or not. The curve was
                # set low enough or it was not; what is heard there cannot be put in semitones.
                got["ok"] = got["set_st"] is not None and got["set_st"] <= entry["asked_st"] + TOLERANCE["fall_st"]
                got["note"] = "ends in a creak, as the model does by itself: set, not heard"
        elif tail.size < 4 or end.size < 2:
            got.update(ok=False, note="the ending is not voiced clearly enough to hear the movement")
        elif entry["end"] == "rise":
            got["got_st"] = round(_st(float(np.median(end)), float(np.percentile(tail, 10))), 2)
            got["end_level_st"] = round(_st(float(np.median(end)), line), 2)
            got["voiced"] = round(float(follows[first:last + 1].mean()), 2)      # share of the rise that is cleanly voiced
            length, climb = glide(first, last)
            got["glide_ms"], got["glide_st"] = round(length), round(climb, 2)
            got["ok"] = got["got_st"] >= max(HEARD_RISE_ST, TOLERANCE["rise"] * entry["asked_st"])
            if got["ok"] and (length < MIN_GLIDE_MS or climb < HEARD_RISE_ST):
                got.update(ok=False, note=f"the rise is a step, not a glide: its last unbroken stretch of clean voice is {length:.0f} ms "
                                          f"and climbs {climb:.1f} st (wanted: {MIN_GLIDE_MS} ms and {HEARD_RISE_ST} st)")
            elif got["ok"] and got["voiced"] < CLEAN_RISE_SHARE:
                got.update(ok=False, note=f"the rise is creaky: only {got['voiced']:.0%} of it is heard at the pitch set")
        else:                                     # continue: the end against the start of the lifted stretch
            got["got_st"] = round(_st(float(np.median(pitches(last - 3, last + 2)) if pitches(last - 3, last + 2).size else np.median(end)),
                                      float(np.percentile(tail, 10))), 2)
            got["end_level_st"] = round(_st(float(np.median(end)), line), 2)
            got["ok"] = got["got_st"] >= TOLERANCE["continue"] * entry["asked_st"]
        out["ok"] = out["ok"] and got["ok"]
        out["phrases"].append(got)

    for entry in planned["focus"]:
        got = {"word": entry["word"], "asked_st": entry.get("asked_st")}
        if entry.get("asked_st") is None:
            out["focus"].append({**got, "note": entry.get("note", "")})
            continue
        peak = pitches(*entry["frames"]) if "frames" in entry else np.array([])
        if peak.size < 2:
            out["focus"].append({**got, "ok": False, "note": entry.get("note", "not voiced clearly enough to measure")})
            out["ok"] = False
            continue
        around = np.concatenate([pitches(i, j) for i, j in entry["near"]])
        got["got_st"] = round(_st(float(np.sort(peak)[-min(3, peak.size)]), float(np.median(around)) if around.size else line), 2)
        got["ok"] = got["got_st"] >= entry["asked_st"] - TOLERANCE["focus_st"]      # the height held for 40 ms, over the words around
        out["ok"] = out["ok"] and got["ok"]
        out["focus"].append(got)
    return out


def curves(take: Take, offset_s: float = 0.0) -> dict:
    """The curves of a take for the sheet: the model's own, the planned one, and the one heard in the audio."""
    t = np.arange(take.base_hz.size) * F0_STEP_S - offset_s
    if take.planned.get("ref_hz"):
        heard, follows = follow(take)
    else:                                        # a line with no voiced sound has no pitch to draw
        heard, follows = np.full(take.base_hz.size, np.nan), np.zeros(take.base_hz.size, bool)
    keep = lambda values: [round(float(v), 1) if np.isfinite(v) and v > VOICED_HZ else None for v in values]
    return {"ref_hz": take.planned.get("ref_hz") or 200.0, "t": [round(float(v), 4) for v in t],
            "model_hz": keep(take.base_hz), "set_hz": keep(take.set_hz), "heard_hz": keep(heard),
            "follows": [bool(v) for v in follows]}


def overall(curves_by_id: dict) -> dict:
    """Liveliness of a whole narration: how much the pitch moves, in semitones about the narration's median.

    Counted on the points heard at the pitch set. Reading (from the research notes of the Colosseum film): a
    spread (standard deviation) of 2 to 3 st is flat, about 4 st lively, 4.8 st the top of what was measured
    on people.
    """
    heard = np.array([hz for c in curves_by_id.values() for hz, ok in zip(c["heard_hz"], c["follows"]) if ok and hz], float)
    if heard.size < 10:
        return {}
    st = 12.0 * np.log2(heard / np.median(heard))
    p10, p90 = np.percentile(st, [10, 90])
    return {"median_hz": round(float(np.median(heard)), 1), "sd_st": round(float(st.std()), 2),
            "p10_p90_st": round(float(p90 - p10), 2), "top_st": round(float(np.percentile(st, 99)), 2)}


def word_times(take: Take, offset_s: float = 0.0) -> list[dict]:
    """When each word starts and ends (its punctuation, which the model turns into silence, not counted)."""
    def last_sound(w: Word) -> int:
        end = w.span[1]
        while end - 1 > w.span[0] and take.phonemes[end - 1] in MAJOR + MINOR:
            end -= 1
        return end

    return [{"text": w.text, "start_s": round(take.time_of(w.span[0]) - offset_s, 3),
             "end_s": round(take.time_of(last_sound(w)) - offset_s, 3),
             "stress_s": round(take.time_of(w.stress) - offset_s, 3)} for w in take.words]


def problems(narration: dict) -> list[str]:
    """Pitch movements that were asked for and did not come out, for `film check`."""
    out = []
    for s in narration["sentences"]:
        p = s.get("pitch")
        if not p:
            continue
        if p.get("note") and not p.get("ok", True):
            out.append(f"pitch {s['id']}: {p['note']}")
        for phrase in p.get("phrases", []):
            if phrase.get("ok") is False:
                heard = f"measured {phrase['got_st']} st, " if phrase.get("got_st") is not None else ""
                out.append(f"pitch {s['id']}: the {phrase['end']} on {phrase.get('on')!r}: {heard}asked {phrase.get('asked_st')} st"
                           + (f" ({phrase['note']})" if phrase.get("note") else ""))
        for f in p.get("focus", []):
            if f.get("ok") is False:
                out.append(f"pitch {s['id']}: the accent on {f['word']!r} measured {f.get('got_st')} st over the words around it, "
                           f"asked {f.get('asked_st')} st" + (f" ({f['note']})" if f.get("note") else ""))
    return out


def summary(sentence: dict) -> str:
    """One line for the terminal: what the pitch of a sentence does."""
    p = sentence.get("pitch")
    if not p or "range_st" not in p:
        return ""
    parts = [f"range {p['range_st']:.1f} st (model alone {p['model_range_st']:.1f})"]
    for phrase in p["phrases"]:
        if phrase["end"] == "keep":
            continue
        mark = "ok" if phrase.get("ok") else "SHORT"
        name = f"{phrase['end']} on \"{phrase['on']}\""
        if phrase.get("got_st") is None:
            parts.append(f"{name} set {phrase['set_st']:+.1f} st, ends in a creak (not heard)" if phrase.get("set_st") is not None
                         else f"{name} SHORT")
        elif phrase["end"] == "rise":
            parts.append(f"{name} {phrase['got_st']:+.1f} st, a {phrase['glide_ms']} ms glide {mark}")
        else:
            parts.append(f"{name} {phrase['got_st']:+.1f} st {mark}")
    for f in p["focus"]:
        if f.get("got_st") is not None:
            parts.append(f"accent \"{f['word']}\" {f['got_st']:+.1f} st {'ok' if f.get('ok') else 'SHORT'}")
        elif f.get("ok") is False:
            parts.append(f"accent \"{f['word']}\" SHORT")
    return "; ".join(parts)


# ------------------------------------------------------------------ the sheet
def sheet(narration: dict, curves_by_id: dict, out_png: str | Path, title: str = "") -> Path:
    """Draw every line's pitch: the model's own curve (grey), the planned curve (accent), the audio as measured (dark dots)."""
    from PIL import Image, ImageDraw, ImageFont

    root = Path(__file__).resolve().parents[1]
    tokens = json.loads((root / "engine" / "tokens.json").read_text(encoding="utf-8"))
    accent = tokens["accent"]["options"][tokens["accent"]["current"]]
    font = lambda size, weight="Medium": ImageFont.truetype(str(root / "assets" / "fonts" / f"Inter-{weight}.otf"), size)
    mono = ImageFont.truetype(str(root / "assets" / "fonts" / "JetBrainsMono-Regular.ttf"), 20)
    rows = [s for s in narration["sentences"] if s["id"] in curves_by_id]
    width, row_h, top, left, right = 1800, 300, 90, 90, 40
    image = Image.new("RGB", (width, top + row_h * len(rows) + 30), (247, 248, 250))
    draw = ImageDraw.Draw(image)
    draw.text((left, 26), title or "Pitch of the narration", font=font(34, "SemiBold"), fill=(20, 22, 26))
    draw.text((left + 760, 38), "grey: the model alone    colour: as set    dots: heard in the audio (hollow: off the set pitch)    semitones about each line's median",
              font=font(18, "Regular"), fill=(90, 96, 104))
    longest = max(s["end_s"] - s["start_s"] for s in rows)
    scale_x = (width - left - right) / (longest + 0.2)
    lo, hi = -10.0, 12.0
    for n, s in enumerate(rows):
        c = curves_by_id[s["id"]]
        ref = c["ref_hz"]
        y0 = top + n * row_h
        plot_top, plot_bottom = y0 + 46, y0 + row_h - 62
        y = lambda st: plot_bottom - (st - lo) / (hi - lo) * (plot_bottom - plot_top)
        x = lambda t: left + t * scale_x
        draw.text((left, y0 + 8), f"{s['id']}  {s['text']}", font=font(24, "SemiBold"), fill=(20, 22, 26))
        note = summary(s)
        draw.text((left, y0 + row_h - 34), note, font=font(18, "Regular"), fill=(170, 40, 20) if "SHORT" in note else (60, 66, 74))
        for st in (-8, -4, 0, 4, 8, 12):
            draw.line([(left, y(st)), (width - right, y(st))], fill=(205, 209, 214) if st else (150, 156, 164), width=1)
            draw.text((left - 46, y(st) - 11), f"{st:+d}", font=mono, fill=(120, 126, 134))
        for w in s.get("words", []):
            wx = max(left, x(w["start_s"] - s["start_s"]))
            draw.line([(wx, plot_top), (wx, plot_bottom)], fill=(226, 229, 233), width=1)
            draw.text((wx + 3, plot_bottom + 4), w["text"], font=font(17, "Regular"), fill=(60, 66, 74))
        for key, colour, thick in (("model_hz", (168, 174, 182), 3), ("set_hz", accent, 4)):
            run = []
            for t, hz in zip(c["t"], c[key]):
                if hz is None or t < -0.05:
                    if len(run) > 1:
                        draw.line(run, fill=colour, width=thick, joint="curve")
                    run = []
                else:
                    run.append((x(t), y(max(lo, min(hi, 12 * math.log2(hz / ref))))))
            if len(run) > 1:
                draw.line(run, fill=colour, width=thick, joint="curve")
        for t, hz, ok in zip(c["t"], c["heard_hz"], c["follows"]):
            if hz and t >= -0.05:
                px, py = x(t), y(max(lo, min(hi, 12 * math.log2(hz / ref))))
                draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=(20, 22, 26) if ok else None, outline=(20, 22, 26))
    out = Path(out_png)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    image.save(out)
    return out
