from pathlib import Path

import pytest

from episode import TARGET_MINUTES, build_kit
from planspec import TRANSLATION_MARKER, PlanSpec, PlanSpecError

from test_planspec import minimal_spec_dict

EXAMPLE = Path(__file__).resolve().parent / "plans" / "example-h1234-001-2026.json"


@pytest.fixture
def example_spec():
    return PlanSpec.load(EXAMPLE)


class TestSourceDocument:
    def test_disclaimer_appears_at_both_ends(self, example_spec):
        source = build_kit(example_spec, "en").files["source.md"]
        assert source.count(example_spec.disclaimer_en) == 2

        head, tail = source[: len(source) // 2], source[len(source) // 2 :]
        assert example_spec.disclaimer_en in head
        assert example_spec.disclaimer_en in tail

    def test_every_benefit_reaches_the_source(self, example_spec):
        source = build_kit(example_spec, "en").files["source.md"]
        for benefit in example_spec.benefits:
            assert benefit.name in source

    def test_zero_dollar_costs_get_their_own_clause(self, example_spec):
        source = build_kit(example_spec, "en").files["source.md"]
        assert "**Primary care doctor visit** — you pay nothing for this." in source
        # The bare "$0" is unhelpful for two hosts reading aloud, and slotting a
        # noun phrase into "you pay ___" produces "you pay no cost to you".
        assert "you pay $0" not in source
        assert "no cost to you" not in source

    def test_spanish_zero_cost_clause_is_grammatical(self, example_spec):
        source = build_kit(example_spec, "es").files["source.md"]
        assert "**Visita al medico de cabecera** — usted no paga nada por esto." in source
        assert "usted paga sin costo" not in source

    def test_real_dollar_amounts_are_never_reworded(self, example_spec):
        source = build_kit(example_spec, "en").files["source.md"]
        assert "$4,500" in source
        assert "$40 copay" in source

    def test_rules_are_not_rendered_as_prices(self, example_spec):
        source = build_kit(example_spec, "en").files["source.md"]
        assert "you pay not covered" not in source.lower()
        assert "**You must use doctors and hospitals in the plan's network.**" in source

    def test_categories_appear_in_listening_order(self, example_spec):
        source = build_kit(example_spec, "en").files["source.md"]
        positions = [
            source.index("What this plan costs you"),
            source.index("Seeing a doctor"),
            source.index("Extra benefits"),
            source.index("Your prescriptions"),
            source.index("Rules that decide"),
        ]
        assert positions == sorted(positions)

    def test_source_is_traceable_to_the_sob(self, example_spec):
        source = build_kit(example_spec, "en").files["source.md"]
        assert example_spec.sob_source in source
        assert example_spec.verified_by in source
        assert example_spec.sob_verified_on in source

    def test_spanish_source_is_spanish(self, example_spec):
        source = build_kit(example_spec, "es").files["source.md"]
        assert "usted paga" in source
        assert "Lo que este plan le cuesta" in source
        assert example_spec.disclaimer_es in source

    def test_spanish_source_carries_no_english_costs(self, example_spec):
        source = build_kit(example_spec, "es").files["source.md"]
        assert "copay" not in source
        assert "$40 de copago" in source


class TestSteeringPrompt:
    def test_forbids_material_outside_the_source(self, example_spec):
        steering = build_kit(example_spec, "en").files["steering.txt"]
        assert "ONLY the source document" in steering

    def test_forbids_rounding(self, example_spec):
        steering = build_kit(example_spec, "en").files["steering.txt"]
        assert "Never round" in steering

    def test_forbids_plan_comparisons(self, example_spec):
        """Comparative claims are the fastest way to turn an educational
        communication into a marketing piece."""
        steering = build_kit(example_spec, "en").files["steering.txt"]
        assert "Do not compare this plan" in steering

    def test_names_the_plan_and_the_runtime(self, example_spec):
        steering = build_kit(example_spec, "en").files["steering.txt"]
        assert example_spec.plan_id in steering
        assert str(TARGET_MINUTES[0]) in steering
        assert str(TARGET_MINUTES[1]) in steering

    def test_spanish_prompt_asks_for_spanish(self, example_spec):
        steering = build_kit(example_spec, "es").files["steering.txt"]
        assert "Idioma: espanol" in steering
        assert "SOLO el documento fuente" in steering


class TestDeliveryMessage:
    def test_carries_both_placeholders(self, example_spec):
        for lang in ("en", "es"):
            delivery = build_kit(example_spec, lang).files["delivery.md"]
            assert "{{first_name}}" in delivery
            assert "{{audio_link}}" in delivery

    def test_points_back_to_the_official_document(self, example_spec):
        delivery = build_kit(example_spec, "en").files["delivery.md"]
        assert "Summary of Benefits is the official document" in delivery

    def test_spanish_message_points_back_too(self, example_spec):
        delivery = build_kit(example_spec, "es").files["delivery.md"]
        assert "documento oficial" in delivery

    def test_agent_phone_is_omitted_cleanly_when_unset(self, example_spec):
        delivery = build_kit(example_spec, "en").files["delivery.md"]
        assert "call me." in delivery
        assert "at ." not in delivery

    def test_agent_phone_is_included_when_set(self):
        spec = PlanSpec.from_dict(minimal_spec_dict(agent_phone="305-555-0142"))
        delivery = build_kit(spec, "en").files["delivery.md"]
        assert "call me at 305-555-0142." in delivery


class TestReviewChecklist:
    def test_lists_the_counties_to_confirm(self, example_spec):
        review = build_kit(example_spec, "en").files["review.md"]
        for county in example_spec.counties:
            assert county in review

    def test_has_a_signature_block(self, example_spec):
        review = build_kit(example_spec, "en").files["review.md"]
        assert "Reviewed by:" in review

    def test_spanish_review_adds_a_native_speaker_check(self, example_spec):
        review = build_kit(example_spec, "es").files["review.md"]
        assert "native Spanish speaker" in review

    def test_translation_gaps_are_called_out_as_blocking(self):
        spec = PlanSpec.from_dict(
            minimal_spec_dict(
                benefits=[
                    {"name": "Hearing aids", "category": "extras", "member_cost": "$699 each"}
                ]
            )
        )
        review = build_kit(spec, "es").files["review.md"]
        assert "BLOCKED" in review
        assert TRANSLATION_MARKER in review
        assert "Hearing aids" in review

    def test_no_blocked_section_when_fully_translated(self, example_spec):
        review = build_kit(example_spec, "es").files["review.md"]
        assert "BLOCKED" not in review


class TestKit:
    def test_complete_when_nothing_is_missing(self, example_spec):
        assert build_kit(example_spec, "en").complete
        assert build_kit(example_spec, "es").complete

    def test_incomplete_spanish_kit_reports_its_gaps(self):
        spec = PlanSpec.from_dict(
            minimal_spec_dict(
                benefits=[
                    {"name": "Hearing aids", "category": "extras", "member_cost": "$699 each"}
                ]
            )
        )
        kit = build_kit(spec, "es")
        assert not kit.complete
        assert kit.translation_gaps

        # English is unaffected by a missing Spanish translation.
        assert build_kit(spec, "en").complete

    def test_writes_all_four_files_under_slug_and_language(self, example_spec, tmp_path):
        directory = build_kit(example_spec, "es").write(tmp_path)
        assert directory == tmp_path / "h1234-001-2026" / "es"
        assert sorted(p.name for p in directory.iterdir()) == [
            "delivery.md",
            "review.md",
            "source.md",
            "steering.txt",
        ]

    def test_rebuilding_overwrites_in_place(self, example_spec, tmp_path):
        first = build_kit(example_spec, "en").write(tmp_path)
        stale = first / "source.md"
        stale.write_text("stale", encoding="utf-8")

        build_kit(example_spec, "en").write(tmp_path)
        assert stale.read_text(encoding="utf-8") != "stale"

    def test_rejects_unknown_language(self, example_spec):
        with pytest.raises(PlanSpecError, match="Unsupported language"):
            build_kit(example_spec, "pt")
