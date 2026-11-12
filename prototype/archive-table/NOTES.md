# Archive light table still
Re-render: `cd <this folder> && python3 build.py`  (writes still.png, 1080x1920)
Data: Stukeley 1740, archive.org b30448554, jp2 scans 0059 (plan, Tab. XI), 0067 (Prospect from the Southwest, Tab. XIII, p. 24), 0083 (inward view, Tab. XVII). OSM/LIDAR not used.
Loupe: 2.5x by construction (crop of the jp2 master at 2.5x the on-table scale). Orange ellipse = our mark on the lintel.
Guesses: table glow, shadows, paper lift, loupe rim are rendered effects, not scans. Plate 0059 is laid as scanned (rotated 90 degrees); plate tilt angles are arbitrary. "Great lintel" is not labelled on frame.
Motion test (5 s, 30 fps, 1080x1920): re-render with `cd <this folder> && python3 render_motion.py` (writes motion.mp4, strip.jpg; no frame PNGs kept).
Timeline: whole clip slow push 1.00 to 1.04 (25% linear + 75% smoothstep, never stops); hook fixed on screen.
0-1.0 s table and three plates only. 1.0-3.0 s loupe glides in on a curved eased path (fades in 1.0-1.4), lens shows the 2.5x master crop at its position every frame; 2.5x tag travels with it.
3.0-3.5 s orange ellipse draws on from the top; 3.45-3.8 s leader grows down from the loupe.
3.6-4.4 s caption plate rises 28 px and fades in; 4.4-5.0 s hold on the still frame, push still creeping (ends at 1.04 scale, so slightly tighter than still.png).

## Full narrated film (about 28.8 s)
Rebuild: `cd <this folder> && sh build_film.sh`  (narrate.py -> narration.json + voice_raw.wav; render_film.py -> film_silent.mp4 + film_strip.jpg + timeline.json; make_sound.py -> mix.wav; ffmpeg mux -> film.mp4). Voice bm_fable en-gb 0.92. ~3 min render on 4 cores.
Timeline (s): 0.4-9.1 beat 1 table + hook, push 1.00 to 1.06 whole film; 9.5-11.5 loupe glides to lintel (swell); 12.1-13.0 orange ellipse draws, tick at 13.0; 15.0-16.6 loupe glides down to man+dog (swell), 16.6-17.3 new mark; 19.1-19.8 loupe fades; 19.5-20.6 orange ring draws round plan plate (Tab. XI "Geometrical Ground-plot of Stonehenge", complete circle -> beat-4 line "drew the circle complete"), camera focal eases toward it; 23.3-24.2 caption plate eases in; hold to 28.8.
Subtitles = narration.json, 0.15 s fades, 40 px, bottom band y<=1528. Mix: voice -16 LUFS, room tone -48 dBFS RMS, cues 14 dB under voice peak.
