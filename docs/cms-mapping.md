# CMS landscape mapping

CMS does not publish a public live REST API for the full Medicare Advantage landscape. The official public source is the annual landscape file on:

https://www.cms.gov/medicare/coverage/prescription-drug-coverage

## Current file

- CY2026 Landscape (202608)
- https://www.cms.gov/files/zip/cy2026-landscape-202608.zip
- CMS last updated 2026-08-10
- Mapped 2026-08-28

CY2027 landscape is not public until mid-to-late September 2026. Until then, every CMS match is **historical 2026 reference only — not a verified 2027 benefit**.

The HPMS PBP API is for authorized plan/consultant users, not independent agents.

## How matching works

Workbook plan numbers such as `H1036-305` or `H1032-244-001` are parsed into contract, PBP, and segment, then matched to CMS `Contract ID` + `Plan ID` + `Segment ID` in the target Florida counties.

Re-run:

```bash
python3 scripts/map_cms_landscape.py \
  --workbook-json data/plans/workbook-plan-ids-2026-08-28.json \
  --landscape-zip /path/to/cy2026-landscape-202608.zip \
  --out-dir data/cms
```

When the 2027 ZIP is published, point `--landscape-zip` at that file. Do not mark Official SOB / Official CMS 2027 until that import succeeds and the SOB is attached.

## First mapping result

- 724 workbook rows with a plan number
- 693 CMS 2026 county + segment matches
- 28 not in the CY2026 landscape (Doctors H4140-020 through 026, Simply H4571-075)
- 3 pending official 2027 plan IDs (Solis Balanced Plan)

Those unmatched IDs may be 2027-only, mistyped, or not yet in the public landscape. Do not invent a CMS match for them.
