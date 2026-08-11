"""Tracks which plan-year episodes exist, what state they are in, and whether
they are safe to send.

The catalog is the thing standing between "we generated some audio" and "a
member received it." Its job is to make one failure mode impossible: sending a
member an episode that describes a benefit grid the plan no longer has.

Every entry stores a fingerprint of the plan spec the audio was generated from.
Change a copay in the spec and the fingerprint changes, which marks the approved
episode **stale** — it drops out of :func:`Catalog.deliverable` immediately,
without anyone having to remember that the audio needs redoing.

States move in one direction:

    kit_built -> audio_generated -> approved -> published

Only ``published`` entries with a matching fingerprint are deliverable.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from planspec import PlanSpec, _require_language

STATUSES = ("kit_built", "audio_generated", "approved", "published")

_NEXT_STATUS: Dict[str, str] = {
    "kit_built": "audio_generated",
    "audio_generated": "approved",
    "approved": "published",
}


class CatalogError(RuntimeError):
    """Raised on an illegal state transition or a missing entry."""


def fingerprint(spec: PlanSpec) -> str:
    """Short, stable hash of a plan spec's member-facing content.

    Internal-only fields are excluded: re-verifying an unchanged SOB or fixing a
    typo in ``notes`` should not invalidate approved audio.
    """
    payload = spec.to_dict()
    for internal in ("notes", "sob_verified_on", "verified_by"):
        payload.pop(internal, None)

    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


@dataclass
class Entry:
    """One plan-year in one language."""

    slug: str
    plan_id: str
    plan_year: int
    lang: str
    status: str
    spec_fingerprint: str
    kit_path: str = ""
    audio_path: str = ""
    audio_link: str = ""
    approved_by: str = ""
    approved_on: str = ""
    published_on: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise CatalogError(
                f"Unknown status {self.status!r}; expected one of {list(STATUSES)}"
            )
        _require_language(self.lang)

    @property
    def key(self) -> str:
        return f"{self.slug}/{self.lang}"

    def is_stale(self, spec: PlanSpec) -> bool:
        """True when the plan spec changed since this audio was made."""
        return self.spec_fingerprint != fingerprint(spec)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v != ""}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entry":
        try:
            return cls(**data)
        except TypeError as exc:
            raise CatalogError(f"Invalid catalog entry: {exc}") from exc


@dataclass
class Catalog:
    """A JSON-backed registry of episode entries."""

    entries: Dict[str, Entry] = field(default_factory=dict)
    path: Optional[Path] = None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path | str) -> "Catalog":
        """Load a catalog, returning an empty one if the file does not exist."""
        path = Path(path)
        if not path.exists():
            return cls(entries={}, path=path)

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CatalogError(f"Catalog {path} is not valid JSON: {exc}") from exc

        if not isinstance(raw, list):
            raise CatalogError(f"Catalog {path} must contain a JSON array")

        entries = {}
        for item in raw:
            entry = Entry.from_dict(item)
            entries[entry.key] = entry

        return cls(entries=entries, path=path)

    def save(self, path: Path | str | None = None) -> Path:
        target = Path(path) if path else self.path
        if target is None:
            raise CatalogError("No path given and this catalog has no default path")

        target.parent.mkdir(parents=True, exist_ok=True)
        payload = [e.to_dict() for e in self.sorted_entries()]
        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        self.path = target
        return target

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def sorted_entries(self) -> List[Entry]:
        return sorted(self.entries.values(), key=lambda e: e.key)

    def __iter__(self) -> Iterator[Entry]:
        return iter(self.sorted_entries())

    def __len__(self) -> int:
        return len(self.entries)

    def get(self, slug: str, lang: str) -> Optional[Entry]:
        return self.entries.get(f"{slug}/{lang}")

    def require(self, slug: str, lang: str) -> Entry:
        entry = self.get(slug, lang)
        if entry is None:
            raise CatalogError(f"No catalog entry for {slug}/{lang}")
        return entry

    def deliverable(self, spec: PlanSpec, lang: str) -> Entry:
        """Return the entry that may be sent to a member, or raise.

        Raises:
            CatalogError: If no entry exists, it is not published, or the plan
                spec has changed since the audio was approved.
        """
        entry = self.require(spec.slug(), lang)

        if entry.status != "published":
            raise CatalogError(
                f"{entry.key} is {entry.status}, not published — nothing to send"
            )

        if entry.is_stale(spec):
            raise CatalogError(
                f"{entry.key} was approved against an older version of the plan "
                f"spec. Rebuild the kit and regenerate the audio before sending."
            )

        return entry

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def register_kit(self, spec: PlanSpec, lang: str, kit_path: Path | str) -> Entry:
        """Record a freshly built kit, resetting any prior approval.

        Rebuilding a kit for a spec that changed deliberately throws away the
        old approval: the audio it approved no longer describes this plan.
        """
        _require_language(lang)
        key = f"{spec.slug()}/{lang}"
        current = self.entries.get(key)
        new_fingerprint = fingerprint(spec)

        if current is not None and current.spec_fingerprint == new_fingerprint:
            current.kit_path = str(kit_path)
            return current

        entry = Entry(
            slug=spec.slug(),
            plan_id=spec.plan_id,
            plan_year=spec.plan_year,
            lang=lang,
            status="kit_built",
            spec_fingerprint=new_fingerprint,
            kit_path=str(kit_path),
            notes=(
                "Rebuilt after plan spec change; previous approval discarded."
                if current is not None
                else ""
            ),
        )
        self.entries[key] = entry
        return entry

    def _advance(self, entry: Entry, to_status: str) -> Entry:
        expected = _NEXT_STATUS.get(entry.status)
        if expected != to_status:
            raise CatalogError(
                f"{entry.key}: cannot go from {entry.status!r} to {to_status!r}"
                + (f"; the next step is {expected!r}" if expected else "")
            )
        entry.status = to_status
        return entry

    def record_audio(
        self, slug: str, lang: str, audio_path: str, audio_link: str = ""
    ) -> Entry:
        """Mark that a human generated and downloaded the NotebookLM audio."""
        entry = self.require(slug, lang)
        if not audio_path.strip():
            raise CatalogError("audio_path is required when recording audio")

        self._advance(entry, "audio_generated")
        entry.audio_path = audio_path
        entry.audio_link = audio_link
        return entry

    def approve(self, slug: str, lang: str, approved_by: str, approved_on: str) -> Entry:
        """Record the accuracy sign-off from `review.md`."""
        entry = self.require(slug, lang)
        if not approved_by.strip():
            raise CatalogError("approve() requires the name of a real reviewer")

        self._advance(entry, "approved")
        entry.approved_by = approved_by
        entry.approved_on = approved_on
        return entry

    def publish(self, slug: str, lang: str, published_on: str, audio_link: str = "") -> Entry:
        """Make an approved episode deliverable to members."""
        entry = self.require(slug, lang)
        self._advance(entry, "published")
        entry.published_on = published_on
        if audio_link:
            entry.audio_link = audio_link

        if not entry.audio_link:
            raise CatalogError(
                f"{entry.key}: an audio_link is required to publish — that is "
                f"the URL the member receives"
            )
        return entry

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def status_report(self, specs: List[PlanSpec]) -> List[str]:
        """Human-readable status per plan/language, including stale audio."""
        by_slug = {s.slug(): s for s in specs}
        lines: List[str] = []

        for entry in self.sorted_entries():
            spec = by_slug.get(entry.slug)
            if spec is None:
                lines.append(f"{entry.key}: {entry.status} (no plan spec on disk)")
                continue

            flag = " [STALE — spec changed]" if entry.is_stale(spec) else ""
            lines.append(f"{entry.key}: {entry.status}{flag}")

        for spec in specs:
            for lang in ("en", "es"):
                if self.get(spec.slug(), lang) is None:
                    lines.append(f"{spec.slug()}/{lang}: no kit built")

        return sorted(lines)
