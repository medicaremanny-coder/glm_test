# MedicareManny 2027 Florida Plan Comparison

## Mission

Build and maintain an agent-ready comparison system for 2027 Florida Medicare Advantage plans.

This repository is the software and data brain. The live Google Sheet is an interface, not the source of truth.

Primary market:

- Miami-Dade
- Broward
- Palm Beach

Secondary market:

- Central Florida (Orange, Osceola, Seminole, Polk, Hillsborough, Pasco, Pinellas)

## Source of Truth

Never invent Medicare benefits.

Priority:

1. Official carrier Summary of Benefits
2. Evidence of Coverage
3. Carrier producer portal / document
4. Official CMS MA/PD landscape file (not a public live REST API; CY2027 due mid-to-late September)
5. Verified provider / network sources

If information cannot be verified, mark it `UNVERIFIED` or `PENDING`.
Never convert preliminary 2027 information into a verified benefit.

## Live workbook

Google Sheet: [MedicareManny 2027 Florida Plan Comparison Engine](https://docs.google.com/spreadsheets/d/1WCuS2bKtIyEyJjGNTv2cLBieKpYYmzxWa3qBLY4_EfY/edit)

Home stays compact: navigation, verification status, and current alerts.
Detailed material belongs in dedicated tabs.

## Plan Data

Track at minimum:

- Carrier, plan name, contract_id, pbp_id, segment_id, county, county FIPS, plan type
- benefit_year, target_plan_year, verification_class, source dataset/version
- Premium, Part B giveback, MOOP
- PCP, specialist, hospital, ER, urgent care, MRI/CT, labs
- Dental, vision, hearing, OTC, food/utilities, transportation, Part D
- Network notes, hospital participation
- Verification status, source URL/document, last verified date

## Comparison Rules

Never compare plans from different counties as though they are directly interchangeable.

Always preserve plan year, county, contract, PBP, benefit source, and verification date.

## MedicareManny Workflow

When new 2027 documents arrive:

1. Identify carrier / plan / contract / PBP / county.
2. Extract benefits.
3. Compare against existing data.
4. Flag discrepancies.
5. Update the verification log.
6. Update comparison data.
7. Never overwrite verified data without recording the change.

## Compliance

This system assists the agent. It does not replace:

- current Summary of Benefits
- Evidence of Coverage
- formulary
- provider directory
- carrier enrollment systems

Client-facing comparisons must use verified current plan information.
Do not store SSN, MBI, DOB, or other sensitive member identifiers in this repo or the workbook.
