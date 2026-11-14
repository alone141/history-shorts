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
  stonehenge/                the site: sources.json, refs.json, survey, plan digitising, model
    stones.json              the measured stone table the model is built from (kept in the repository)
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

The two Stonehenge films are rendered (vermilion accent) after two independent
refutation passes; see each film's FACTS.md. The Great Pyramid film has its script,
model, stills and documents, checked claim by claim (its FACTS.md has the record);
its final render follows the last review. Nothing is posted. Account name: Measured
Past. Not done: a code review of the whole pipeline (the changes made for the Great
Pyramid film were reviewed), and the TikTok and Instagram labelling rules.

## This PC

Found while building here on 12 November 2026:

- HTTPS is inspected by the organisation; downloads verify against the Windows certificate store (`engine/fetch.py` uses `truststore`).
- Chrome cannot be automated here (a data-loss-prevention agent closes its automation port), so the phase model is drawn with OpenGL in Python instead of three.js in headless Chrome.
- On drive E:, overwriting a file in place does not truncate it. Every writer goes through `engine/files.py`. Do not copy over existing files by hand; delete first.
- TikTok and Instagram are blocked on this network.
- Git's own certificate store fails behind the inspection; this checkout is set to use the Windows store (`git config http.sslBackend schannel`, local to this repository).
