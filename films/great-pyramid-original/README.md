# What did the Great Pyramid originally look like?

Phase model. A white model of what stands today, built from the surveyed level of
every course, on a plate in a dark room; a projector paints the lost casing and
apex as light.

Status: **stills only**. Script and readout revised after the fact check of
14 November 2026 (see FACTS.md). Awaiting the last review and the final render. Not posted.

## The answer the film gives

What stands today is a staircase of 203 courses of stone, 138.5 m to its highest
block, ending in a flat top about 11 m across. As finished it was smooth, cased in
white limestone, and rose to a point 146.7 m high. Almost all of that casing was
quarried away in the Middle Ages. Its capstone has never been found.

## Script (69 spoken words, 26.5 s)

0. What did the Great Pyramid originally look like? (the title, spoken as the opening; no caption, because it is on screen)
1. What stands today is a staircase: 203 courses of stone.
2. It ends in a flat top, about 11 metres across.
3. But it was finished smooth: cased in white limestone, rising to a point.
4. Almost all of that casing was quarried away in the Middle Ages, much of it to build Cairo.
5. Its own capstone has never been found.

Captions are shown a few words at a time, in the larger size.

## What happens when

| Voice | Picture | Sound |
|---|---|---|
| 0 | House lights. The white pyramid fills the frame and turns slowly. Half a second in, the lights dip and the casing flashes on in light for under a second: a glimpse of the answer. | Relay click |
| 1 | A band of brightness runs up the courses as they are counted; the readout climbs with it to 138.5 m, 454 ft, "still standing · 203 courses". The camera rises towards the top. | A soft tick on every eighth course |
| 2 | Close on the flat top and the few blocks left on it. | |
| (pause) | House lights cut. The projector strikes. | Relay click |
| 3 | The casing climbs the dark pyramid in light, from its footprint to the level of the flat top, then closes to a point as the voice says "rising to a point". The readout runs up and lands on 146.7 m, 481 ft, "as finished · casing and apex". | |
| 4 | On "was quarried away" the casing goes dark and the house lights return: the staircase again. The readout drops back to 138.5 m. The missing top stays lit. | Relay click |
| 5 | Close on the flat top with the point of light above it. The camera pulls back to where it started and the light goes out, so the film closes on its first frame. | |
| (hold) | Credit line. | |

## Files

- `stills/`, `contact_sheet.jpg`: eight frames
- `narration.json`: the spoken text and its timing
- `sound_levels.json`: measured loudness of voice, room tone and every cue
- `FACTS.md`: every claim and its source, with the refutation record
- `CREDITS.md`: on-screen credit, post-description credit, licences
- `POST.md`: title, description, pinned comment and posting notes
- `great-pyramid-original.mp4` and `render.json` are written by the final render.

## Rebuild

```
python -m engine.fetch topics/giza/sources.json          # Petrie's plate and text, 2.5 MB
python -m engine.film great_pyramid_original check
python -m engine.film great_pyramid_original stills
python -m engine.film great_pyramid_original sound
python -m engine.film great_pyramid_original render      # about 15 minutes on four cores without a graphics card
```

The model reads `topics/giza/courses.json`, which is kept in the repository. To rebuild
that table from the scans: `python -m topics.giza.plate_tiles` cuts the plate into
reading tiles, and `python -m topics.giza.build_courses` turns the readings in
`plate_readings.json` into the table and checks them against the plate's own drawing.

## What is modelled and what is not

- The height of every white step is the level Petrie surveyed for that course in 1880-82.
- The outline of the steps follows the planes he sighted over the edges of the masonry at the bottom and at the flat top; in between it is drawn straight. Individual blocks, the gash and the entrance on the north face, and the hollow down the middle of each face are not drawn.
- The two courses above the flat top are a few blocks in the middle; their outline is schematic.
- The light is one smooth pyramid on Petrie's base, rising to the height he worked out from the base and the slope. No capstone is drawn as a separate thing, and nothing is gold.
- The 54 m of casing still in place at the foot is too small to draw at this scale; the film says "almost all".

Details and sources: FACTS.md, "Modelling choices".

## What this film uses that the Stonehenge films do not

All are options in the engine, off unless a film asks for them: a readout in metres
and feet that follows the count; light that rises with a bright front; a first
glimpse of the answer; captions a few words at a time; a camera that goes from the
whole model to a detail a few metres across; its own shorter pauses.

## Labelling when posting

The narration is a synthetic voice and the film says so on screen. The picture is a
model drawn by code from survey data, not footage and not generated imagery. See
the design guide for what each platform asks.
