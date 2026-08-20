import json
from pathlib import Path

import pytest

from planspec import (
    CATEGORY_ORDER,
    TRANSLATION_MARKER,
    Benefit,
    PlanSpec,
    PlanSpecError,
    category_label,
    load_all,
)

EXAMPLE = Path(__file__).resolve().parent / "plans" / "example-h1234-001-2026.json"


def minimal_spec_dict(**overrides):
    data = {
        "plan_id": "H1234-001",
        "plan_name": "Example Advantage Plus",
        "carrier": "Example Health",
        "plan_year": 2026,
        "plan_type": "HMO",
        "counties": ["Miami-Dade"],
        "sob_source": "example-sob.pdf p.4",
        "sob_verified_on": "2026-08-11",
        "verified_by": "Manny Leon",
        "disclaimer_en": "Example disclaimer.",
        "disclaimer_es": "Aviso de ejemplo.",
        "benefits": [
            {
                "name": "Monthly plan premium",
                "category": "money",
                "member_cost": "$0",
                "name_es": "Prima mensual del plan",
            }
        ],
    }
    data.update(overrides)
    return data


class TestBenefit:
    def test_requires_a_known_category(self):
        with pytest.raises(PlanSpecError, match="category must be one of"):
            Benefit(name="Dental", category="dentalish", member_cost="$0")

    def test_requires_a_cost_for_priced_categories(self):
        with pytest.raises(PlanSpecError, match="member_cost is required"):
            Benefit(name="Specialist visit", category="care")

    def test_rules_may_omit_cost_but_need_a_detail(self):
        rule = Benefit(
            name="Network only",
            category="rules",
            detail="Out-of-network care is not covered except in an emergency",
        )
        assert rule.member_cost == ""

        with pytest.raises(PlanSpecError, match="detail is required for 'rules'"):
            Benefit(name="Network only", category="rules")

    def test_english_fields_pass_through(self):
        benefit = Benefit(
            name="Specialist visit",
            category="care",
            member_cost="$40 copay",
            detail="Referral required",
        )
        assert benefit.localized("en") == {
            "name": "Specialist visit",
            "member_cost": "$40 copay",
            "detail": "Referral required",
        }

    def test_language_neutral_costs_need_no_translation(self):
        benefit = Benefit(
            name="Primary care", category="care", member_cost="$0", name_es="Medico"
        )
        assert benefit.missing_translations() == []
        assert benefit.localized("es")["member_cost"] == "$0"

    def test_costs_containing_words_must_be_translated(self):
        benefit = Benefit(
            name="Specialist visit",
            category="care",
            member_cost="$40 copay",
            name_es="Especialista",
        )
        assert "member_cost_es" in benefit.missing_translations()
        assert TRANSLATION_MARKER in benefit.localized("es")["member_cost"]

    def test_untranslated_spanish_never_falls_back_to_english(self):
        """The failure mode this guards: a Spanish episode quietly reciting
        English cost-sharing because a translation was missing."""
        benefit = Benefit(name="Hearing aids", category="extras", member_cost="$699 each")
        spanish = benefit.localized("es")
        assert spanish["name"].startswith(TRANSLATION_MARKER)
        assert spanish["member_cost"].startswith(TRANSLATION_MARKER)

    def test_empty_detail_is_not_flagged_as_untranslated(self):
        benefit = Benefit(
            name="Primary care", category="care", member_cost="$0", name_es="Medico"
        )
        assert benefit.localized("es")["detail"] == ""
        assert "detail_es" not in benefit.missing_translations()

    def test_rejects_unknown_language(self):
        benefit = Benefit(name="Premium", category="money", member_cost="$0")
        with pytest.raises(PlanSpecError, match="Unsupported language"):
            benefit.localized("fr")


class TestPlanSpec:
    def test_round_trips_through_dict(self):
        spec = PlanSpec.from_dict(minimal_spec_dict())
        assert PlanSpec.from_dict(spec.to_dict()).to_dict() == spec.to_dict()

    def test_slug_and_display_name(self):
        spec = PlanSpec.from_dict(minimal_spec_dict())
        assert spec.slug() == "h1234-001-2026"
        assert "H1234-001" in spec.display_name()
        assert "2026" in spec.display_name()

    @pytest.mark.parametrize(
        "plan_id", ["H1234001", "1234-001", "H123-001", "H1234-01", "Z1234-001", ""]
    )
    def test_rejects_malformed_plan_ids(self, plan_id):
        with pytest.raises(PlanSpecError, match="plan_id"):
            PlanSpec.from_dict(minimal_spec_dict(plan_id=plan_id))

    @pytest.mark.parametrize("plan_id", ["H1234-001", "R5678-002", "S9999-123", "E1111-000"])
    def test_accepts_every_cms_contract_prefix(self, plan_id):
        assert PlanSpec.from_dict(minimal_spec_dict(plan_id=plan_id)).plan_id == plan_id

    def test_requires_at_least_one_county(self):
        with pytest.raises(PlanSpecError, match="counties"):
            PlanSpec.from_dict(minimal_spec_dict(counties=[]))

    def test_requires_at_least_one_benefit(self):
        with pytest.raises(PlanSpecError, match="benefits"):
            PlanSpec.from_dict(minimal_spec_dict(benefits=[]))

    def test_requires_iso_verification_date(self):
        with pytest.raises(PlanSpecError, match="sob_verified_on"):
            PlanSpec.from_dict(minimal_spec_dict(sob_verified_on="08/11/2026"))

    def test_rejects_unknown_fields(self):
        with pytest.raises(PlanSpecError, match="Unknown plan spec field"):
            PlanSpec.from_dict(minimal_spec_dict(premium="$0"))

    def test_reports_missing_required_fields_clearly(self):
        data = minimal_spec_dict()
        del data["carrier"]
        with pytest.raises(PlanSpecError, match="carrier"):
            PlanSpec.from_dict(data)

    def test_groups_benefits_in_listening_order(self):
        data = minimal_spec_dict(
            benefits=[
                {
                    "name": "Network only",
                    "category": "rules",
                    "detail": "Emergencies excepted",
                },
                {"name": "Tier 1 drugs", "category": "drugs", "member_cost": "$0"},
                {"name": "Premium", "category": "money", "member_cost": "$0"},
            ]
        )
        spec = PlanSpec.from_dict(data)
        assert [c for c, _ in spec.by_category()] == ["money", "drugs", "rules"]

    def test_empty_categories_are_dropped(self):
        spec = PlanSpec.from_dict(minimal_spec_dict())
        categories = [c for c, _ in spec.by_category()]
        assert categories == ["money"]
        assert len(categories) < len(CATEGORY_ORDER)

    def test_english_is_always_ready(self):
        data = minimal_spec_dict(
            benefits=[{"name": "Hearing aids", "category": "extras", "member_cost": "$699 each"}]
        )
        spec = PlanSpec.from_dict(data)
        assert spec.ready_for("en")
        assert not spec.ready_for("es")

    def test_untranslated_report_names_the_benefit(self):
        data = minimal_spec_dict(
            benefits=[{"name": "Hearing aids", "category": "extras", "member_cost": "$699 each"}]
        )
        gaps = PlanSpec.from_dict(data).untranslated()
        assert any("Hearing aids" in gap and "name_es" in gap for gap in gaps)

    def test_missing_spanish_disclaimer_blocks_spanish(self):
        with pytest.raises(PlanSpecError, match="disclaimer_es"):
            PlanSpec.from_dict(minimal_spec_dict(disclaimer_es="  "))

    def test_save_and_load(self, tmp_path):
        spec = PlanSpec.from_dict(minimal_spec_dict())
        path = spec.save(tmp_path / "nested" / "plan.json")
        assert PlanSpec.load(path).to_dict() == spec.to_dict()

    def test_load_reports_bad_json_with_the_path(self, tmp_path):
        bad = tmp_path / "broken.json"
        bad.write_text("{not json", encoding="utf-8")
        with pytest.raises(PlanSpecError, match="broken.json"):
            PlanSpec.load(bad)

    def test_load_reports_missing_file(self, tmp_path):
        with pytest.raises(PlanSpecError, match="not found"):
            PlanSpec.load(tmp_path / "nope.json")


class TestShippedExample:
    def test_example_plan_parses(self):
        spec = PlanSpec.load(EXAMPLE)
        assert spec.slug() == "h1234-001-2026"

    def test_example_plan_is_fully_translated(self):
        """The shipped example is what people copy. If it has translation gaps,
        every plan cloned from it starts with them too."""
        assert PlanSpec.load(EXAMPLE).untranslated() == []

    def test_example_plan_is_labelled_as_fake(self):
        spec = PlanSpec.load(EXAMPLE)
        assert "EXAMPLE" in spec.sob_source

    def test_load_all_finds_it(self):
        specs = load_all(EXAMPLE.parent)
        assert any(s.slug() == "h1234-001-2026" for s in specs)

    def test_load_all_rejects_a_file(self):
        with pytest.raises(PlanSpecError, match="Not a directory"):
            load_all(EXAMPLE)


def test_every_category_has_labels_in_every_language():
    for category in CATEGORY_ORDER:
        for lang in ("en", "es"):
            assert category_label(category, lang).strip()
