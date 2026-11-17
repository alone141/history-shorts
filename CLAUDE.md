# Notes for Claude working in this repository

## Feedback from the account owner

**Do not take the channel's direction too literally (12 November 2026).**
What was said: "you are taking the direction of the channel too literally,
hyperfixating on one kind of rule that defines the channel and its one of your
weaknesses."
Context: the owner had rewritten the standing film's script in a more
conversational voice ("Here is what survives today. And here is what we
infer."). I argued for keeping the spoken "White is... / Light is..." lines
because the design guide treats that colour rule as the channel's identity. I
had also been treating other design-guide rules (restrained tone, "shown not
told", code-made sound cues) as fixed.

My interpretation, to apply in every session here:
- The design guide and the README describe a starting point, not a set of
  constraints. The owner's taste and what makes a film watchable come first.
- Do not defend a stylistic rule against the owner's edit. If a rule seems
  worth mentioning, say it once in a sentence, then do what was asked.
- Do not build recommendations around one defining idea of the channel
  (for example the white/light rule); propose a range.
- This does not relax factual accuracy: still flag an edit that makes a claim
  false, and say why.

**What the owner wants from a film (15 November 2026, Sphinx film).**
Each point is something the owner said or chose while the buried-Sphinx film
was made; the "so" part is my interpretation.

- "This feels like everyone knows about the Napoleon situation." So: do not
  pitch a well-worn myth-bust as the hook. Offer angles a viewer has not heard,
  and say which ones are familiar.
- "Start of the video screen feels frozen as nothing is happening." So:
  something must move from the first frame. On the light table, give objects an
  `enter` and bring the loupe in early.
- "The narrator feels too calm and non enthusiastic"; the owner then chose the
  Kokoro voice `af_heart` (US female) at speed 1.15 over the house voice. Later:
  "talking speed is fine but it should wait in between some sentences to
  emphasize". So: start new films with that voice and speed, and put pauses
  (`gap_before` 0.5 to 0.8 s) before reveals and after the hook. Whether the
  older films should change voice was not asked.
- "Make the script reference whats shown on the video." So: write narration
  that points at the picture ("These two drawings...", "See the man on the
  donkey?", "Look at the sand line."), timed to the loupe and marks.
- The owner asked for background music, chose a free licensed track over
  code-made sound, and picked "Desert City" (Kevin MacLeod, CC BY 4.0) from
  seven samples, over the lighter tracks. So: films get a music bed (`music` in
  the film module, about -30 LUFS); prefer a track that signals the place; keep
  the attribution in POST.md.
- The owner rewrote the script line by line twice and cut lines ("This.",
  "Those are its paws."). So: show the full script as a numbered list with the
  pauses marked before rendering, and expect edits; fix grammar only, and fill
  a gap the owner marks (e.g. a name) from the research notes.
- "It does not have the question punctuation on it (voice freq change), if
  it's not possible remove that line." Kokoro does not raise its pitch on most
  questions (measured: only "See the man on the donkey?" rose). So: avoid
  ending a line on a yes/no question; write it as a statement, or measure the
  pitch before keeping it. (Superseded on 16 November 2026: questions are
  wanted and the pitch engine now makes the rise; see the next section.)
- "The optical zoom is too much let's dial it back to 2x" (17 November 2026,
  Colosseum mock, which used a 3x loupe like the Sphinx film). So: new light
  table films start with `"magnification": 2.0`.
- I cannot hear audio. What worked: send short samples (voices, music mixed
  under the narration) and let the owner pick by number, instead of describing.
- Process the owner accepted: Sonnet agents for source research and one
  hostile fact check, Haiku for FACTS/CREDITS/POST, renders of about 4 minutes
  run without asking. Run the fact check before the first render.

**Pitch is mine to plan, set and check (16 November 2026, Colosseum film).**
What was said: "You are the responsible one for pitch changes in the script.
From now on it's one of the most important aspects of video generation. Redo
the narration and script."
Context: the owner had asked for two questions in the script ("Did you
know ...?", "Can you see the piers?"). I sent a mock, reported a small measured
rise on the second one, and asked the owner to listen for whether it landed as
a question.

My interpretation, to apply in every session here:
- Do not hand a pitch question back to the owner. Decide what each line's pitch
  should do, make it happen, measure it, and report the numbers.
- The tool is `engine/pitch.py` (README, "The narrator's pitch"). A film sets
  `"prosody": {}`; a script line carries `"pitch": {"focus": [...], "ends":
  [...]}`. `film voice` prints each movement asked and heard and writes
  `build/<film>/voice/pitch.png`. Look at that sheet before every render;
  `check` and `render` stop on a movement that did not come out.
- Why it was needed (measured): Kokoro alone raised 1 of 8 yes/no questions,
  and no wording, punctuation, speed or voice changes that; it often gives the
  last word of a phrase no pitch at all. So a question in a script only works
  through the engine.
- Write the script for pitch: a yes/no question rises; a what/why question
  falls; a line cut before a pause ends on `"continue"`; one accent per clause,
  on a word with a long voiced vowel ("iron", "holes", "people"; not
  "accepted" or "stalls"); vary the shapes from line to line. Aim for a spread
  of about 4 semitones over the narration (the model alone gave 3.0 on this
  script, which the owner had called too calm).
- "It's right here: ends with a rise when it should not. same issue with
  'Most of the clamps are gone now'" (17 November 2026). I had put a small
  "continue" rise on both, one by the engine's default for a colon, one by
  hand for a contrast pair. So: a finished statement falls, and a colon keeps
  the model's own ending (now the default). Later the same day: "'iron was
  valuable,' ends with a pitch raise when it shouldnt", although that clause
  is unfinished and runs on into the next line. So: do not ask for
  `"continue"` at all. The only rise inside a statement the owner has
  accepted is on the first of two choices ("was it barbarians, or market
  stalls?"). The voice also rises by itself at some commas ("gone now,"
  climbed 7 semitones with nothing asked), so a finished clause inside a line
  gets `"fall"` with `"fall_st": 2.0`, and `film voice` prints "left alone
  RISES" for any ending it did not touch that climbs. Read those before
  sending audio; a lead-in ("In 1651,", "After Rome fell,") may stay.
- "these two lines are perfect" (17 November 2026), said of "Those dark dots
  are holes, and they've puzzled people for centuries." and "In 1651, this
  page asked: was it barbarians, or market stalls?", after the owner had asked
  for "a more natural flowing dialogue". My reading of what the two share,
  to write other lines by (the owner confirmed these two points, and struck a
  third, "each line does two jobs", as unnecessary):
  - the pitch moves because of how the sentence is built (two clauses joined
    by "and"; a choice of two, up on the first and down on the second), not
    because a movement was added to its end. The one rise in them, on
    "barbarians,", is there because the sentence asks for it;
  - they sound said, not read: a contraction, a question the viewer would
    ask, plain nouns, no hedging phrase in front.
- A question must be short (12 words at most) and end on a word the voice
  keeps voiced. My first opening, "Did you know people made most of the
  Colosseum's holes?", passed my own check and was wrong: an independent
  re-measurement showed its rise was a 50 ms step on a breaking voice. "...
  holes are man-made?" gave a clean 200 ms glide. So when the check says "a
  step, not a glide", reword the line; do not turn the settings up.
- Have the pitch checked by something other than my own code before sending.
  The verification agents found what my checks had passed: the broken rise
  above, falls I reported as measured that were only the curve I had set (the
  model ends most statements in a creak nobody can measure), and crashes on
  lines with digits. `film voice` now says "set, not heard" for those falls.
- I still cannot hear. What I can vouch for is the pitch measured in the audio,
  not how natural it sounds; say that plainly when sending a film.
- The engine is tuned for `af_heart` at 1.15 only. With `bm_fable` two of five
  test questions got a real glide; the older films were not converted.
- Process the owner accepted for this: a workflow with Sonnet agents (research
  on intonation, a baseline measurement of the voice, three script writers and
  three judges, then independent verification of the engine).

**The Colosseum film, start to finish (posted 17 November 2026).**
"Why is the Colosseum full of holes?" was accepted and posted by the owner.
What follows is my reading of how it went, for the next film; the owner asked
me to record what I learned and did not dictate these points.

- Send the narration alone before rendering. From the conversational rewrite
  on, I sent a narration-only audio file with the numbered script, the owner
  corrected lines by ear ("ends with a rise when it should not"), and the
  film was rendered once the narration was right. Earlier I had rendered a
  full mock for every change.
- When the owner reports one ending, check every ending of that kind before
  sending again. Three finished clauses were reported one after another
  before I listed them all and found four more that the voice raised by
  itself.
- When the owner reports a sound my measures do not show, do not rebuild the
  engine on it. "Too airy" led me to change how every question is spoken; the
  owner then said "It's ok I've misheard it" and I took it all out. Next time:
  send the same clip beside a variant first, and leave verified audio alone
  until the owner confirms the fault.
- Run the fact check again after every rewording, not only on the first
  script. Making the lines conversational introduced one misleading line
  ("this page blamed barbarians", when its author preferred the market
  stalls) and one false attribution ("what do historians say", answered by a
  page of 1892). The same check found that the caption plate's source line
  named sources that do not give the figure on the plate.
- The owner accepted the music heard in the mocks ("music is good") without
  going through the seven samples: "Suonatore di Liuto" (Kevin MacLeod, CC BY
  4.0), an Italian lute piece, chosen by me because it signals the place.
- 35 seconds was accepted; the conversational script needed about 100 words.
- The post title states the finding ("Most of the Colosseum's holes are
  man-made"), not the question on screen.

