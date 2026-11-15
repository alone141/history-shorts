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
  pitch before keeping it.
- I cannot hear audio. What worked: send short samples (voices, music mixed
  under the narration) and let the owner pick by number, instead of describing.
- Process the owner accepted: Sonnet agents for source research and one
  hostile fact check, Haiku for FACTS/CREDITS/POST, renders of about 4 minutes
  run without asking. Run the fact check before the first render.
