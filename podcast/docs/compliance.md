# Compliance notes — benefits podcast

_Written 2026-08-11. **Not legal advice, and not verified with a carrier.**
Everything in the "verify before launch" section below needs a real answer from
a real compliance department before the first episode goes to a real member._

## Why this needs care at all

The material this pipeline produces names a specific plan and states specific
cost-sharing amounts, and it goes to Medicare beneficiaries. That places it
inside the regime CMS governs under 42 CFR Part 422 Subpart V and the Medicare
Communications and Marketing Guidelines. Being audio, being AI-generated, and
being "just a summary of what we already sent them" do not move it outside that
regime.

The distinction that decides how heavy the requirements are:

- **Marketing** — material intended to draw attention to a plan or influence an
  enrollment decision. Mentioning benefits or cost sharing pushes material
  toward this category. Marketing material generally requires carrier review and
  CMS submission before use.
- **Communications** — material that informs someone about a plan they are
  already in. Lighter requirements, but it still must be accurate and not
  misleading.

**This project is designed to sit on the communications side of that line**, and
the design reflects it deliberately:

- Episodes go **only to members already enrolled in the plan the episode
  describes**. This is the load-bearing constraint. The same audio posted
  publicly, sent to a prospect, or used in a sales appointment is a different
  category of material with different obligations.
- `steering.txt` forbids comparisons to other plans and superlatives. "Better
  than," "cheaper than," and "the best plan for you" are what convert an
  explanation into a marketing claim.
- `steering.txt` forbids any benefit not present in the source document.
- The disclaimer is read verbatim at the start and end of every episode.

Staying on the communications side is a discipline, not a property. It holds
only as long as distribution stays post-enrollment.

## Verify before launch

Do not treat any of this as settled. Each item needs an answer from the specific
carrier, in writing, kept with the plan spec:

1. **Does this carrier consider a post-enrollment audio summary a communication
   or a marketing material?** Ask about this exact format — agent-produced,
   AI-generated audio, describing that member's own plan. Carriers differ, and
   some treat any agent-produced plan-specific material as requiring review
   regardless of audience.
2. **Does it require carrier review or CMS/HPMS submission before use?** If yes,
   build that review into the workflow between `approve` and `publish`, and
   record the approval reference in the catalog entry's `notes`.
3. **What is the exact required disclaimer for this material type?** The text in
   `example-h1234-001-2026.json` is a *placeholder built from the standard TPMO
   disclaimer language* and has not been confirmed as correct for this use.
   Replace `disclaimer_en` / `disclaimer_es` per carrier with what they specify.
4. **Does the carrier accept a machine-generated Spanish translation?** Several
   require translated member materials to be certified. The pipeline demands a
   human translation in the spec, which helps, but certification is a separate
   question.
5. **Are there rules about synthetic voices?** This is newer ground than the
   rest and the least likely to have a settled answer. Ask anyway, and ask
   whether the episode must disclose that the voices are AI-generated. If the
   answer is yes or unclear, disclose it — it costs one sentence.

Until 1–3 have real answers, treat the pipeline as ready-to-run but **not
launched**.

## Rules that hold regardless of the answers

- **The SOB and the Evidence of Coverage govern.** The audio is a walkthrough.
  Every episode says so, in the disclaimer, at both ends.
- **Never send an episode to someone not enrolled in that plan.** Not to a
  prospect, not to a spouse on a different plan, not as a sample. If a prospect
  asks for one, the answer is a generic Medicare-education episode with no plan
  named — which this pipeline does not produce today.
- **Never publish an episode publicly.** Not on TikTok, not on a podcast feed,
  not on the website. Public distribution of plan-specific benefit content is
  marketing, full stop, and the TikTok compliance rules in
  `marketing/tiktok/review-before-posting-checklist.md` apply instead.
- **Never let an episode recommend care.** Explaining that a plan pays for a
  service is a benefit statement. Suggesting someone get that service is a
  clinical recommendation, and neither Manny nor a synthetic host is in a
  position to make one.
- **A human listens to every episode before it is sent.** Not a sample of
  episodes — every one. `review.md` is the record that it happened, and the
  catalog will not publish without a named reviewer.
- **Stale benefits are a compliance problem, not just a quality one.** Telling a
  member their specialist copay is $40 when the plan changed it to $50 is
  inaccurate material about their coverage. The catalog's staleness check exists
  for this and should never be worked around.

## Record keeping

Each plan spec carries `sob_source`, `sob_verified_on`, and `verified_by`; each
catalog entry carries `approved_by` and `approved_on`, plus the fingerprint of
the exact benefit set the audio was made from. Between them, any statement in
any episode can be traced to a document, a date, and a person.

Keep the generated kits in version control. If a member says "your podcast told
me the emergency room was free," you want to be able to produce the exact source
document that was used, as it existed on the day the audio was made.
