# How much of Stonehenge is still standing?

Phase model. A white model of what survives today, on a plate in a dark room;
a projector paints what is inferred as light.

Status: **rendered** (12 November 2026, vermilion accent), after the second refutation pass. Not posted; the account name is still open.

## The answer the film gives

Seventeen of the outer circle's thirty uprights stand. Six lintels are in place.
Three of five trilithons are complete. Thirteen of the seventeen were re-set or
secured in the twentieth century.

## Script (70 spoken words, 33.8 s)

1. The great stones were raised about 4,500 years ago.
2. The outer circle most likely had thirty uprights.
3. But of those thirty, only seventeen still stand.
4. Here we show where the others stood, and the missing lintels.
5. Last century, engineers re-set or secured thirteen of the seventeen.
6. Inside, three of the five trilithons still stand complete.
7. Here is what survives today.
8. And here is what we infer.

## What happens when

| Voice | Picture | Sound |
|---|---|---|
| 1 | House lights. The model turns slowly. | Room tone |
| 2, 3 | Each standing upright is picked out once; the figure counts to 17 as the voice says it. | One soft tick per stone |
| (pause) | House lights cut. The projector strikes with a flicker. | Relay click |
| 4 | Footprints of the missing uprights sweep round the circle, then the uprights rise; on "lintels" the missing lintels appear. "of 30" joins the figure. | |
| 5 | Hold; the camera keeps moving. | |
| 6 | The two fallen trilithon uprights and their lintels appear in light; camera lowest and closest. | |
| 7 | House lights rise; the white legend row brightens. | |
| 8 | House lights fall; the light pulses; the light legend row brightens. | |
| (hold) | Credit line. | |

## Files

- `stonehenge-standing.mp4`: the film, H.264, 1080 x 1920, 30 fps
- `stills/`, `contact_sheet.jpg`: eight frames
- `narration.json`: the spoken text and its timing
- `sound_levels.json`: measured loudness of voice, room tone and every cue
- `render.json`: what the encoder wrote
- `FACTS.md`: every claim and its source, with the refutation record
- `CREDITS.md`: on-screen credit, post-description credit, licences

## Rebuild

```
python -m engine.film stonehenge_standing check
python -m engine.film stonehenge_standing stills
python -m engine.film stonehenge_standing sound
python -m engine.film stonehenge_standing render
```

The data behind the model is rebuilt with `topics/stonehenge/prepare_survey.py`, `digitise_plan.py` and `build_stones.py` (see the root README).

## What is modelled and what is not

- Every surviving stone is drawn from a published plan and stands or lies at its height in the 2021 laser scan. The ground is flattened.
- Missing circle uprights and lintels are projected at even positions round the circle. That evenness is a modelling choice.
- Bluestones the scan cannot resolve are drawn as low footprints. Missing bluestones are not projected: their number is not agreed.
- The Heel Stone, Slaughter Stone, Station Stones, ditch and bank are outside the plate.

## Labelling when posting

The narration is a synthetic voice and the film says so on screen. The picture is a model drawn by code from survey data, not footage and not generated imagery. See the design guide for what each platform asks.
