# Design guide

Short films about archaeology and history for TikTok, Instagram Reels and
YouTube Shorts. This guide is the reference for anyone making a film for the
account. Values quoted here live in `engine/tokens.json`; change them there,
not in code.

Status: draft for the owner's review. Open choices are marked **OPEN**.

## 1. Positioning

Each film answers **one question** about a site or object, **shown not told**,
built **only from evidence**.

- What survives or was measured is shown as such.
- What is inferred is visibly marked as inferred.
- Every number has a source, on screen or one tap away.

That honesty is the product. Many accounts show seamless reconstructions; this
one shows the join between what is there and what is supposed.

A film is ready when a hostile reader of its `FACTS.md` finds nothing to correct.

## 2. The evidence code

One rule, used in both looks:

| On screen | Means |
|---|---|
| **White matter** (phase model) or **the scan itself** (light table) | Evidence. It survives today, or it was measured. |
| **Projected light** (phase model) | Inferred. Where something stood, or how large it was, worked out and not observed. |
| **The accent colour** (both looks) | Ours, not evidence. A mark, a projection, an underline. |

Consequences:

- White is never used for something that is not there today. A fallen stone is white, lying down.
- Light is never used for something that survives.
- The accent is never decoration. If it is on screen it is saying "we added this".
- The scan is never redrawn, retouched or generated. One uniform levels curve is allowed and is declared in `FACTS.md`.
- The words say it once, near the end: "White is what survives today. Light is what we infer." / "The scans are real. The mark and the lens are ours."
- Things made by modern hands that stand today (a re-erected stone) stay white, with one stated, sourced line. No third visual state.

When evidence runs out, show less. Missing things with no agreed number or position are left dark and listed in `FACTS.md` under "Modelling choices".

## 3. The two looks

### 3.1 Phase model (the signature look)

A white model of what survives today, on a plate, on a plinth, in a dark room. A projector paints what is inferred as light.

- **Model.** Real outlines from a published plan, extruded to measured heights, with a small bevel. Matte white. Standing and fallen stones alike.
- **Plate.** Mid grey, darker than the model so white reads as white. A fine rim line, an engraved scale bar and a north mark are the only things on it. The scale bar is true.
- **Plinth and room.** Dark satin plinth with a lighter lip; near-black room. The plinth must read as an object: keep its lip lit.
- **House lights.** One warm key light with real shadows, a cool rim light, a soft fill from the camera side. Lights are fixed in the room; the camera moves.
- **Projected light.** Footprints on the plate first, then volumes rising from them. Each volume has soft faces and a crisp edge about 3 px wide, so it reads at phone size. Light is additive: it never darkens anything and is hidden behind matter.
- **Depth of field and glow.** Slight depth of field about the centre of the model; glow only on the projected light.
- **Readout.** One large figure, lower left, that counts with the picture, and a two-row legend (white, light).

### 3.2 Archive light table (the workhorse)

Real public-domain scans on a cool backlit table. A loupe at a true, stated magnification. One accent mark. A caption plate.

- **Table.** Cool white glow with gentle fall-off, fine grain, small registration ticks, a dark frame. No sepia, no ageing overlays.
- **Sheets.** Whole pages or plates at true proportions, with soft contact shadows and a slight tilt. Two or three at most.
- **Loupe.** Dark rim, light bevel. The lens shows the full-resolution scan under its centre at exactly the stated magnification; the tag (for example "5x") travels with it. One magnification per film.
- **Mark.** One per film, in the accent colour, anchored to the scan: an underline, an ellipse or a box. It appears on the table and inside the lens alike.
- **Caption plate.** Dark plate with an accent edge: a small mono label, one large reading, one line of explanation, the source in mono, and one line in the accent colour saying what is ours.

### 3.3 Choosing a look

Use the phase model when the answer is a quantity or a shape in space (how much, how big, where). Use the light table when the answer is in a document (who said what, when, in what words). A topic can have one film in each; they should agree on the numbers.

## 4. Colour

| Token | Value | Use |
|---|---|---|
| `accent` | **OPEN**: A vermilion `#FF4A1F` (recommended), B cobalt `#2F7BFF`, C magenta `#F0338C`, D cyan `#27D6EE` | Ours, not evidence. Projected light, marks, the hook underline, the plate edge and its "ours" line. Nothing else. |
| `phase.room` | `#06080B` | The dark room and text shades |
| `phase.plinth` / `plinth_lip` | `#24272B` / `#4A4F55` | Plinth and its lip |
| `phase.plate` / `plate_edge` | `#7A7D7B` / `#B9BBB7` | Plate top and side |
| `phase.matter` | `#F3F2ED` | The white model |
| `phase.key_light` / `fill_light` / `rim_light` | `#FFF4E6` / `#C9D6E6` / `#BCD0EA` | Warm key, cool fill and rim |
| `phase.text` / `text_secondary` / `text_mono` | `#F1F2EE` / `#A7B0B5` / `#9FAAB0` | Text on dark |
| `table.surface` / `surface_glow` / `surface_edge` | `#E7ECF0` / `#F6F9FB` / `#C9D1D8` | Light table |
| `table.frame` / `surround` | `#22262B` / `#15181C` | Table frame |
| `table.ink` | `#14161A` | Hook on the table |
| `table.plate` / `plate_text` / `plate_secondary` | `#2A2E33` / `#F2F3F0` / `#A9B1B7` | Caption plate |

Why vermilion is recommended: it is the strongest of the four on cream paper, it reads as warm light against the cool room, and it is far from the cyan-blue "hologram" colour common in reconstruction videos. Cyan is weak on paper. See `review/accent_options.jpg`.

Rules: one accent only; no gradients in the accent; neutral greys carry everything else; scans keep their own colour.

## 5. Type

Inter Display for display, Inter for text, JetBrains Mono for instruments and sources. All SIL Open Font License.

| Role | Face | Size / line (px) | Notes |
|---|---|---|---|
| Hook | Inter Display SemiBold | 74 / 82 | At most 2 lines, never under 56 px, on screen from the first frame |
| Eyebrow | JetBrains Mono Medium | 24 / 30, tracking 0.14 em | Place name, small capitals by spelling |
| Figure | Inter Display Bold | 168 / 168 | One per film |
| Figure unit ("of") | Inter Medium | 60 / 64 | Secondary colour |
| Label | Inter Medium | 42 / 50 | Says what the figure counts |
| Caption | Inter Medium | 40 / 51 | Never under 36 px, at most 2 lines |
| Plate reading | JetBrains Mono Bold | 64 / 68 | Light table only |
| Plate text | Inter Medium | 30 / 38 | |
| Legend, sources | JetBrains Mono Medium | 24 / 32 | |
| Credit | JetBrains Mono Medium | 22 / 30 | The smallest size allowed anywhere |

Nothing under 22 px. Numbers in captions are written as figures; the voice reads them as words (`"say"` in the script).

## 6. Layout and safe areas

Frame 1080 x 1920, 30 fps.

- Left margin x = 60. Right limit x = 1020 in the upper half.
- **Lower half (y > 960): nothing essential right of x = 880.** Platform buttons sit there.
- **Nothing essential below y = 1536**, and nothing essential above y = 200.
- Hook block starts at y = 200. The subject sits between about y = 420 and y = 1100.
- Readout (figure, label, legend) from y = 1104 to 1416 on the phase model; caption plate above y = 1390 on the light table.
- Captions: left-aligned at x = 60, at most 800 px wide, bottom edge at y = 1524.
- Credit: same zone as the captions, shown only when no caption is on screen.

`python -m engine.film <topic> check` tests these and refuses to render if any fails. On the light table it also checks that the loupe never leaves the frame and that no two pieces of text overlap, frame by frame.

## 7. Motion

- **The narration is the clock.** Every picture and sound event is written as a time on the narration (`"s3"`, `"s3.end"`, `"s4.cue:lintels"`, `"s5+0.4"`), never as a bare number. Re-record the voice and everything moves with it.
- **Every frame is a pure function of its frame number.** No state carried between frames.
- **The camera never stops.** Phase model: one slow orbit of about 55 degrees over the film, lowest and closest at the detail beat, on a smooth curve through keys. Light table: one slow push from 1.00 to about 1.05.
- **Light is the actor.** House lights cut quickly (about 0.3 s) and return slowly (about 1 s). The projector strikes with a six-frame flicker. Inferred things arrive as a sweep round the model: footprint, then volume.
- **Count with the picture.** Each counted thing is picked out once, in order; the figure lands on its final value as the voice says it.
- **Easing.** Arrivals ease out; moves ease in and out; nothing overshoots, bounces or pops. Text fades in 0.15 s (captions) to 0.6 s (plates).
- **One reading per film.** One figure, or one plate. If a second number is needed, it is spoken and captioned, not given its own graphic.

Beat order that has worked: hook and subject in house light; the count; lights down and the inferred part; one line of context or honesty; the code line; a hold with the credit.

## 8. Sound

| Element | Level | Notes |
|---|---|---|
| Voice | -16 LUFS integrated | Kokoro `bm_fable`, British English, speed 0.92. Peaks held to -1.5 dBTP by a limiter; its action is reported. |
| Room tone | -48 dBFS RMS | Low, steady, the whole film |
| Cues | At least 12 dB under the voice | Made by code: tick, click, swell, thump, hum, lift. Few, and only on picture events. |

No music. A silent beat of about two seconds before the turn. `python -m engine.film <topic> sound` writes the mix and a levels report; the render refuses to run if the report fails. A person must still listen: numbers cannot hear a squashed consonant or a cue that lands on the wrong word.

About 60 to 70 spoken words give 32 to 34 seconds at this pace. For a 30-second film write 55 to 60.

## 9. Captions, credits and labels

- **Captions** are burned in and are the narration, word for word, one sentence at a time. On dark grounds they sit directly on the picture with a soft shadow; on the light table they sit on a dark rounded box. Same face, size and position in both.
- **Sources on screen.** The source of the main number is on screen in mono while the number is: in the legend (phase model) or on the plate (light table).
- **Credit line.** One or two lines at 22 px on the final hold: data source and licence, and "Synthetic voice".
- **Post description.** The fuller credit from the film's `CREDITS.md`.
- **FACTS.md** per film: every spoken and on-screen claim, its source and the wording or method. An independent agent tries to refute each row before release, and the record of that is kept in the file.
- **Voice of the writing.** Calm and precise. British spelling. No hype words, no exclamation marks, no emoji. Hedge when the sources hedge ("most likely"), and never more.

### Platform labelling (read 12 November 2026)

- **YouTube.** The help page on altered or synthetic content requires disclosure for realistic content: a real person made to say or do something, altered footage of a real event or place, a realistic scene that did not happen. It exempts clearly unrealistic content and AI help with scripts. It does not mention stock text-to-speech voices. On that wording neither film needs the disclosure. Its monetisation policy excludes mass-produced or templated content, so each film must carry its own finding.
- **TikTok and Instagram.** **OPEN.** Their rule pages are blocked on the network this was built on and were not read. Secondary reports say both ask creators to label realistic AI-made video or realistic-sounding AI audio. Until the pages are read, the cautious course is to apply each platform's AI label for the synthetic voice.
- Both films already state "Synthetic voice" on screen.

## 10. Making a film

A topic is one data module in `topics/` plus its sources.

```
python -m engine.fetch topics/<site>/sources.json     # download the open data it lists
python -m engine.film <topic> voice                   # narration and the clock
python -m engine.film <topic> check                   # layout and safe areas
python -m engine.film <topic> stills                  # frames for approval
python -m engine.film <topic> accents                 # one still per accent option
python -m engine.film <topic> sound                   # mix and levels report
python -m engine.film <topic> render                  # MP4, stills, contact sheet in films/<id>/
```

Order of work: sources and `FACTS.md` first; script; stills for approval; refutation; sound for a person to hear; render last.

## 11. Account name

**Measured Past** (handle `measuredpast`), chosen by the account owner on 12 November 2026. Whether the handle is free on TikTok, Instagram and YouTube has not been checked. Bio line: "History and archaeology, shown from the evidence." The name is not shown in the films.
