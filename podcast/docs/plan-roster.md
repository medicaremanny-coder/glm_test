# Plan roster — what gets an episode, and in what order

Each plan-year costs roughly fifteen minutes of transcription plus fifteen
minutes in NotebookLM, times two languages. That is the whole reason this file
exists: at about an hour a plan, the order matters, and "all of them" is not a
plan.

This file is the queue. Fill in the table, work top to bottom, and mark each row
off as its episode reaches `published`.

## Picking the order

Rank by **how many active members are actually on the plan**, not by how good
the plan is. The point of an episode is to stop the same benefit question from
arriving forty times; a plan with sixty members on it saves more calls than a
better plan with four.

Spark Advisors is the source of truth for the book — pull active clients grouped
by plan and take the counts from there. Two adjustments worth making by hand
before you commit to an order:

- **Weight D-SNP plans up.** Dual members get the most benefit from hearing the
  extras out loud (OTC card, transportation, dental), and they are the members
  least likely to read an eighty-page booklet.
- **Weight anything you are about to sell up.** A plan you expect to write
  volume on during AEP earns its episode before a plan you are only servicing.

## The queue

Leave `Plan ID` blank until you have read it off the SOB — the whole pipeline
keys on it, and a wrong contract-PBP means a correct episode filed under the
wrong plan. `Members` is the count from Spark on the date you filled the row.

| # | Carrier | Plan name | Plan ID | Type | Counties | Members | Status |
|---|---|---|---|---|---|---|---|
| 1 |  |  |  |  |  |  | not started |
| 2 |  |  |  |  |  |  | not started |
| 3 |  |  |  |  |  |  | not started |
| 4 |  |  |  |  |  |  | not started |
| 5 |  |  |  |  |  |  | not started |
| 6 |  |  |  |  |  |  | not started |
| 7 |  |  |  |  |  |  | not started |
| 8 |  |  |  |  |  |  | not started |

`Status` tracks the pipeline: `not started` → `scaffolded` → `filled` →
`recorded` → `approved` → `published`. After `scaffolded` the real state lives in
`catalog.json`; `python podcast/cli.py status` is authoritative and this column
is just a glance.

## Carriers to expect in Miami-Dade and Broward

A starting point for the names column, not a ranking and not a list of plans —
confirm every one of these against your own book before it earns a row, and get
the plan IDs from SunFire or the SOB rather than from here.

- Humana — including **CarePlus Health Plans** and the **Leon Medical Centers**
  plans, which behave like separate carriers to a member and need their own
  episodes
- UnitedHealthcare — including **Preferred Care Partners**
- Aetna
- Devoted Health
- Florida Blue / BlueMedicare
- Simply Healthcare
- Wellcare
- Molina Healthcare
- AvMed
- Freedom Health / Optimum HealthCare

## One episode per plan-year per county set

Benefits vary by county inside a single contract, and `PlanSpec.counties` exists
to make that visible. If a plan's Miami-Dade benefits differ from its Broward
benefits, that is two specs and two episodes, not one spec listing both counties.
Listing both when they differ is the mistake this section exists to prevent.

## Plan year

An episode is only true for the contract year it was transcribed from. A 2026
episode is wrong for a member enrolled in the 2027 version of the same plan, even
though the plan name and the contract-PBP have not changed.

So the roster resets every year:

- **2027 Summary of Benefits documents publish around October 1.** Nothing about
  a 2027 plan can be transcribed before then — the figures do not exist yet, and
  the CMS landscape files land shortly before.
- Before October, the useful work is deciding the order, scaffolding the specs
  from what you already know about the plans, and letting `build` sit at
  `BLOCKED` until the numbers arrive.
- Once the SOBs are out, filling a scaffold is the only step left, and it is
  mechanical.

Keep last year's specs. `catalog.json` fingerprints the benefits an episode was
built from, so a 2026 episode does not silently become a 2027 one — but the 2026
episode stays valid for as long as members are still enrolled in the 2026 plan,
which is through the end of that plan year.

## Adding a row to the pipeline

```
python podcast/cli.py new-plan \
    --plan-id H1036-001 \
    --name "Gold Plus" \
    --carrier "Humana" \
    --year 2026 \
    --type HMO \
    --county Miami-Dade
```

That writes `plans/h1036-001-2026.json` with every SOB line pre-labeled in both
languages and `[SOB]` wherever a figure belongs. Fill it against the Summary of
Benefits, delete the rows the plan does not offer, then `build`.
