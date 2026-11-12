# What did Stonehenge look like in 1740?

Archive light table. Real public-domain page scans on a backlit table, a loupe
at a true magnification, one mark, a caption plate.

Status: **rendered** (12 November 2026, vermilion accent), after the second refutation pass. Not posted; the account name is still open.

## The finding

On page 19 of his book of 1740, William Stukeley counts the outer circle:
17 uprights standing, 6 lintels in place, 2 on the ground, 22 carried off.
A study published in 2022 gives the same four numbers for today.

## Script (68 spoken words, 32.7 s)

1. William Stukeley surveyed Stonehenge in the 1720s.
2. His book of 1740 counts the outer circle:
3. seventeen uprights left standing,
4. six lintels in place, two on the ground, twenty-two carried off.
5. A study published in 2022 gives the same four numbers.
6. In the circle, three stones fell and were put back, and more were straightened.
7. The scans are real. The mark and the lens are ours.

## What happens when

| Voice | Picture | Sound |
|---|---|---|
| 1 | The table: page 19 and two of Stukeley's engraved views. A slow push begins. | Room tone |
| 2 | The loupe (5x) glides onto the page. | Swell |
| 3 | The lens rests on the sentence; an underline draws under "17 left ſtanding." | Tick as it closes |
| 4 | The loupe glides down the paragraph to the lintels and "22 are carried off". | Swell |
| 5 | The loupe lifts away. The caption plate rises: 17 · 6 · 2 · 22, with both sources. | Lift |
| 6, 7 | Hold; the push continues. | |
| (hold) | Credit line. | |

## Files

- `stonehenge-1740.mp4`: the film, H.264, 1080 x 1920, 30 fps
- `stills/`, `contact_sheet.jpg`: eight frames
- `narration.json`, `sound_levels.json`, `render.json`
- `FACTS.md`: every claim and its source, with the refutation record
- `CREDITS.md`: on-screen credit, post-description credit, licences

## Rebuild

```
python -m engine.film stonehenge_1740 check
python -m engine.film stonehenge_1740 stills
python -m engine.film stonehenge_1740 sound
python -m engine.film stonehenge_1740 render
```

## What is real and what is ours

- The three sheets are scans of the Wellcome Collection copy, at true proportions. Nothing in them is redrawn or generated. One uniform levels curve is applied to all scan pixels.
- Ours: the table, the shadows and slight tilt of the sheets, the loupe, the underline, the caption plate, the subtitles.
- The loupe is true: five lens pixels for each on-table pixel, sampled from the full-resolution scan.

## Things to know before posting

- The title says 1740, the year the count was printed. Stukeley made it in the 1720s, and the first line says so.
- The film does not claim the same seventeen stones stood then, and does not identify stones on the engravings.
- The narration is a synthetic voice and the film says so on screen.
