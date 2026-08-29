#!/usr/bin/env python3
"""Map MedicareManny Plan Database rows to the official CMS MA/PD landscape.

CMS does not publish a live public REST API for the full landscape.
The official public source is the annual landscape file:

https://www.cms.gov/medicare/coverage/prescription-drug-coverage
Current file used here: CY2026 Landscape (202608)
https://www.cms.gov/files/zip/cy2026-landscape-202608.zip

CY2027 landscape is not public until mid-to-late September 2026.
Until that file exists, matches are historical 2026 CMS reference only —
not verified 2027 benefits.
"""

from __future__ import annotations

import argparse
import csv
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

TARGET_COUNTIES = {
    "Miami-Dade",
    "Miami Dade",
    "Broward",
    "Palm Beach",
    "Orange",
    "Osceola",
    "Seminole",
    "Polk",
    "Hillsborough",
    "Pasco",
    "Pinellas",
}

COUNTY_ALIASES = {
    "Miami Dade": "Miami-Dade",
    "Miami-Dade": "Miami-Dade",
}

# Official five-digit county FIPS. State prefix 12 = Florida.
COUNTY_FIPS = {
    "Broward": "12011",
    "Hillsborough": "12057",
    "Miami-Dade": "12086",
    "Orange": "12095",
    "Osceola": "12097",
    "Palm Beach": "12099",
    "Pasco": "12101",
    "Pinellas": "12103",
    "Polk": "12105",
    "Seminole": "12117",
}

CMS_ZIP_URL = "https://www.cms.gov/files/zip/cy2026-landscape-202608.zip"
CMS_SOURCE_PAGE = "https://www.cms.gov/medicare/coverage/prescription-drug-coverage"
CMS_FILE_LABEL = "CY2026 Landscape (202608)"
CMS_DATASET = "CY2026_Landscape"
CMS_SOURCE_VERSION = "202608"
CMS_UPDATED = "2026-08-10"
BENEFIT_YEAR = 2026
TARGET_PLAN_YEAR = 2027
MAPPED_ON = "2026-08-28"

VERIFICATION_HISTORICAL = "historical_2026"
VERIFICATION_UNMATCHED = "unmatched_historical"
VERIFICATION_PRELIMINARY = "preliminary_2027"
VERIFICATION_VERIFIED = "verified_2027"

CSV_FIELDS = [
    "county",
    "county_fips",
    "plan_type",
    "carrier",
    "workbook_plan_name",
    "plan_number",
    "contract_id",
    "pbp_id",
    "segment_id",
    "segment_explicit",
    "contract_pbp",
    "benefit_year",
    "target_plan_year",
    "verification_class",
    "match_status",
    "cms_contract_id",
    "cms_pbp_id",
    "cms_segment_id",
    "cms_plan_name",
    "cms_org",
    "cms_plan_type",
    "cms_snp_type",
    "cms_premium",
    "cms_moop",
    "cms_overall_stars",
    "cms_sanctioned",
    "cms_county",
    "source_dataset",
    "source_version",
    "source_url",
    "source_page",
    "source_updated",
    "mapped_on",
    "benefit_year_status",
]


def normalize_county(name: str) -> str:
    name = (name or "").strip()
    return COUNTY_ALIASES.get(name, name)


def county_fips(name: str) -> str:
    return COUNTY_FIPS.get(normalize_county(name), "")


def parse_plan_number(plan_number: str) -> dict:
    raw = (plan_number or "").strip().upper()
    if not raw or raw.startswith("PENDING"):
        return {
            "raw": raw,
            "contract": "",
            "pbp": "",
            "segment": "",
            "segment_explicit": False,
            "key": "",
            "segment_key": "",
        }
    parts = [p for p in raw.replace("_", "-").split("-") if p]
    contract = parts[0] if parts else ""
    pbp = parts[1].zfill(3) if len(parts) > 1 else ""
    segment_explicit = len(parts) > 2
    segment = (parts[2].lstrip("0") or "0") if segment_explicit else "0"
    return {
        "raw": raw,
        "contract": contract,
        "pbp": pbp,
        "segment": segment,
        "segment_explicit": segment_explicit,
        "key": f"{contract}{pbp}",
        "segment_key": f"{contract}{pbp}{segment}",
    }


def load_workbook_plans(path: Path) -> list[dict]:
    payload = json.loads(path.read_text())
    values = payload["values"]
    header, rows = values[0], values[1:]
    plans = []
    for idx, row in enumerate(rows, start=4):
        rec = {header[i]: (row[i] if i < len(row) else "") for i in range(len(header))}
        parsed = parse_plan_number(str(rec.get("Plan Number", "")))
        rec["_row"] = idx
        rec.update({f"_{k}": v for k, v in parsed.items()})
        rec["County"] = normalize_county(str(rec.get("County", "")))
        if rec.get("Plan Number"):
            plans.append(rec)
    return plans


def iter_florida_landscape(zip_path: Path):
    with zipfile.ZipFile(zip_path) as zf:
        csv_name = next(n for n in zf.namelist() if n.endswith(".csv"))
        with zf.open(csv_name) as raw:
            yield from iter_landscape_rows(line.decode("utf-8-sig") for line in raw)


def iter_landscape_rows(lines) -> list[dict]:
    reader = csv.DictReader(lines)
    rows = []
    for row in reader:
        if row.get("State Territory Abbreviation") not in {None, "", "FL"}:
            continue
        county = normalize_county(row.get("County Name", ""))
        if county not in TARGET_COUNTIES:
            continue
        parsed = parse_plan_number(
            f"{row.get('Contract ID', '')}-{row.get('Plan ID', '')}-{row.get('Segment ID', '0')}"
        )
        row["_county"] = county
        row["_key"] = parsed["key"]
        row["_segment_key"] = parsed["segment_key"]
        row["_contract"] = parsed["contract"]
        row["_pbp"] = parsed["pbp"]
        row["_segment"] = parsed["segment"]
        rows.append(row)
    return rows


def verification_for(status: str) -> str:
    if status == "Pending official 2027 plan ID":
        return VERIFICATION_PRELIMINARY
    if status == "Not in CY2026 landscape":
        return VERIFICATION_UNMATCHED
    if status.startswith("CMS 2026"):
        return VERIFICATION_HISTORICAL
    raise ValueError(f"Unmapped match status: {status}")


def match(plans: list[dict], landscape_rows: list[dict]) -> dict:
    by_key_county = defaultdict(list)
    by_key = defaultdict(list)
    by_segment_county = defaultdict(list)
    for row in landscape_rows:
        by_key_county[(row["_key"], row["_county"])].append(row)
        by_key[row["_key"]].append(row)
        by_segment_county[(row["_segment_key"], row["_county"])].append(row)

    matches = []
    for plan in plans:
        county = plan["County"]
        key = plan["_key"]
        segment_key = plan.get("_segment_key", "")
        raw = plan.get("_raw", "")
        if raw.startswith("PENDING") or not key:
            status = "Pending official 2027 plan ID"
            cms = None
        elif by_segment_county.get((segment_key, county)):
            status = "CMS 2026 county + segment match"
            cms = by_segment_county[(segment_key, county)][0]
        elif by_key_county.get((key, county)):
            status = "CMS 2026 county match"
            cms = by_key_county[(key, county)][0]
        elif by_key.get(key):
            status = "CMS 2026 contract/PBP match — county differs"
            cms = by_key[key][0]
        else:
            status = "Not in CY2026 landscape"
            cms = None
        verification_class = verification_for(status)
        matches.append(
            {
                "workbook_row": plan["_row"],
                "county": county,
                "county_fips": county_fips(county),
                "plan_type": plan.get("Plan Type", ""),
                "carrier": plan.get("Carrier", ""),
                "workbook_plan_name": plan.get("Plan Name", ""),
                "plan_number": plan.get("Plan Number", ""),
                "contract_id": plan.get("_contract", ""),
                "pbp_id": plan.get("_pbp", ""),
                "segment_id": plan.get("_segment", ""),
                "segment_explicit": bool(plan.get("_segment_explicit")),
                "contract_pbp": key,
                "benefit_year": BENEFIT_YEAR,
                "target_plan_year": TARGET_PLAN_YEAR,
                "verification_class": verification_class,
                "match_status": status,
                "cms_contract_id": (cms or {}).get("_contract") or (cms or {}).get("Contract ID", ""),
                "cms_pbp_id": (cms or {}).get("_pbp") or "",
                "cms_segment_id": (cms or {}).get("_segment") or "",
                "cms_plan_name": (cms or {}).get("Plan Name", ""),
                "cms_org": (cms or {}).get("Organization Marketing Name", ""),
                "cms_plan_type": (cms or {}).get("Plan Type", ""),
                "cms_snp_type": (cms or {}).get("SNP Type", ""),
                "cms_premium": (cms or {}).get("Monthly Consolidated Premium (Part C + D)", ""),
                "cms_moop": (cms or {}).get("In-Network Maximum Out-of-Pocket (MOOP) Amount", ""),
                "cms_part_c_premium": (cms or {}).get("Part C Premium", ""),
                "cms_overall_stars": (cms or {}).get("Overall Star Rating", ""),
                "cms_sanctioned": (cms or {}).get("Sanctioned Plan", ""),
                "cms_county": (cms or {}).get("_county", ""),
                "source_dataset": CMS_DATASET,
                "source_version": CMS_SOURCE_VERSION,
                "source_url": CMS_ZIP_URL,
                "source_page": CMS_SOURCE_PAGE,
                "source_updated": CMS_UPDATED,
                "mapped_on": MAPPED_ON,
                "benefit_year_status": "Historical 2026 CMS reference only — not verified 2027 benefits",
            }
        )
    return {
        "source": source_block(),
        "summary": summarize(matches),
        "matches": matches,
    }


def source_block() -> dict:
    return {
        "dataset": CMS_DATASET,
        "label": CMS_FILE_LABEL,
        "version": CMS_SOURCE_VERSION,
        "url": CMS_ZIP_URL,
        "page": CMS_SOURCE_PAGE,
        "cms_updated": CMS_UPDATED,
        "benefit_year": BENEFIT_YEAR,
        "target_plan_year": TARGET_PLAN_YEAR,
        "mapped_on": MAPPED_ON,
        "note": "CY2027 landscape is not public until mid-to-late September 2026. Historical 2026 matches are not verified 2027 benefits.",
    }


def summarize(matches: list[dict]) -> dict:
    counts = Counter(m["match_status"] for m in matches)
    classes = Counter(m["verification_class"] for m in matches)
    unique_ids = {m["plan_number"] for m in matches}
    unmatched_ids = {
        m["plan_number"]
        for m in matches
        if m["verification_class"] in {VERIFICATION_UNMATCHED, VERIFICATION_PRELIMINARY}
    }
    return {
        "workbook_rows": len(matches),
        "unique_plan_numbers": len(unique_ids),
        "segment_explicit_rows": sum(1 for m in matches if m["segment_explicit"]),
        "status_counts": dict(counts),
        "verification_class_counts": dict(classes),
        "unmatched_plan_numbers": sorted(unmatched_ids),
    }


def write_outputs(result: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cms-match-2026.json").write_text(json.dumps(result, indent=2))
    csv_path = out_dir / "cms-match-2026.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(result["matches"])
    (out_dir / "cms-match-2026-summary.json").write_text(
        json.dumps({"source": result["source"], "summary": result["summary"]}, indent=2)
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook-json", required=True)
    parser.add_argument("--landscape-zip", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    plans = load_workbook_plans(Path(args.workbook_json))
    landscape = list(iter_florida_landscape(Path(args.landscape_zip)))
    result = match(plans, landscape)
    write_outputs(result, Path(args.out_dir))
    print(json.dumps({"source": result["source"], "summary": result["summary"], "landscape_fl_rows": len(landscape)}, indent=2))


if __name__ == "__main__":
    main()
