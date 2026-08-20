"""Blank plan-spec scaffolding.

:mod:`planspec` deliberately refuses to guess: every number in an episode has to
be typed by a human who read the page it came from. That rule is what makes the
audio safe, and it is also the reason adding a plan feels like a chore — you
start from an empty file and try to remember which twenty-odd lines of the
Summary of Benefits actually matter to someone listening in the car.

This module removes the remembering without touching the rule. It produces a
spec that has:

* every line a South Florida MA-PD Summary of Benefits is expected to fill,
  in the order a listener needs them,
* the Spanish **benefit name** already written, because a benefit name is a
  label and translating "Specialist visit" carries no plan-specific risk,
* :data:`SOB_PLACEHOLDER` wherever a fact belongs.

Nothing factual is pre-filled. Costs, limits, and plan rules are left as
placeholders, and the placeholder is not language-neutral, so
:meth:`planspec.PlanSpec.untranslated` reports every unfilled row and
``cli.py build`` prints the kit as ``BLOCKED``. A scaffold cannot be recorded by
accident; it has to be filled in first.

Example:
    >>> spec = blank_spec(
    ...     plan_id="H1036-001", plan_name="Gold Plus", carrier="Humana",
    ...     plan_year=2026, plan_type="HMO", counties=["Miami-Dade"],
    ...     verified_by="Manny Leon", verified_on="2026-08-11",
    ... )
    >>> spec.slug()
    'h1036-001-2026'
    >>> spec.ready_for("es")
    False
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from planspec import SOB_PLACEHOLDER, Benefit, PlanSpec

# The standard CMS multi-plan disclaimer. Boilerplate, not plan-specific — but
# see docs/compliance.md: each carrier has to confirm its own required wording
# before an episode reaches a member.
DEFAULT_DISCLAIMER_EN = (
    "This is a plain-language walkthrough of your plan's Summary of Benefits. "
    "Your Evidence of Coverage is the official document and controls in any "
    "disagreement. We do not offer every plan available in your area. Any "
    "information we provide is limited to the plans we do offer in your area. "
    "Please contact Medicare.gov or 1-800-MEDICARE to get information on all "
    "of your options."
)

DEFAULT_DISCLAIMER_ES = (
    "Esta es una explicacion en palabras sencillas del Resumen de Beneficios "
    "de su plan. Su Evidencia de Cobertura es el documento oficial y es el que "
    "manda si hay alguna diferencia. No ofrecemos todos los planes disponibles "
    "en su area. La informacion que ofrecemos se limita a los planes que si "
    "ofrecemos en su area. Comuniquese con Medicare.gov o llame a "
    "1-800-MEDICARE para obtener informacion sobre todas sus opciones."
)

# One row per line worth speaking. `name`/`name_es` are labels and are safe to
# ship pre-written; everything factual is a placeholder. Rows a given plan does
# not have (a giveback it does not offer, a tier it does not use) get deleted
# rather than filled — a shorter episode is a better episode.
#
# `rules` rows carry the placeholder in the name as well, because whether a rule
# applies at all depends on the plan: an HMO's referral requirement is not a
# PPO's, and pre-writing "a referral is required" would be inventing a fact.
_SKELETON: Tuple[Dict[str, Optional[str]], ...] = (
    # --- money ---------------------------------------------------------
    {
        "name": "Monthly plan premium",
        "name_es": "Prima mensual del plan",
        "category": "money",
    },
    {
        "name": "Part B premium giveback",
        "name_es": "Reembolso de la prima de la Parte B",
        "category": "money",
    },
    {
        "name": "Medical deductible",
        "name_es": "Deducible medico",
        "category": "money",
    },
    {
        "name": "Prescription drug deductible",
        "name_es": "Deducible de medicinas recetadas",
        "category": "money",
    },
    {
        "name": "Most you would pay in a year for medical care",
        "name_es": "Lo maximo que pagaria en un ano por atencion medica",
        "category": "money",
    },
    # --- care ----------------------------------------------------------
    {
        "name": "Primary care doctor visit",
        "name_es": "Visita al medico de cabecera",
        "category": "care",
    },
    {
        "name": "Specialist visit",
        "name_es": "Visita al especialista",
        "category": "care",
    },
    {
        "name": "Annual wellness visit",
        "name_es": "Visita anual de bienestar",
        "category": "care",
    },
    {
        "name": "Urgent care",
        "name_es": "Atencion urgente",
        "category": "care",
    },
    {
        "name": "Emergency room",
        "name_es": "Sala de emergencia",
        "category": "care",
    },
    {
        "name": "Ambulance",
        "name_es": "Ambulancia",
        "category": "care",
    },
    {
        "name": "Inpatient hospital stay",
        "name_es": "Estadia en el hospital",
        "category": "care",
    },
    {
        "name": "Outpatient surgery",
        "name_es": "Cirugia ambulatoria",
        "category": "care",
    },
    {
        "name": "Lab work and blood tests",
        "name_es": "Analisis de laboratorio y de sangre",
        "category": "care",
    },
    {
        "name": "X-rays",
        "name_es": "Radiografias",
        "category": "care",
    },
    {
        "name": "Advanced imaging such as an MRI or a CT scan",
        "name_es": "Imagenes avanzadas como una resonancia magnetica o una tomografia",
        "category": "care",
    },
    {
        "name": "Physical therapy",
        "name_es": "Terapia fisica",
        "category": "care",
    },
    {
        "name": "Mental health visit",
        "name_es": "Visita de salud mental",
        "category": "care",
    },
    {
        "name": "Skilled nursing facility",
        "name_es": "Centro de enfermeria especializada",
        "category": "care",
    },
    # --- extras --------------------------------------------------------
    {
        "name": "Dental — cleanings, exams, and x-rays",
        "name_es": "Dental — limpiezas, examenes y radiografias",
        "category": "extras",
    },
    {
        "name": "Dental — fillings, crowns, dentures, and extractions",
        "name_es": "Dental — rellenos, coronas, dentaduras y extracciones",
        "category": "extras",
    },
    {
        "name": "Eye exam",
        "name_es": "Examen de la vista",
        "category": "extras",
    },
    {
        "name": "Allowance for eyeglasses or contact lenses",
        "name_es": "Ayuda para lentes o lentes de contacto",
        "category": "extras",
    },
    {
        "name": "Hearing exam",
        "name_es": "Examen de audicion",
        "category": "extras",
    },
    {
        "name": "Allowance for hearing aids",
        "name_es": "Ayuda para aparatos auditivos",
        "category": "extras",
    },
    {
        "name": "Over-the-counter card",
        "name_es": "Tarjeta de venta libre",
        "category": "extras",
    },
    {
        "name": "Transportation to medical appointments",
        "name_es": "Transporte a citas medicas",
        "category": "extras",
    },
    {
        "name": "Fitness benefit",
        "name_es": "Beneficio de gimnasio",
        "category": "extras",
    },
    {
        "name": "Meals after a hospital stay",
        "name_es": "Comidas despues de una estadia en el hospital",
        "category": "extras",
    },
    # --- drugs ---------------------------------------------------------
    {
        "name": "Tier 1 preferred generic drugs at a preferred pharmacy",
        "name_es": "Medicinas genericas preferidas del Nivel 1 en una farmacia preferida",
        "category": "drugs",
    },
    {
        "name": "Tier 2 generic drugs",
        "name_es": "Medicinas genericas del Nivel 2",
        "category": "drugs",
    },
    {
        "name": "Tier 3 preferred brand-name drugs",
        "name_es": "Medicinas de marca preferidas del Nivel 3",
        "category": "drugs",
    },
    {
        "name": "Tier 4 non-preferred drugs",
        "name_es": "Medicinas no preferidas del Nivel 4",
        "category": "drugs",
    },
    {
        "name": "Tier 5 specialty drugs",
        "name_es": "Medicinas de especialidad del Nivel 5",
        "category": "drugs",
    },
    {
        "name": "Insulin",
        "name_es": "Insulina",
        "category": "drugs",
    },
    {
        "name": "A 90-day supply by mail order",
        "name_es": "Un suministro de 90 dias por pedido por correo",
        "category": "drugs",
    },
    # --- rules ---------------------------------------------------------
    {
        "name": f"{SOB_PLACEHOLDER} Network — what happens if a member goes out of network",
        "category": "rules",
        "detail": f"{SOB_PLACEHOLDER} State the rule in plain words. An HMO and a PPO answer this differently.",
    },
    {
        "name": f"{SOB_PLACEHOLDER} Referrals — whether one is needed to see a specialist",
        "category": "rules",
        "detail": f"{SOB_PLACEHOLDER} Say who issues it and when it is needed, or delete this row if the plan needs none.",
    },
    {
        "name": f"{SOB_PLACEHOLDER} Prior authorization — services the plan must approve first",
        "category": "rules",
        "detail": f"{SOB_PLACEHOLDER} Name the categories the SOB flags, and point the listener to the Evidence of Coverage for the full list.",
    },
    {
        "name": f"{SOB_PLACEHOLDER} Service area — where the plan works",
        "category": "rules",
        "detail": f"{SOB_PLACEHOLDER} Name the counties, and say what happens when a member moves or travels.",
    },
)


def skeleton_rows() -> List[Dict[str, Optional[str]]]:
    """A fresh mutable copy of the standard SOB row set."""
    return [dict(row) for row in _SKELETON]


def _to_benefit(row: Dict[str, Optional[str]]) -> Benefit:
    category = row["category"] or ""
    # `rules` rows describe a condition rather than a price, and planspec
    # forbids a cost on them; every other row must carry one, so it gets the
    # placeholder until a human reads the real figure off the page.
    member_cost = "" if category == "rules" else SOB_PLACEHOLDER
    return Benefit(
        name=row["name"] or "",
        category=category,
        member_cost=member_cost,
        detail=row.get("detail") or "",
        name_es=row.get("name_es"),
        # Left unset on purpose: these are what `build` counts as blocking.
        member_cost_es=None,
        detail_es=None,
    )


def blank_spec(
    *,
    plan_id: str,
    plan_name: str,
    carrier: str,
    plan_year: int,
    plan_type: str,
    counties: Sequence[str],
    verified_by: str,
    verified_on: str,
    rows: Optional[Sequence[Dict[str, Optional[str]]]] = None,
) -> PlanSpec:
    """Build an unfilled :class:`~planspec.PlanSpec` for one plan-year.

    The result is *valid* — it round-trips through ``PlanSpec.save`` and
    ``load`` — and *not ready*: ``spec.ready_for("es")`` is False and every
    factual field reads :data:`SOB_PLACEHOLDER` until someone types the real
    values from the Summary of Benefits.

    Args:
        plan_id: CMS contract-PBP, e.g. ``H1036-001``.
        plan_name: Marketed name, spelled the way the SOB spells it.
        carrier: Carrier name.
        plan_year: Contract year the SOB covers.
        plan_type: ``HMO``, ``PPO``, ``HMO D-SNP``, ``PDP``, and so on.
        counties: Service-area counties this spec will be accurate for.
        verified_by: Who will check the spec against the SOB.
        verified_on: ISO date to stamp as the verification date.
        rows: Override the row set; defaults to :func:`skeleton_rows`.

    Raises:
        planspec.PlanSpecError: If any identifying field is malformed —
            validation is the same as for a finished spec.
    """
    source_rows = list(rows) if rows is not None else skeleton_rows()

    return PlanSpec(
        plan_id=plan_id,
        plan_name=plan_name,
        carrier=carrier,
        plan_year=plan_year,
        plan_type=plan_type,
        counties=list(counties),
        benefits=[_to_benefit(row) for row in source_rows],
        sob_source=(
            f"{SOB_PLACEHOLDER} Replace with the SOB filename and the page "
            f"numbers each figure came from."
        ),
        sob_verified_on=verified_on,
        verified_by=verified_by,
        disclaimer_en=DEFAULT_DISCLAIMER_EN,
        disclaimer_es=DEFAULT_DISCLAIMER_ES,
        notes=(
            f"SCAFFOLD — not filled in. Every {SOB_PLACEHOLDER} is a value a "
            f"human still has to read off the Summary of Benefits. Delete rows "
            f"this plan does not offer instead of marking them $0, and fill in "
            f"member_cost_es for any cost that contains a word. Kits built from "
            f"this file report BLOCKED until that is done."
        ),
    )
