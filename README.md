# Evidence films

Short vertical films (1080 x 1920, 30 fps, about 30 seconds) about archaeology
and history. Each film answers one question, shown not told, built only from
evidence. The design rules are in [docs/design-guide.md](docs/design-guide.md).

## Layout

```
engine/            everything shared by all films
  film.py            one command per film (voice, check, stills, accents, sound, render)
  tokens.json        colours, type, safe areas, sound levels: the single source of design values
  timeline.py        times as expressions on the narration clock ("s3", "s4.cue:lintels", "s5+0.4")
  voice.py           narration (Kokoro) and the clock it defines
  pitch.py           the narrator's intonation: planned per line, rendered through the model, measured from the audio
  sound.py           voice + room tone + code-made cues, with a levels report
  encode.py          H.264 MP4 (PyAV)
  files.py           safe file writing (see "This PC" below)
  fetch.py           downloads the open data a topic lists
  phase/             look 1, the phase model: OpenGL picture (render.py, geometry.py) and text layer (overlay.py)
  table.py           look 2, the archive light table (Pillow)
topics/            one data module per film, plus the site's sources
  stonehenge_standing.py     "How much of Stonehenge is still standing?"         (phase model)
  stonehenge_1740.py         "What did Stonehenge look like in 1740?"            (light table)
  great_pyramid_original.py  "What did the Great Pyramid originally look like?"  (phase model)
  sphinx_buried.py           "The Sphinx was buried to its neck for about 1,500 years"  (light table)
  stonehenge/                the site: sources.json, refs.json, survey, plan digitising, model
    stones.json              the measured stone table the model is built from (kept in the repository)
  sphinx/                    the scans' sources.json and research.md (claims, quotes, what not to say)
  giza/                      the site: sources.json, reading of Petrie's plate of course levels, model
    courses.json             the level of every course of the Great Pyramid (kept in the repository)
films/             one folder per film: MP4, README, FACTS, CREDITS, stills, contact sheet
docs/              design guide
assets/fonts/      Inter, Inter Display, JetBrains Mono (SIL Open Font License, licence files included)
review/            stills, accent options and sound drafts awaiting approval
prototype/         the approved test films this work started from (reference only; its paths are stale)
data/, models/, build/, .venv/   downloads and working files, not in version control
```

## A new topic

A topic is **one data module plus its sources**.

1. `topics/<site>/sources.json`: the open data to download (name, URL, destination, licence note).
2. `topics/<film>.py`: a `FILM` dictionary with the look, the hook, the script, when each picture and sound event happens on the narration clock, and the stills to keep. Copy one of the two Stonehenge modules.
3. For the phase model, a function that returns the model: prisms that survive (`matter`) and prisms that are inferred (`light`). See `topics/stonehenge/model.py`.
4. `films/<id>/FACTS.md` and `CREDITS.md`.

The narrator's pitch is part of the script. A film with `"prosody": {}` has every line's
intonation planned, rendered and measured (see "The narrator's pitch" below); a line says what
it wants under `"pitch"`, for example `{"focus": ["holes"]}` or `{"ends": ["continue"]}`.

Then:

```
python -m engine.fetch topics/<site>/sources.json
python -m engine.film <film> voice
python -m engine.film <film> check
python -m engine.film <film> stills
python -m engine.film <film> sound
python -m engine.film <film> render
```

Run from the repository root with the project environment (`.venv`).

## The narrator's pitch

Kokoro on its own ends most questions flat: on eight yes/no questions only one rose, and it often
gives the last word of a phrase no pitch at all and lets it trail off. `engine/pitch.py` therefore
sets the pitch itself. It writes a copy of the voice model (`models/kokoro/kokoro-v1.0-pitch.onnx`,
built on first use, identical to the stock model when nothing is set) whose pitch curve, energy and
phoneme lengths can be given, and for each line it:

- widens the model's own movement about the line's median (`range`),
- puts a pitch accent on the line's `focus` words, counted from the words around them,
- ends each phrase by its punctuation: a yes/no question rises from a low on its last stressed
  syllable, a statement or a question that opens on what/why/how falls, a comma or a colon keeps the model's
  own ending;
  `"ends"` overrides this (`"rise"`, `"fall"`, `"continue"`, `"keep"`),
- then measures the audio with Praat's pitch tracker and reports every asked movement next to what
  came out.

What the report can and cannot say. A rise passes only if it is a glide: at least 4 semitones over at
least 100 ms of unbroken clean voice (a rise that is only a short step after a gap fails). An accent
passes if the vowel holds its height for 40 ms. A fall is different: the model ends most statements
in a creak that no pitch tracker follows, with or without this engine, so most falls are reported as
"set, ends in a creak (not heard)": the curve was set low, and nothing more can be measured. None of
this says how natural the voice sounds; that takes ears.

Writing for it (from 70 test lines and an independent re-measurement, November 2026):

- A question: 12 words at most, one clause, and a last word the voice keeps voiced to the end:
  "piers", "man-made", "damage", "iron", "Colosseum". On some last words the model trails off and
  the rise breaks ("... most of the Colosseum's holes?" did); the check says so, and the cure is to
  reword, not to raise the settings.
- An accent: one per clause, on a word with a long voiced vowel, and not the last word of a falling
  line if its vowel is short ("picks", "gap"). Two accents on neighbouring words flatten the second.
- Figures need `"say"` in words. A line with digits is spoken, but its word times are approximate.
- The settings were tested with `af_heart` at 1.15. With the older films' `bm_fable` only two of five
  test questions got a real glide, so those films keep their narration until that voice is tuned.
- The limits in `engine/pitch.py` (`LIMITS`) are where the tests stopped: a rise over 9 semitones or
  a range over 1.6 makes the voice rough.

`python -m engine.film <film> voice` prints that report and the spread of pitch over the whole
narration, and writes `build/<film>/voice/pitch.png`, a drawing of every line's curve (the model
alone, the curve set, the pitch heard). `check` and `render` stop on a movement that did not come
out. The settings and their meaning are in `engine/tokens.json` under `"prosody"`. A narration made
this way also knows when every word is spoken, so a picture event can be tied to a word:
`"s2.word:dots"` (and a `"cues"` entry is timed from the same word times).

## Setting up on another machine

Python 3.10 or later, and a graphics card with OpenGL 3.3 for the phase model.
No browser, Node or FFmpeg program is needed. Run everything from the repository root.

```
git clone https://github.com/alone141/history-shorts.git
cd history-shorts
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # on macOS or Linux: .venv/bin/python
.venv/Scripts/python -m engine.fetch engine/sources_common.json --check   # optional: are the sources still there?
.venv/Scripts/python -m engine.fetch engine/sources_common.json           # narrator model, about 350 MB
.venv/Scripts/python -m engine.fetch topics/stonehenge/sources.json stukeley-1740   # page scans for the 1740 film, 121 MB
.venv/Scripts/python -m engine.selftest_av                                  # voice, sound and MP4 checks, about 15 s
```

That is enough to make all three films: the Stonehenge phase model reads the stone
table in `topics/stonehenge/stones.json`, the light table reads the scans straight
from the downloaded archive, and the Great Pyramid model reads the course table in
`topics/giza/courses.json`. The fonts are in `assets/fonts`.

To rebuild the stone table from the raw open data (about 450 MB more):

```
.venv/Scripts/python -m engine.fetch topics/stonehenge/sources.json
.venv/Scripts/python -m engine.fetch topics/stonehenge/refs.json
.venv/Scripts/python -m topics.stonehenge.prepare_survey
.venv/Scripts/python -m topics.stonehenge.digitise_plan
.venv/Scripts/python -m topics.stonehenge.build_stones
```

To rebuild the Great Pyramid's course table from Petrie's plate (2.5 MB):

```
.venv/Scripts/python -m engine.fetch topics/giza/sources.json
.venv/Scripts/python -m topics.giza.plate_tiles       # cuts the plate into reading tiles
.venv/Scripts/python -m topics.giza.build_courses     # readings -> courses.json, checked against the plate's own drawing
```

The readings themselves (`topics/giza/plate_readings.json`) were made by eye from the tiles, twice.

## Without a graphics card (Linux server or cloud container)

The phase model also renders on Mesa's software OpenGL under a virtual display:
prefix the `engine.film` commands with `xvfb-run -a`. On four cores a phase
film takes 13 to 15 minutes and the light table film about 9.

## Where things stand

All three films are rendered (vermilion accent). The two Stonehenge films went through
two independent refutation passes. The Great Pyramid film went through a claim-by-claim
fact check and a review of a candidate render (facts, picture, code); its FACTS.md has
the record of what was changed and why. The Sphinx film (15 November 2026) is rendered: its script went through one
independent hostile fact check, whose wording changes were applied before the render. An
earlier cut built on the Napoleon legend was dropped as too familiar; its research stays in
topics/sphinx/research.md. Light-table objects can now enter the table one after another
("enter" in the object spec), so a film moves from its first frame. Nothing is posted. Account name: Measured Past.
Not done: nobody has yet watched the films in motion or listened to the mixes (the
checks so far are on decoded frames, measured sound levels and timing); a code review
of the whole pipeline (the changes made for the Great Pyramid film were reviewed); and
the TikTok and Instagram labelling rules.

## This PC

Found while building here on 12 November 2026:

- HTTPS is inspected by the organisation; downloads verify against the Windows certificate store (`engine/fetch.py` uses `truststore`).
- Chrome cannot be automated here (a data-loss-prevention agent closes its automation port), so the phase model is drawn with OpenGL in Python instead of three.js in headless Chrome.
- On drive E:, overwriting a file in place does not truncate it. Every writer goes through `engine/files.py`. Do not copy over existing files by hand; delete first.
- TikTok and Instagram are blocked on this network.
- Git's own certificate store fails behind the inspection; this checkout is set to use the Windows store (`git config http.sslBackend schannel`, local to this repository).
