# Decisions

## 2026-08-29 — Cursor is engine room, Codex owns the live tool

Cursor stays on CMS imports, matching, schemas, CSV/JSON, tests, GitHub Actions, and discrepancy detection.

Codex owns Home, Compare, Reference, Carrier Resources, Sheets formatting, dropdowns, carrier headers, colors, hyperlinks, and saved-state readback.

Cursor does not edit Home, Compare, Reference, or Carrier Resources unless explicitly assigned. Only one agent edits the live workbook at a time.

Obsidian, Notion, Calendar, Gmail, and Granola are unchanged by this split.

## 2026-08-29 — Home stays compact

Codex continues the visual Home design. Cursor adds a thin Agent Intelligence Bar and dedicated tabs instead of more large Home cards.

Detailed eligibility, intake, year-over-year changes, and the audit trail do not belong on Home.

## 2026-08-29 — Sheet is the interface, repo is the brain

The Google Sheet remains the MVP agents use during calls. Structured JSON in `data/` is the long-term source of truth so the same verified dataset can later feed Sheets, Excel, and a web app.

## 2026-08-29 — No invented 2027 benefits

Until official 2027 Summaries of Benefits are verified, 2027 change rows stay `PENDING`. The Intelligence Bar shows Carrier Preview / Pending CMS, not Official SOB.

## 2026-08-29 — MARx is not for sale

MARx is a CMS role-based system. Independent agents use MyACCESS, SSA Extra Help, carrier portals, and SHINE. A MARx mention is “authorized plan users only.”
