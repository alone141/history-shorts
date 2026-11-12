# Projection on a white model: Stonehenge test still

Re-render (from this folder): `python -I build_data.py && node render.mjs still.png "D=235&VO=150&EL=40"`
(`osm_ways.json` comes from `parse_osm.py`, `pts_window.npy` from `extract_laz.py`; both already present.)

Data used: OSM extract (stones, ditch, embankment ways), LiDAR point cloud SU1040 (.laz, via pts_window.npy),
SU14sw_DTM_1m.tif (ground heights). Not used: DSM tif, Stukeley.

Method: circle fitted through mapped footprints (R 15.8 m, 30 even slots, phase 11 deg). A slot counts as standing
if a mapped stone assigned to it is >= 2.5 m tall in the cloud, or >= 2 cloud points >= 3 m lie within 1.5 m of the slot.
Result 16 standing, 7 fallen, 7 empty.

Guesses: 60 bluestones on a ring (radius = median of small mapped stones; count and 2 m height assumed); trilithon ring
spacing (10 uprights evenly at 22 deg, radius from tall inner stones), heights 4.1 m / 6.2 m, lintel sizes; all 30 circle
lintels shown as light even where some survive (surviving lintels are not modelled as matter; standing uprights capped at 4.1 m);
ground flattened; model scale 1:200 is nominal; plate cropped to 40 m radius so the Heel Stone and most of the bank are out.
Standing count may be low/high by one or two where footprints are merged (cloud and OSM disagree).

## Motion test (5 s, 30 fps, silent)
Re-render: `node render_motion.mjs` (uses scene_motion.html, `setFrame(n)` is a pure function of the frame; writes motion.mp4 and strip.jpg, deletes frame PNGs)
Timeline: 0-1.2 s house light only, "16 / circle uprights still stand", camera drifting (about 6 deg orbit, 1.5 deg rise, never stops).
1.2-1.45 s house light cuts to 20%; 1.5-1.7 s projector strikes with a 6-frame flicker; 1.7-2.7 s footprints wash round the circle.
2.1-3.9 s light volumes ease up by group (circle uprights, circle lintels, trilithon uprights, trilithon lintels, bluestones); "of 30" and PROJECTED LIGHT row fade in 1.9-2.6 s.
1.9-3.7 s house light returns slowly; 4.0-5.0 s hold on the still frame, camera still drifting.

## Full narrated film (31.6 s, 948 frames, 30 fps) -> film.mp4
Rebuild (from this folder): `python3 -I synth_film.py && node render_film.mjs 4 && python3 -I sound_film.py && ffmpeg -y -i picture_silent.mp4 -i audio/mix48k.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 160k -ar 48000 -ac 2 -t 31.6 -movflags +faststart film.mp4`
(synth_film.py writes narration.json, the clock; scene_film.html reads it, so every picture event is keyed to the voice. render_film.mjs runs 4 parallel Chromium workers, about 7 min.)
Timeline (s): 0.4-4.9 beat 1 house light, no projection; 5.3-8.9 "Thirty..." and 9.2-11.4 "Sixteen still stand": 16 circle uprights picked out in turn, count rises with them, lands 16 on "Sixteen" (soft tick per stone);
11.7-13.7 beat 3 silent: relay click + house cut at 11.9, projector strike with 6-frame flicker, lamp thump + fan hum at 12.5; 13.7-18.1 beat 4: footprints then uprights, lintels at "ring of lintels" (16.5), "of 30" and PROJECTED LIGHT row at 14.7;
18.5-23.4 beat 5: trilithons then bluestones, camera lower and closer; 23.75-26.4 and 26.8-29.1 beat 6: legend rows emphasised on "White" / "Light", camera back to the still framing; 29.1-31.6 beat 7 hold with source line, no fade.
Captions at y 1418-1516 (38 px, max 2 lines, x < 880). Lower text block moved up ~20-30 px to make room. 16 slots map onto the model's tall circle stones (some merged footprints, so a stone can pulse twice).
