import json
from pathlib import Path

import pytest

from episode import build_kit
from planspec import (
    CATEGORY_ORDER,
    SOB_PLACEHOLDER as PLANSPEC_PLACEHOLDER,
    TRANSLATION_MARKER,
    PlanSpec,
    PlanSpecError,
)
from skeleton import (
    DEFAULT_DISCLAIMER_EN,
    DEFAULT_DISCLAIMER_ES,
    SOB_PLACEHOLDER,
    blank_spec,
    skeleton_rows,
)

EXAMPLE = Path(__file__).resolve().parent / "plans" / "example-h1234-001-2026.json"

FIELDS = {
    "plan_id": "H1036-001",
    "plan_name": "Gold Plus",
    "carrier": "Humana",
    "plan_year": 2026,
    "plan_type": "HMO",
    "counties": ["Miami-Dade"],
    "verified_by": "Manny Leon",
    "verified_on": "2026-08-11",
}


def make(**overrides):
    return blank_spec(**{**FIELDS, **overrides})


# --- the scaffold is a valid spec -------------------------------------------


def test_blank_spec_is_valid_and_identifies_itself():
    spec = make()
    assert spec.slug() == "h1036-001-2026"
    assert spec.display_name() == "Humana Gold Plus (H1036-001, 2026)"


def test_blank_spec_round_trips_through_disk(tmp_path):
    path = make().save(tmp_path / "h1036-001-2026.json")
    reloaded = PlanSpec.load(path)
    assert reloaded.slug() == "h1036-001-2026"
    assert len(reloaded.benefits) == len(skeleton_rows())


def test_blank_spec_validates_plan_id_like_any_other_spec():
    with pytest.raises(PlanSpecError, match="plan_id"):
        make(plan_id="not-a-plan")


def test_blank_spec_validates_the_verification_date():
    with pytest.raises(PlanSpecError, match="sob_verified_on"):
        make(verified_on="8/11/2026")


def test_counties_are_copied_not_aliased():
    counties = ["Miami-Dade"]
    spec = make(counties=counties)
    counties.append("Broward")
    assert spec.counties == ["Miami-Dade"]


# --- and it is deliberately not ready ---------------------------------------


def test_scaffold_is_not_ready_for_spanish():
    assert make().ready_for("es") is False


def test_every_priced_row_starts_as_a_placeholder():
    for benefit in make().benefits:
        if benefit.category == "rules":
            assert benefit.member_cost == ""
        else:
            assert benefit.member_cost == SOB_PLACEHOLDER


def test_placeholder_is_reported_as_an_untranslated_cost():
    # The placeholder must not read as language-neutral: if it did, a scaffold
    # would build clean and could be recorded with no numbers in it.
    gaps = make().untranslated()
    assert any("member_cost_es" in gap for gap in gaps)


def test_placeholder_surfaces_in_spanish_output_as_a_marker():
    priced = [b for b in make().benefits if b.category != "rules"]
    localized = priced[0].localized("es")
    assert TRANSLATION_MARKER in localized["member_cost"]


def test_sob_source_is_a_placeholder_so_provenance_cannot_be_skipped():
    assert SOB_PLACEHOLDER in make().sob_source


def test_notes_mark_the_file_as_a_scaffold():
    assert "SCAFFOLD" in make().notes


# --- what is pre-filled is only ever a label --------------------------------


def test_priced_rows_ship_with_their_spanish_name_written():
    for benefit in make().benefits:
        if benefit.category != "rules":
            assert benefit.name_es, f"{benefit.name} is missing name_es"


def test_no_priced_row_carries_a_pre_filled_spanish_cost_or_detail():
    for benefit in make().benefits:
        assert benefit.member_cost_es is None
        assert benefit.detail_es is None


def test_rules_rows_do_not_assert_facts_about_the_plan():
    # Whether a referral is required is plan-specific, so a rules row has to be
    # rewritten rather than accepted as written.
    rules = [b for b in make().benefits if b.category == "rules"]
    assert rules
    for benefit in rules:
        assert SOB_PLACEHOLDER in benefit.name
        assert SOB_PLACEHOLDER in benefit.detail
        assert benefit.name_es is None


def test_disclaimers_are_populated_so_the_spec_validates():
    spec = make()
    assert spec.disclaimer_en == DEFAULT_DISCLAIMER_EN
    assert spec.disclaimer_es == DEFAULT_DISCLAIMER_ES


# --- shape of the row set ----------------------------------------------------


def test_rows_cover_every_category():
    categories = {b.category for b in make().benefits}
    assert categories == set(CATEGORY_ORDER)


def test_rows_are_grouped_in_listening_order():
    spec = make()
    assert [category for category, _ in spec.by_category()] == list(CATEGORY_ORDER)


def test_row_names_are_unique():
    names = [b.name for b in make().benefits]
    assert len(names) == len(set(names))


def test_skeleton_rows_returns_an_independent_copy():
    first = skeleton_rows()
    first[0]["name"] = "mutated"
    assert skeleton_rows()[0]["name"] != "mutated"


def test_caller_can_supply_a_shorter_row_set():
    spec = make(rows=[{"name": "Monthly plan premium", "category": "money"}])
    assert len(spec.benefits) == 1
    assert spec.benefits[0].member_cost == SOB_PLACEHOLDER


def test_a_rules_only_row_set_still_validates():
    # planspec requires a detail on every rules row; the scaffold supplies one.
    spec = make(
        rows=[
            {
                "name": f"{SOB_PLACEHOLDER} Network",
                "category": "rules",
                "detail": f"{SOB_PLACEHOLDER} State the rule.",
            }
        ]
    )
    assert spec.benefits[0].member_cost == ""


# --- serialized form --------------------------------------------------------


class TestUnfilledIsBlockingInBothLanguages:
    """An unread copay is missing from the English episode too.

    Spanish is protected by the translation marker, but English has no
    translation step, so before `unfilled` existed a scaffold built clean in
    English and could have been carried into NotebookLM with `[SOB]` where every
    dollar amount belonged.
    """

    def test_placeholder_constant_is_shared_with_planspec(self):
        assert SOB_PLACEHOLDER == PLANSPEC_PLACEHOLDER

    def test_scaffold_is_not_ready_for_english_either(self):
        assert make().ready_for("en") is False

    def test_unfilled_reports_every_placeholder_field(self):
        spec = make()
        # One per priced row's cost, three per rules row (name + detail), plus
        # the provenance field itself.
        priced = [b for b in spec.benefits if b.category != "rules"]
        rules = [b for b in spec.benefits if b.category == "rules"]
        assert len(spec.unfilled()) == len(priced) + 2 * len(rules) + 1

    def test_unfilled_flags_missing_provenance(self):
        assert "plan.sob_source" in make().unfilled()

    def test_english_kit_is_blocked(self):
        kit = build_kit(make(), "en")
        assert not kit.complete
        assert kit.unfilled
        assert not kit.translation_gaps

    def test_spanish_kit_is_blocked_for_both_reasons(self):
        kit = build_kit(make(), "es")
        assert not kit.complete
        assert kit.unfilled
        assert kit.translation_gaps
        assert kit.blocking == kit.unfilled + kit.translation_gaps

    def test_english_review_names_the_unread_fields(self):
        review = build_kit(make(), "en").files["review.md"]
        assert "BLOCKED" in review
        assert SOB_PLACEHOLDER in review

    def test_filling_the_spec_clears_the_english_block(self):
        spec = make(
            rows=[{"name": "Monthly plan premium", "name_es": "Prima mensual", "category": "money"}]
        )
        assert not build_kit(spec, "en").complete

        spec.benefits[0].member_cost = "$0"
        spec.sob_source = "humana-gold-plus-sob-2026.pdf p.4"
        assert spec.unfilled() == []
        assert build_kit(spec, "en").complete

    def test_a_finished_spec_is_unaffected(self):
        # The committed example has invented but complete figures; it must not
        # start reporting as blocked because of this guard.
        example = PlanSpec.load(EXAMPLE)
        assert example.unfilled() == []
        assert build_kit(example, "en").complete
        assert build_kit(example, "es").complete


def test_saved_json_omits_empty_optional_fields(tmp_path):
    path = make().save(tmp_path / "spec.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    priced = [b for b in payload["benefits"] if b["category"] != "rules"]
    assert priced
    for benefit in priced:
        assert "member_cost_es" not in benefit
        assert "detail_es" not in benefit
