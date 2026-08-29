# MedicareManny 2027 Comparison Engine

South Florida Medicare plan intelligence for working agents.

This repository is the permanent project home. The live Google Sheet is the current agent interface.

**Workbook:** [MedicareManny 2027 Florida Plan Comparison Engine](https://docs.google.com/spreadsheets/d/1WCuS2bKtIyEyJjGNTv2cLBieKpYYmzxWa3qBLY4_EfY/edit)

## Status

Draft build for 2027. Comparison grids still carry verified 2026 Summary of Benefits values until official 2027 documents replace them. Do not present draft 2027 figures as final.

## Agent interface

| Tab | Purpose |
| --- | --- |
| Home | Navigation, Agent Intelligence Bar, alerts |
| Compare | County + plan-type comparison |
| Call Checklist | Client-call intake without storing SSN/MBI |
| Eligibility Center | MyACCESS, Extra Help, Medicare eligibility |
| What Changed 2027 | 2026→2027 change detector (pending official SOB) |
| Update Log | Dated corrections, SOB links, discrepancy queue |
| County grids / Plan Database / Hospitals / Carrier Resources | Existing comparison and reference |

## Rules

Read `AGENTS.md` and `.cursor/rules/` before changing benefits, Home, or verification status.

## Data

Structured JSON in `data/` is the long-term source of truth. The Sheet should be updated from that data, not the other way around.

---

## Legacy glm_test utilities

This GitHub repository originally held small Python utilities (`url_shortener.py`, `calculate_sum.py`). Those files remain for history. New MedicareManny work should not depend on them.
