import json
from pathlib import Path

import pytest

from catalog import Catalog, CatalogError, Entry, fingerprint
from planspec import PlanSpec

from test_planspec import minimal_spec_dict

EXAMPLE = Path(__file__).resolve().parent / "plans" / "example-h1234-001-2026.json"


@pytest.fixture
def spec():
    return PlanSpec.load(EXAMPLE)


@pytest.fixture
def catalog(tmp_path):
    return Catalog.load(tmp_path / "catalog.json")


def take_to_published(catalog, spec, lang="en", link="https://audio.example/1.m4a"):
    catalog.register_kit(spec, lang, "kits/x")
    catalog.record_audio(spec.slug(), lang, "audio/x.m4a")
    catalog.approve(spec.slug(), lang, "Manny Leon", "2026-08-11")
    return catalog.publish(spec.slug(), lang, "2026-08-11", link)


class TestFingerprint:
    def test_stable_across_identical_specs(self, spec):
        assert fingerprint(spec) == fingerprint(PlanSpec.load(EXAMPLE))

    def test_changes_when_a_copay_changes(self, spec):
        changed = PlanSpec.from_dict(spec.to_dict())
        changed.benefits[3].member_cost = "$50 copay"
        assert fingerprint(changed) != fingerprint(spec)

    def test_changes_when_a_county_is_added(self, spec):
        changed = PlanSpec.from_dict(spec.to_dict())
        changed.counties.append("Palm Beach")
        assert fingerprint(changed) != fingerprint(spec)

    def test_ignores_internal_only_fields(self, spec):
        """Re-verifying an unchanged SOB must not invalidate approved audio."""
        reverified = PlanSpec.from_dict(
            {**spec.to_dict(), "sob_verified_on": "2026-09-01", "notes": "rechecked"}
        )
        assert fingerprint(reverified) == fingerprint(spec)


class TestTransitions:
    def test_happy_path(self, catalog, spec):
        entry = take_to_published(catalog, spec)
        assert entry.status == "published"
        assert entry.audio_link == "https://audio.example/1.m4a"

    def test_cannot_skip_the_accuracy_review(self, catalog, spec):
        catalog.register_kit(spec, "en", "kits/x")
        catalog.record_audio(spec.slug(), "en", "audio/x.m4a")

        with pytest.raises(CatalogError, match="cannot go from 'audio_generated'"):
            catalog.publish(spec.slug(), "en", "2026-08-11", "https://a/1.m4a")

    def test_cannot_approve_audio_that_does_not_exist(self, catalog, spec):
        catalog.register_kit(spec, "en", "kits/x")
        with pytest.raises(CatalogError, match="cannot go from 'kit_built'"):
            catalog.approve(spec.slug(), "en", "Manny Leon", "2026-08-11")

    def test_error_names_the_expected_next_step(self, catalog, spec):
        catalog.register_kit(spec, "en", "kits/x")
        with pytest.raises(CatalogError, match="next step is 'audio_generated'"):
            catalog.approve(spec.slug(), "en", "Manny Leon", "2026-08-11")

    def test_cannot_republish(self, catalog, spec):
        take_to_published(catalog, spec)
        with pytest.raises(CatalogError, match="cannot go from 'published'"):
            catalog.publish(spec.slug(), "en", "2026-08-12", "https://a/2.m4a")

    def test_approval_requires_a_named_reviewer(self, catalog, spec):
        catalog.register_kit(spec, "en", "kits/x")
        catalog.record_audio(spec.slug(), "en", "audio/x.m4a")
        with pytest.raises(CatalogError, match="real reviewer"):
            catalog.approve(spec.slug(), "en", "   ", "2026-08-11")

    def test_recording_audio_requires_a_file(self, catalog, spec):
        catalog.register_kit(spec, "en", "kits/x")
        with pytest.raises(CatalogError, match="audio_path is required"):
            catalog.record_audio(spec.slug(), "en", "  ")

    def test_publishing_requires_a_member_facing_link(self, catalog, spec):
        catalog.register_kit(spec, "en", "kits/x")
        catalog.record_audio(spec.slug(), "en", "audio/x.m4a")
        catalog.approve(spec.slug(), "en", "Manny Leon", "2026-08-11")
        with pytest.raises(CatalogError, match="audio_link is required"):
            catalog.publish(spec.slug(), "en", "2026-08-11")

    def test_link_may_come_from_record_audio_instead(self, catalog, spec):
        catalog.register_kit(spec, "en", "kits/x")
        catalog.record_audio(spec.slug(), "en", "audio/x.m4a", "https://a/1.m4a")
        catalog.approve(spec.slug(), "en", "Manny Leon", "2026-08-11")
        assert catalog.publish(spec.slug(), "en", "2026-08-11").status == "published"

    def test_unknown_entry_raises(self, catalog):
        with pytest.raises(CatalogError, match="No catalog entry"):
            catalog.require("h9999-001-2026", "en")

    def test_languages_advance_independently(self, catalog, spec):
        take_to_published(catalog, spec, "en")
        catalog.register_kit(spec, "es", "kits/x/es")
        assert catalog.require(spec.slug(), "en").status == "published"
        assert catalog.require(spec.slug(), "es").status == "kit_built"


class TestStaleness:
    def test_rebuild_after_a_change_discards_approval(self, catalog, spec):
        take_to_published(catalog, spec)

        changed = PlanSpec.from_dict(spec.to_dict())
        changed.benefits[3].member_cost = "$50 copay"
        entry = catalog.register_kit(changed, "en", "kits/x")

        assert entry.status == "kit_built"
        assert "previous approval discarded" in entry.notes

    def test_rebuild_without_a_change_keeps_approval(self, catalog, spec):
        take_to_published(catalog, spec)
        entry = catalog.register_kit(PlanSpec.load(EXAMPLE), "en", "kits/other")

        assert entry.status == "published"
        assert entry.kit_path == "kits/other"

    def test_deliverable_rejects_stale_audio(self, catalog, spec):
        """The core guarantee: a copay change makes the old episode unsendable
        even if nobody remembered to rebuild it."""
        take_to_published(catalog, spec)

        changed = PlanSpec.from_dict(spec.to_dict())
        changed.benefits[3].member_cost = "$50 copay"

        with pytest.raises(CatalogError, match="older version of the plan spec"):
            catalog.deliverable(changed, "en")

    def test_deliverable_rejects_unpublished(self, catalog, spec):
        catalog.register_kit(spec, "en", "kits/x")
        with pytest.raises(CatalogError, match="is kit_built, not published"):
            catalog.deliverable(spec, "en")

    def test_deliverable_returns_the_link(self, catalog, spec):
        take_to_published(catalog, spec)
        assert catalog.deliverable(spec, "en").audio_link == "https://audio.example/1.m4a"


class TestPersistence:
    def test_missing_file_loads_as_empty(self, tmp_path):
        catalog = Catalog.load(tmp_path / "none.json")
        assert len(catalog) == 0

    def test_round_trips(self, tmp_path, spec):
        catalog = Catalog.load(tmp_path / "catalog.json")
        take_to_published(catalog, spec)
        catalog.save()

        reloaded = Catalog.load(tmp_path / "catalog.json")
        assert len(reloaded) == 1
        assert reloaded.deliverable(spec, "en").approved_by == "Manny Leon"

    def test_saved_file_is_a_sorted_json_array(self, tmp_path, spec):
        catalog = Catalog.load(tmp_path / "catalog.json")
        catalog.register_kit(spec, "es", "kits/es")
        catalog.register_kit(spec, "en", "kits/en")
        path = catalog.save()

        data = json.loads(path.read_text(encoding="utf-8"))
        assert [e["lang"] for e in data] == ["en", "es"]

    def test_rejects_a_non_array_file(self, tmp_path):
        path = tmp_path / "catalog.json"
        path.write_text('{"not": "an array"}', encoding="utf-8")
        with pytest.raises(CatalogError, match="must contain a JSON array"):
            Catalog.load(path)

    def test_rejects_malformed_json(self, tmp_path):
        path = tmp_path / "catalog.json"
        path.write_text("{[", encoding="utf-8")
        with pytest.raises(CatalogError, match="not valid JSON"):
            Catalog.load(path)

    def test_save_without_a_path_raises(self, spec):
        catalog = Catalog()
        catalog.register_kit(spec, "en", "kits/x")
        with pytest.raises(CatalogError, match="no default path"):
            catalog.save()


class TestEntry:
    def test_rejects_unknown_status(self):
        with pytest.raises(CatalogError, match="Unknown status"):
            Entry(
                slug="h1234-001-2026",
                plan_id="H1234-001",
                plan_year=2026,
                lang="en",
                status="sent",
                spec_fingerprint="abc",
            )

    def test_rejects_unknown_language(self):
        with pytest.raises(Exception, match="Unsupported language"):
            Entry(
                slug="h1234-001-2026",
                plan_id="H1234-001",
                plan_year=2026,
                lang="fr",
                status="kit_built",
                spec_fingerprint="abc",
            )


class TestStatusReport:
    def test_reports_missing_kits(self, catalog, spec):
        lines = catalog.status_report([spec])
        assert any("en: no kit built" in line for line in lines)
        assert any("es: no kit built" in line for line in lines)

    def test_flags_stale_entries(self, catalog, spec):
        take_to_published(catalog, spec)
        changed = PlanSpec.from_dict(spec.to_dict())
        changed.benefits[3].member_cost = "$50 copay"

        lines = catalog.status_report([changed])
        assert any("STALE" in line for line in lines)

    def test_reports_orphaned_entries(self, catalog, spec):
        catalog.register_kit(spec, "en", "kits/x")
        lines = catalog.status_report([])
        assert any("no plan spec on disk" in line for line in lines)
