# Plan Benefits Podcast

Turns a Medicare plan's Summary of Benefits into a short NotebookLM audio
episode, in English and Spanish, that a member receives when they enroll — so
they can learn their benefits on the drive to an appointment or before bed
instead of reading an eighty-page booklet.

_Started 2026-08-11._

## The shape of the problem

NotebookLM has no public API. You cannot create a notebook, attach a source, or
generate an Audio Overview from a script. So this pipeline does not try to
automate NotebookLM — it automates **everything on both sides of it** and makes
the manual middle as short and as safe as possible.

```
Summary of Benefits (PDF)
        │  a human transcribes it, once per plan-year
        ▼
plans/<slug>.json           ← the only thing the generator trusts
        │  python podcast/cli.py build
        ▼
kits/<slug>/<lang>/
    source.md       the single source you paste into NotebookLM
    steering.txt    the Audio Overview customization prompt
    delivery.md     the message the member gets, EN + ES
    review.md       the accuracy checklist, signed before anything is sent
        │  ~15 min by hand in NotebookLM
        ▼
audio file
        │  record-audio → approve → publish
        ▼
catalog.json        knows what is safe to send, and what went stale
```

## Two design decisions worth knowing

**The plan spec is typed by hand, not extracted from the PDF.** The output is
audio telling a member what their health care costs. A layout-parsing mistake on
a benefits grid — reading the out-of-network column as in-network — becomes a
confident spoken sentence a member acts on. A spec takes about fifteen minutes
and carries its own provenance, so every number in an episode traces back to a
page a person actually read.

**The catalog fingerprints the benefits the audio was made from.** Change a
copay in a spec and the approved episode goes stale automatically: it drops out
of `check` and shows up flagged in `status`. You cannot send outdated benefits by
forgetting to redo the audio — only by deliberately re-recording and
re-approving them.

## Use it

```
python podcast/cli.py build                       # every plan, both languages
python podcast/cli.py status                      # what exists, what is stale
python podcast/cli.py record-audio <slug> en --file audio/x.m4a
python podcast/cli.py approve     <slug> en --by "Manny Leon"
python podcast/cli.py publish     <slug> en --link "https://..."
python podcast/cli.py check       <slug> en       # safe to send right now?
```

`<slug>` is `<plan-id>-<year>` lowercased: `h1234-001-2026`.

Full walkthrough, including the NotebookLM steps and what to listen for:
**`docs/notebooklm-workflow.md`**.

## Spanish is a first-class output, not a translation pass

Spanish fields live in the plan spec next to their English counterparts. Leave
one blank and the generator writes `[TRADUCIR]` into the source document instead
of falling back to English, and `build` reports the kit as `BLOCKED`. An
untranslated copay silently read in English inside a Spanish episode is the
specific outcome this prevents.

Costs that read identically in both languages (`$0`, `20%`) pass through without
a translation. Anything with a word in it (`$40 copay`) does not.

## Before this goes to a real member

Read **`docs/compliance.md`**. Short version: the material names a plan and
states cost sharing, which puts it inside what CMS governs. The design keeps it
on the *communications* side of the marketing line by sending episodes only to
members already enrolled in the plan described — but three questions need real
answers from each carrier's compliance department before launch, and the
placeholder disclaimer in the example spec is not one of them.

The pipeline is ready to run. It has not been cleared to launch.

## Layout

| Path | What it is |
|---|---|
| `planspec.py` | The plan-year model, validation, and the translation-gap rules |
| `episode.py` | Kit generation — source doc, steering prompt, delivery, review |
| `catalog.py` | Episode states, approval gates, and staleness detection |
| `cli.py` | The commands above |
| `plans/` | One JSON spec per plan-year (`example-*` is a fake template) |
| `kits/` | Generated output, git-ignored — rebuild it, don't edit it |
| `docs/` | Workflow and compliance |

## Tests

```
cd podcast && python -m pytest -q
```

101 tests, no dependencies beyond `pytest`.
