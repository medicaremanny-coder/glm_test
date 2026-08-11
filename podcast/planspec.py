"""Plan specification model for the MedicareManny benefits podcast.

A :class:`PlanSpec` is the single structured record for one Medicare plan-year.
It is transcribed by hand from that plan's official **Summary of Benefits** (SOB)
and it is the *only* input the episode generator is allowed to read.

Why hand-transcribed instead of auto-extracted from the SOB PDF? Because the
output of this pipeline is audio that tells a member what their health care
costs. A layout-parsing mistake on a benefits grid — reading the in-network
column as the out-of-network column, for instance — becomes a confident spoken
sentence that a member acts on. The spec is small enough to type in fifteen
minutes and it carries its own provenance fields (`sob_source`,
`sob_verified_on`, `verified_by`) so every number in an episode can be traced
back to a page a human actually read.

Example:
    >>> spec = PlanSpec.from_dict({
    ...     "plan_id": "H1234-001",
    ...     "plan_name": "Example Advantage Plus",
    ...     "carrier": "Example Health",
    ...     "plan_year": 2026,
    ...     "plan_type": "HMO",
    ...     "counties": ["Miami-Dade"],
    ...     "sob_source": "example-sob-2026.pdf p.4",
    ...     "sob_verified_on": "2026-08-11",
    ...     "verified_by": "Manny Leon",
    ...     "disclaimer_en": "Example disclaimer.",
    ...     "disclaimer_es": "Aviso de ejemplo.",
    ...     "benefits": [
    ...         {"name": "Monthly plan premium", "member_cost": "$0",
    ...          "category": "money"},
    ...     ],
    ... })
    >>> spec.plan_id
    'H1234-001'
    >>> spec.slug()
    'h1234-001-2026'
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Contract number + PBP. H = local MA/MA-PD, R = regional PPO, S = PDP,
# E = employer group. CMS writes these as H1234-001.
PLAN_ID_PATTERN = re.compile(r"^[HRSE]\d{4}-\d{3}$")

ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SUPPORTED_LANGUAGES: Tuple[str, ...] = ("en", "es")

# Benefit categories, in the order a member actually needs them when they are
# listening in the car. Money first because it is the question everyone has;
# plan rules last because they only matter once you know what you have.
CATEGORY_ORDER: Tuple[str, ...] = ("money", "care", "extras", "drugs", "rules")

CATEGORY_LABELS: Dict[str, Dict[str, str]] = {
    "money": {
        "en": "What this plan costs you",
        "es": "Lo que este plan le cuesta",
    },
    "care": {
        "en": "Seeing a doctor and going to the hospital",
        "es": "Ver al medico e ir al hospital",
    },
    "extras": {
        "en": "Extra benefits people forget they have",
        "es": "Beneficios extra que la gente olvida que tiene",
    },
    "drugs": {
        "en": "Your prescriptions",
        "es": "Sus medicinas recetadas",
    },
    "rules": {
        "en": "Rules that decide whether something is covered",
        "es": "Reglas que deciden si algo esta cubierto",
    },
}

# Marker written into Spanish output wherever a required translation is absent.
# It is deliberately loud: it must never survive to a recorded episode.
TRANSLATION_MARKER = "[TRADUCIR]"


class PlanSpecError(ValueError):
    """Raised when a plan spec is missing or malformed."""


@dataclass
class Benefit:
    """One line item from the Summary of Benefits.

    Attributes:
        name: What the benefit is called, in member-facing words
            ("Specialist visit"), not carrier jargon ("Spec Off Vst").
        category: One of :data:`CATEGORY_ORDER`.
        member_cost: What the member pays, exactly as the SOB states it
            ("$0", "$45 copay", "20% coinsurance", "Not covered"). Required for
            every category except ``rules``, which describes conditions on
            coverage rather than a price.
        detail: Optional one-sentence clarification a member needs in order to
            use the benefit correctly (limits, frequency, network conditions).
        name_es / member_cost_es / detail_es: Spanish equivalents. Left as
            ``None`` they are rendered as :data:`TRANSLATION_MARKER` and
            reported by :meth:`PlanSpec.untranslated`.
    """

    name: str
    category: str
    member_cost: str = ""
    detail: str = ""
    name_es: Optional[str] = None
    member_cost_es: Optional[str] = None
    detail_es: Optional[str] = None

    def __post_init__(self) -> None:
        for attr in ("name", "category"):
            value = getattr(self, attr)
            if not isinstance(value, str) or not value.strip():
                raise PlanSpecError(
                    f"Benefit.{attr} must be a non-empty string, got {value!r}"
                )

        if self.category not in CATEGORY_ORDER:
            raise PlanSpecError(
                f"Benefit.category must be one of {list(CATEGORY_ORDER)}, "
                f"got {self.category!r} (benefit: {self.name!r})"
            )

        if self.category != "rules" and not self.member_cost.strip():
            raise PlanSpecError(
                f"Benefit.member_cost is required for category "
                f"{self.category!r} (benefit: {self.name!r}); only 'rules' "
                f"entries may omit it"
            )

        if self.category == "rules" and not self.detail.strip():
            raise PlanSpecError(
                f"Benefit.detail is required for 'rules' entries — a rule with "
                f"no explanation is not usable to a listener "
                f"(benefit: {self.name!r})"
            )

    def localized(self, lang: str) -> Dict[str, str]:
        """Return this benefit's fields in ``lang``.

        Missing Spanish fields fall back to :data:`TRANSLATION_MARKER` rather
        than to the English text, so an untranslated cost-sharing amount cannot
        quietly ship inside a Spanish episode.
        """
        _require_language(lang)

        if lang == "en":
            return {
                "name": self.name,
                "member_cost": self.member_cost,
                "detail": self.detail,
            }

        if not self.member_cost:
            cost_es = ""
        else:
            cost_es = (
                self.member_cost_es
                or _translate_cost(self.member_cost)
                or f"{TRANSLATION_MARKER} {self.member_cost}"
            )

        return {
            "name": self.name_es or f"{TRANSLATION_MARKER} {self.name}",
            "member_cost": cost_es,
            # An empty English detail means there is nothing to translate.
            "detail": (
                self.detail_es
                if self.detail_es
                else (f"{TRANSLATION_MARKER} {self.detail}" if self.detail else "")
            ),
        }

    def missing_translations(self) -> List[str]:
        """Names of Spanish fields that still need a human translation."""
        missing: List[str] = []
        if not self.name_es:
            missing.append("name_es")
        if (
            self.member_cost
            and not self.member_cost_es
            and _translate_cost(self.member_cost) is None
        ):
            missing.append("member_cost_es")
        if self.detail and not self.detail_es:
            missing.append("detail_es")
        return missing

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "name": self.name,
            "category": self.category,
        }
        for optional in ("member_cost", "detail", "name_es", "member_cost_es", "detail_es"):
            value = getattr(self, optional)
            if value:
                data[optional] = value
        return data


# Cost strings that are the same in both languages carry no translation risk,
# so they are allowed through untranslated. Anything with a word in it is not
# on this list on purpose.
_LANGUAGE_NEUTRAL_COST = re.compile(r"^\$?[\d,]+(\.\d{2})?%?$")


def _translate_cost(cost: str) -> Optional[str]:
    """Return ``cost`` when it is language-neutral, else ``None``.

    ``"$0"`` and ``"20%"`` read identically to a Spanish speaker. ``"$45
    copay"`` does not, and returns ``None`` so the caller flags it.
    """
    return cost if _LANGUAGE_NEUTRAL_COST.match(cost.strip()) else None


def _require_language(lang: str) -> None:
    if lang not in SUPPORTED_LANGUAGES:
        raise PlanSpecError(
            f"Unsupported language {lang!r}; expected one of "
            f"{list(SUPPORTED_LANGUAGES)}"
        )


@dataclass
class PlanSpec:
    """Everything the generator knows about one plan-year.

    Attributes:
        plan_id: CMS contract-PBP identifier, e.g. ``H1234-001``.
        plan_name: Marketed plan name, spelled as the SOB spells it.
        carrier: Carrier name.
        plan_year: Four-digit contract year.
        plan_type: ``HMO``, ``PPO``, ``HMO D-SNP``, ``PDP``, and so on.
        counties: Service-area counties this episode is accurate for. Benefits
            vary by county within one contract, which is exactly the mistake
            this field exists to prevent.
        benefits: Line items from the SOB.
        sob_source: Filename plus page reference for the SOB used.
        sob_verified_on: ISO date a human last checked this spec against it.
        verified_by: Who checked it.
        disclaimer_en / disclaimer_es: Required disclaimer, read aloud in every
            episode. Supplied per carrier — see docs/compliance.md.
        member_services_phone: Plan's member services number.
        agent_phone: Manny's number.
        notes: Internal notes; never rendered into member-facing output.
    """

    plan_id: str
    plan_name: str
    carrier: str
    plan_year: int
    plan_type: str
    counties: List[str]
    benefits: List[Benefit]
    sob_source: str
    sob_verified_on: str
    verified_by: str
    disclaimer_en: str
    disclaimer_es: str
    member_services_phone: str = ""
    agent_phone: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not PLAN_ID_PATTERN.match(self.plan_id):
            raise PlanSpecError(
                f"plan_id must look like H1234-001 (contract-PBP), "
                f"got {self.plan_id!r}"
            )

        if not isinstance(self.plan_year, int) or not 2000 <= self.plan_year <= 2100:
            raise PlanSpecError(
                f"plan_year must be a four-digit year, got {self.plan_year!r}"
            )

        for attr in (
            "plan_name",
            "carrier",
            "plan_type",
            "sob_source",
            "verified_by",
            "disclaimer_en",
            "disclaimer_es",
        ):
            value = getattr(self, attr)
            if not isinstance(value, str) or not value.strip():
                raise PlanSpecError(
                    f"{attr} must be a non-empty string, got {value!r}"
                )

        if not ISO_DATE_PATTERN.match(self.sob_verified_on):
            raise PlanSpecError(
                f"sob_verified_on must be an ISO date (YYYY-MM-DD), "
                f"got {self.sob_verified_on!r}"
            )

        if not self.counties:
            raise PlanSpecError(
                "counties must list at least one county; benefits vary by "
                "county and an episode is only accurate for the ones named"
            )

        if not self.benefits:
            raise PlanSpecError("benefits must contain at least one line item")

    def slug(self) -> str:
        """Stable filesystem/catalog key: ``h1234-001-2026``."""
        return f"{self.plan_id.lower()}-{self.plan_year}"

    def display_name(self) -> str:
        return f"{self.carrier} {self.plan_name} ({self.plan_id}, {self.plan_year})"

    def disclaimer(self, lang: str) -> str:
        _require_language(lang)
        return self.disclaimer_en if lang == "en" else self.disclaimer_es

    def by_category(self) -> List[Tuple[str, List[Benefit]]]:
        """Benefits grouped into :data:`CATEGORY_ORDER`, empty groups dropped.

        Order within a category is the order they were written in the spec, so
        whoever transcribes the SOB controls emphasis.
        """
        grouped: List[Tuple[str, List[Benefit]]] = []
        for category in CATEGORY_ORDER:
            members = [b for b in self.benefits if b.category == category]
            if members:
                grouped.append((category, members))
        return grouped

    def untranslated(self) -> List[str]:
        """Human-readable list of Spanish fields still needing translation."""
        gaps: List[str] = []
        if not self.disclaimer_es.strip():
            gaps.append("plan.disclaimer_es")
        for index, benefit in enumerate(self.benefits):
            for field_name in benefit.missing_translations():
                gaps.append(f"benefits[{index}] ({benefit.name}): {field_name}")
        return gaps

    def ready_for(self, lang: str) -> bool:
        """True when a kit in ``lang`` would contain no translation markers."""
        _require_language(lang)
        return True if lang == "en" else not self.untranslated()

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanSpec":
        if not isinstance(data, dict):
            raise PlanSpecError(
                f"Plan spec must be a JSON object, got {type(data).__name__}"
            )

        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        unknown = sorted(set(data) - known)
        if unknown:
            raise PlanSpecError(
                f"Unknown plan spec field(s): {', '.join(unknown)}. "
                f"Known fields: {', '.join(sorted(known))}"
            )

        raw_benefits = data.get("benefits")
        if not isinstance(raw_benefits, list):
            raise PlanSpecError("benefits must be a list of benefit objects")

        payload = dict(data)
        payload["benefits"] = [_benefit_from_dict(b, i) for i, b in enumerate(raw_benefits)]

        try:
            return cls(**payload)
        except TypeError as exc:
            raise PlanSpecError(f"Invalid plan spec: {exc}") from exc

    @classmethod
    def load(cls, path: Path | str) -> "PlanSpec":
        path = Path(path)
        try:
            raw = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise PlanSpecError(f"Plan spec not found: {path}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise PlanSpecError(f"Plan spec {path} is not valid JSON: {exc}") from exc

        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "plan_id": self.plan_id,
            "plan_name": self.plan_name,
            "carrier": self.carrier,
            "plan_year": self.plan_year,
            "plan_type": self.plan_type,
            "counties": list(self.counties),
            "sob_source": self.sob_source,
            "sob_verified_on": self.sob_verified_on,
            "verified_by": self.verified_by,
            "disclaimer_en": self.disclaimer_en,
            "disclaimer_es": self.disclaimer_es,
            "benefits": [b.to_dict() for b in self.benefits],
        }
        for optional in ("member_services_phone", "agent_phone", "notes"):
            value = getattr(self, optional)
            if value:
                data[optional] = value
        return data

    def save(self, path: Path | str) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path


def _benefit_from_dict(data: Any, index: int) -> Benefit:
    if not isinstance(data, dict):
        raise PlanSpecError(
            f"benefits[{index}] must be an object, got {type(data).__name__}"
        )

    known = {f for f in Benefit.__dataclass_fields__}  # type: ignore[attr-defined]
    unknown = sorted(set(data) - known)
    if unknown:
        raise PlanSpecError(
            f"benefits[{index}] has unknown field(s): {', '.join(unknown)}"
        )

    try:
        return Benefit(**data)
    except TypeError as exc:
        raise PlanSpecError(f"benefits[{index}]: {exc}") from exc


def load_all(directory: Path | str) -> List[PlanSpec]:
    """Load every ``*.json`` plan spec in ``directory``, sorted by slug."""
    directory = Path(directory)
    if not directory.is_dir():
        raise PlanSpecError(f"Not a directory: {directory}")

    specs = [PlanSpec.load(p) for p in sorted(directory.glob("*.json"))]
    return sorted(specs, key=lambda s: s.slug())


def category_label(category: str, lang: str) -> str:
    _require_language(lang)
    if category not in CATEGORY_LABELS:
        raise PlanSpecError(f"Unknown category {category!r}")
    return CATEGORY_LABELS[category][lang]
