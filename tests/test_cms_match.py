#!/usr/bin/env python3
"""Automated checks for CMS landscape matching.

These tests are the production-backbone gate. They must keep historical 2026
matches separate from preliminary or verified 2027 data.
"""

from __future__ import annotations

import csv
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import map_cms_landscape as cms  # noqa: E402

WORKBOOK = ROOT / "data" / "plans" / "workbook-plan-ids-2026-08-28.json"
CSV_PATH = ROOT / "data" / "cms" / "cms-match-2026.csv"
SUMMARY = ROOT / "data" / "cms" / "cms-match-2026-summary.json"
SCHEMA = ROOT / "data" / "cms" / "schema.json"
MINI_WORKBOOK = ROOT / "tests" / "fixtures" / "cms" / "mini_workbook.json"
MINI_LANDSCAPE = ROOT / "tests" / "fixtures" / "cms" / "mini_landscape.csv"


class ParsePlanNumberTests(unittest.TestCase):
    def test_two_part_defaults_segment_zero(self):
        parsed = cms.parse_plan_number("H1036-305")
        self.assertEqual(parsed["contract"], "H1036")
        self.assertEqual(parsed["pbp"], "305")
        self.assertEqual(parsed["segment"], "0")
        self.assertFalse(parsed["segment_explicit"])

    def test_three_part_keeps_segment(self):
        parsed = cms.parse_plan_number("H1032-244-001")
        self.assertEqual(parsed["contract"], "H1032")
        self.assertEqual(parsed["pbp"], "244")
        self.assertEqual(parsed["segment"], "1")
        self.assertTrue(parsed["segment_explicit"])

    def test_pending_has_no_contract(self):
        parsed = cms.parse_plan_number("Pending official 2027 plan ID")
        self.assertEqual(parsed["contract"], "")
        self.assertEqual(parsed["key"], "")


class CountyFipsTests(unittest.TestCase):
    def test_south_florida_fips(self):
        self.assertEqual(cms.county_fips("Miami-Dade"), "12086")
        self.assertEqual(cms.county_fips("Miami Dade"), "12086")
        self.assertEqual(cms.county_fips("Broward"), "12011")
        self.assertEqual(cms.county_fips("Palm Beach"), "12099")


class FixtureMatchTests(unittest.TestCase):
    def setUp(self):
        plans = cms.load_workbook_plans(MINI_WORKBOOK)
        landscape = cms.iter_landscape_rows(MINI_LANDSCAPE.read_text().splitlines())
        self.result = cms.match(plans, landscape)
        self.by_number = {row["plan_number"]: row for row in self.result["matches"]}

    def test_exact_county_segment_match_is_historical(self):
        row = self.by_number["H1036-305"]
        self.assertEqual(row["contract_id"], "H1036")
        self.assertEqual(row["pbp_id"], "305")
        self.assertEqual(row["segment_id"], "0")
        self.assertEqual(row["county_fips"], "12086")
        self.assertEqual(row["benefit_year"], 2026)
        self.assertEqual(row["target_plan_year"], 2027)
        self.assertEqual(row["verification_class"], cms.VERIFICATION_HISTORICAL)
        self.assertNotEqual(row["verification_class"], cms.VERIFICATION_VERIFIED)

    def test_explicit_segment_matches_cms_segment(self):
        row = self.by_number["H1032-244-001"]
        self.assertTrue(row["segment_explicit"])
        self.assertEqual(row["segment_id"], "1")
        self.assertEqual(row["cms_segment_id"], "1")
        self.assertEqual(row["match_status"], "CMS 2026 county + segment match")
        self.assertEqual(row["verification_class"], cms.VERIFICATION_HISTORICAL)

    def test_missing_landscape_row_is_unmatched_historical(self):
        row = self.by_number["H4140-023"]
        self.assertEqual(row["verification_class"], cms.VERIFICATION_UNMATCHED)
        self.assertEqual(row["cms_plan_name"], "")

    def test_pending_id_is_preliminary_2027(self):
        row = self.by_number["Pending official 2027 plan ID"]
        self.assertEqual(row["verification_class"], cms.VERIFICATION_PRELIMINARY)
        self.assertEqual(row["contract_id"], "")


class ProductionCsvTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA.read_text())
        with CSV_PATH.open() as f:
            cls.rows = list(csv.DictReader(f))
        cls.summary = json.loads(SUMMARY.read_text())
        cls.workbook = json.loads(WORKBOOK.read_text())["values"][1:]

    def test_required_fields_present(self):
        missing = [field for field in self.schema["required_fields"] if field not in self.rows[0]]
        self.assertEqual(missing, [])

    def test_reconciled_counts(self):
        counts = Counter(row["match_status"] for row in self.rows)
        self.assertEqual(len(self.rows), 724)
        self.assertEqual(len({row["plan_number"] for row in self.rows}), 276)
        self.assertEqual(counts["CMS 2026 county + segment match"], 693)
        self.assertEqual(counts["Not in CY2026 landscape"], 28)
        self.assertEqual(counts["Pending official 2027 plan ID"], 3)

    def test_seventy_explicit_segments(self):
        workbook_segmented = sum(
            1
            for row in self.workbook
            if len(row) > 4 and str(row[4]).count("-") >= 2
        )
        csv_segmented = sum(1 for row in self.rows if row["segment_explicit"] == "True")
        self.assertEqual(workbook_segmented, 70)
        self.assertEqual(csv_segmented, 70)

    def test_split_ids_not_only_contract_pbp(self):
        sample = next(row for row in self.rows if row["plan_number"] == "H1036-305")
        self.assertEqual(sample["contract_id"], "H1036")
        self.assertEqual(sample["pbp_id"], "305")
        self.assertEqual(sample["segment_id"], "0")
        self.assertEqual(sample["contract_pbp"], "H1036305")

    def test_segmented_row_exposes_segment_id(self):
        sample = next(row for row in self.rows if row["plan_number"] == "H1032-244-001")
        self.assertEqual(sample["contract_id"], "H1032")
        self.assertEqual(sample["pbp_id"], "244")
        self.assertEqual(sample["segment_id"], "1")
        self.assertEqual(sample["county_fips"], "12086")

    def test_no_verified_2027_labels(self):
        verified = [row["plan_number"] for row in self.rows if row["verification_class"] == cms.VERIFICATION_VERIFIED]
        self.assertEqual(verified, [])
        self.assertTrue(
            all("not verified 2027" in row["benefit_year_status"].lower() for row in self.rows)
        )

    def test_source_version_fields(self):
        sample = self.rows[0]
        self.assertEqual(sample["benefit_year"], "2026")
        self.assertEqual(sample["target_plan_year"], "2027")
        self.assertEqual(sample["source_dataset"], "CY2026_Landscape")
        self.assertEqual(sample["source_version"], "202608")
        self.assertEqual(sample["source_updated"], "2026-08-10")
        self.assertTrue(sample["source_url"].endswith("cy2026-landscape-202608.zip"))

    def test_all_known_counties_have_fips(self):
        missing = [row["county"] for row in self.rows if len(row["county_fips"]) != 5]
        self.assertEqual(missing, [])

    def test_summary_matches_csv(self):
        summary = self.summary["summary"]
        self.assertEqual(summary["workbook_rows"], 724)
        self.assertEqual(summary["unique_plan_numbers"], 276)
        self.assertEqual(summary["segment_explicit_rows"], 70)


if __name__ == "__main__":
    unittest.main()
