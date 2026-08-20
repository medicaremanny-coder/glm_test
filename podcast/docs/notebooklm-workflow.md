# NotebookLM workflow — turning a kit into an episode

_Written 2026-08-11._

The pipeline automates everything on both sides of NotebookLM. NotebookLM itself
is hands-on: there is no public API for creating a notebook, adding a source, or
generating an Audio Overview, so steps 3–5 below are done by a person in a
browser. Budget about **15 minutes per plan per language** the first time, less
once you have the rhythm.

## The loop

### 1. Write the plan spec

Copy `plans/example-h1234-001-2026.json` to `plans/<carrier>-<plan-id>-<year>.json`
and replace every field from the carrier's Summary of Benefits.

Rules that matter more than they look:

- **`sob_source` must name the actual file and pages you read.** When a member
  disputes something they heard, this is how you find the line in ninety seconds.
- **`counties` must be the counties this benefit set is accurate for.** One
  contract can pay different copays in Miami-Dade than in Broward. If the
  benefits differ, that is two plan specs, not one.
- **Read the in-network column.** The most common transcription error is reading
  an out-of-network amount into an in-network field, and it survives every
  automated check in this repo because both are valid dollar amounts.
- **Spanish fields are not optional for a Spanish episode.** Leave `name_es` or
  `member_cost_es` blank and the generator writes `[TRADUCIR]` into the source
  document rather than falling back to English. That is deliberate — an
  untranslated copay is worse than a missing one.

### 2. Build the kit

```
python podcast/cli.py build
```

Writes `podcast/kits/<slug>/<lang>/` with four files and records the plan in
`catalog.json` as `kit_built`. A kit reported as `BLOCKED` has untranslated
fields; fix the spec and rebuild before going further.

### 3. Create the notebook

In NotebookLM, create one notebook per plan-year-language. Name it the slug:
`h1234-001-2026-en`.

Add **`source.md` as the only source.** This is the whole trick. NotebookLM
synthesizes from what it is given, and anything else in the notebook — the raw
SOB PDF, a carrier brochure, last year's version — becomes material the hosts
can pull a number from. One source means the audio can only say what a human
already verified.

Do not add the SOB PDF "for completeness." That is the single change most likely
to put a wrong number in a member's ear.

### 4. Generate the Audio Overview

Open the Audio Overview panel, choose **Customize**, and paste the contents of
`steering.txt` into the instructions box. Generate.

If the language controls are available in your NotebookLM account, set the
output language to Spanish for `es` kits rather than relying on the prompt
alone. The prompt asks for Spanish as a fallback, but an explicit setting is
more reliable.

Generation takes a few minutes. Longer plans sometimes come back short — if the
episode skips whole categories, regenerate before assuming the source is at
fault; output length varies between runs on identical input.

### 5. Listen to the entire thing

Not a skim. Open `review.md` and work the checklist with the audio playing.

The failure modes worth listening for, in order of how often they happen:

1. **A number drifts.** "About forty dollars" instead of "forty dollars," or a
   maximum out-of-pocket rounded to "around forty-five hundred."
2. **A benefit gets invented.** Hosts fill conversational gaps with plausible
   Medicare-sounding benefits that this plan does not have. Transportation and
   gym memberships are the usual intruders.
3. **A comparison appears.** "Which is better than most plans" turns an
   educational communication into a marketing claim. See `compliance.md`.
4. **The disclaimer gets paraphrased.** It has to be verbatim, at both ends.
5. **The hosts speak as the plan.** "We cover" instead of "the plan covers."

Any of these means regenerate — usually with a tightened `steering.txt` — not
edit the audio.

### 6. Record, approve, publish

```
python podcast/cli.py record-audio h1234-001-2026 en --file audio/h1234-001-2026-en.m4a
python podcast/cli.py approve     h1234-001-2026 en --by "Manny Leon"
python podcast/cli.py publish     h1234-001-2026 en --link "https://.../h1234-001-2026-en.m4a"
```

The catalog refuses to let you publish something you never approved, and refuses
to approve audio you never recorded. That is the point of it.

### 7. Send

`delivery.md` holds the text and the email subject in both languages, with
`{{first_name}}` and `{{audio_link}}` to fill in. Before sending, always:

```
python podcast/cli.py check h1234-001-2026 en
```

which fails if the episode is unpublished **or** if the plan spec changed since
the audio was approved.

## When a plan changes

Change the spec, rebuild, and the catalog silently discards the old approval —
the episode drops back to `kit_built` and `check` starts failing. You cannot
send stale benefits by forgetting to redo the audio; you can only send them by
re-recording and re-approving them.

`python podcast/cli.py status` lists everything, flagging `[STALE — spec changed]`.

This is also the mid-year-change path. Carriers do adjust benefits mid-year, and
AEP changes everything at once — expect to rebuild the whole library each
October for the following contract year.

## What is worth automating next

In rough order of payoff:

1. **Hosting and links.** Right now `--link` is pasted by hand. Dropping the
   audio in cloud storage and having `publish` mint the URL removes the step
   most likely to send someone the wrong file.
2. **The send trigger.** Nothing here watches for a new enrollment. Wiring the
   signup event to `check` + `delivery.md` is what makes this run without Manny.
3. **Spec drafting from the SOB.** A first-pass extraction that a human then
   corrects would cut step 1 substantially. Note the ordering: extraction
   proposes, a human disposes. Never the reverse.

Not on the list: automating step 5. The listen-through is the control that makes
the rest of this safe to run.
