"""Build a NotebookLM episode kit from a :class:`~podcast.planspec.PlanSpec`.

NotebookLM generates its Audio Overview from the sources you give it, steered by
a short customization prompt. Neither step is exposed through a public API, so
the automatable part of this pipeline is everything on both sides of it: turning
a Summary of Benefits into a source document that produces good audio, and
turning the resulting file into something a member actually receives.

An **episode kit** is the folder handed to whoever sits at NotebookLM:

    kits/h1234-001-2026/en/
        source.md            paste this into NotebookLM as the only source
        steering.txt         paste this into the Audio Overview customization box
        delivery.md          the message a member gets with the finished audio
        review.md            accuracy gate — signed before anything is sent

The source document is written the way it should be *heard*, not the way an SOB
is laid out. Grids become sentences, because two synthetic hosts reading a table
produce exactly the flat number-recital this project exists to avoid. Every
dollar amount is stated in words the hosts can pronounce, and the disclaimer is
placed as literal text at the top and bottom so it survives into the audio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from planspec import (
    SOB_PLACEHOLDER,
    TRANSLATION_MARKER,
    Benefit,
    PlanSpec,
    _require_language,
    category_label,
)

# Target runtime. Long enough to cover a plan properly, short enough to finish
# on the drive to a morning appointment.
TARGET_MINUTES = (8, 12)

_STRINGS: Dict[str, Dict[str, str]] = {
    "en": {
        "title": "Your plan benefits, explained",
        "intro_heading": "Read this first",
        "plan_heading": "The plan this episode is about",
        "listener": (
            "The listener is a Medicare member who just enrolled in this plan. "
            "They are listening in the car or before bed. They have not read "
            "the Summary of Benefits and they are not going to."
        ),
        "closing_heading": "How to close the episode",
        "closing": (
            "Close by telling the listener that the number to call with a "
            "question about a bill or a doctor is on the back of their member "
            "ID card, and that their agent can help them with anything the "
            "plan will not."
        ),
        "zero_cost": "you pay nothing for this",
        "not_covered": "this plan does not cover it",
        "source_note": "Source of every number in this document",
        "counties": "Counties this is accurate for",
        "plan_type": "Plan type",
        "plan_year": "Plan year",
        "disclaimer_heading": "Required disclaimer — read this out loud, word for word",
    },
    "es": {
        "title": "Sus beneficios, explicados",
        "intro_heading": "Lea esto primero",
        "plan_heading": "El plan del que trata este episodio",
        "listener": (
            "Quien escucha es un miembro de Medicare que acaba de inscribirse "
            "en este plan. Escucha en el carro o antes de dormir. No ha leido "
            "el Resumen de Beneficios y no lo va a leer."
        ),
        "closing_heading": "Como cerrar el episodio",
        "closing": (
            "Cierre diciendole a quien escucha que el numero para llamar con "
            "una pregunta sobre una factura o un medico esta en el reverso de "
            "su tarjeta de miembro, y que su agente puede ayudarle con lo que "
            "el plan no resuelva."
        ),
        "zero_cost": "usted no paga nada por esto",
        "not_covered": "este plan no lo cubre",
        "source_note": "Fuente de cada numero en este documento",
        "counties": "Condados para los que esto es correcto",
        "plan_type": "Tipo de plan",
        "plan_year": "Ano del plan",
        "disclaimer_heading": "Aviso obligatorio — lealo en voz alta, palabra por palabra",
    },
}


@dataclass
class EpisodeKit:
    """The generated files for one plan-year in one language.

    Attributes:
        slug: Plan slug, e.g. ``h1234-001-2026``.
        lang: ``en`` or ``es``.
        files: Filename to file contents.
        translation_gaps: Spanish fields still needing a human. Non-empty means
            the kit contains :data:`~podcast.planspec.TRANSLATION_MARKER` and
            must not be recorded.
        unfilled: Fields still holding :data:`~podcast.planspec.SOB_PLACEHOLDER`
            — figures nobody has read off the Summary of Benefits yet. Blocking
            in both languages, unlike ``translation_gaps``.
    """

    slug: str
    lang: str
    files: Dict[str, str]
    translation_gaps: List[str]
    unfilled: List[str] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return not self.translation_gaps and not self.unfilled

    @property
    def blocking(self) -> List[str]:
        """Everything standing between this kit and a recording session."""
        return self.unfilled + self.translation_gaps

    def write(self, root: Path | str) -> Path:
        """Write the kit to ``root/<slug>/<lang>/`` and return that directory."""
        directory = Path(root) / self.slug / self.lang
        directory.mkdir(parents=True, exist_ok=True)
        for name, contents in self.files.items():
            (directory / name).write_text(contents, encoding="utf-8")
        return directory


def build_kit(spec: PlanSpec, lang: str) -> EpisodeKit:
    """Generate the full episode kit for ``spec`` in ``lang``."""
    _require_language(lang)

    gaps = spec.untranslated() if lang == "es" else []
    unfilled = spec.unfilled()

    files = {
        "source.md": _source_document(spec, lang),
        "steering.txt": _steering_prompt(spec, lang),
        "delivery.md": _delivery_message(spec, lang),
        "review.md": _review_checklist(spec, lang, gaps, unfilled),
    }

    return EpisodeKit(
        slug=spec.slug(),
        lang=lang,
        files=files,
        translation_gaps=gaps,
        unfilled=unfilled,
    )


# ----------------------------------------------------------------------
# source.md — the only thing NotebookLM is allowed to read
# ----------------------------------------------------------------------


def _source_document(spec: PlanSpec, lang: str) -> str:
    s = _STRINGS[lang]
    lines: List[str] = [
        f"# {spec.plan_name} — {s['title']}",
        "",
        f"## {s['disclaimer_heading']}",
        "",
        f"> {spec.disclaimer(lang)}",
        "",
        f"## {s['plan_heading']}",
        "",
        f"- {spec.carrier} {spec.plan_name}",
        f"- {s['plan_type']}: {spec.plan_type} ({spec.plan_id})",
        f"- {s['plan_year']}: {spec.plan_year}",
        f"- {s['counties']}: {', '.join(spec.counties)}",
        "",
    ]

    for category, benefits in spec.by_category():
        lines.append(f"## {category_label(category, lang)}")
        lines.append("")
        for benefit in benefits:
            lines.append(_benefit_sentence(benefit, lang))
            lines.append("")

    lines += [
        f"## {s['closing_heading']}",
        "",
        s["closing"],
        "",
        f"> {spec.disclaimer(lang)}",
        "",
        "---",
        "",
        f"_{s['source_note']}: {spec.sob_source} — "
        f"{spec.verified_by}, {spec.sob_verified_on}._",
        "",
    ]

    return "\n".join(lines)


def _benefit_sentence(benefit: Benefit, lang: str) -> str:
    """Render one benefit as a spoken sentence rather than a table row.

    A row like ``Specialist visit | $45 copay`` gives the hosts nothing to say.
    A sentence gives them a clause to expand on, which is what turns the Audio
    Overview into a conversation instead of a reading.
    """
    parts = benefit.localized(lang)
    s = _STRINGS[lang]

    # A rule is a condition on coverage, not a price. Forcing it through the
    # "you pay X" template produces sentences like "you pay not covered".
    if benefit.category == "rules":
        return f"**{parts['name']}.** {parts['detail'].rstrip('.')}."

    cost = parts["member_cost"].strip()
    normalized = cost.lower().rstrip(".")

    # $0 and "not covered" get their own clause. Slotting them into the
    # "you pay ___" template yields "you pay no cost to you", and the Spanish
    # equivalent is worse.
    if normalized in {"$0", "0", "$0.00"}:
        clause = s["zero_cost"]
    elif normalized in {"not covered", "no cubierto"}:
        clause = s["not_covered"]
    elif lang == "en":
        clause = f"you pay {cost}"
    else:
        clause = f"usted paga {cost}"

    sentence = f"**{parts['name']}** — {clause}."

    if parts["detail"]:
        sentence = f"{sentence} {parts['detail'].rstrip('.')}."

    return sentence


# ----------------------------------------------------------------------
# steering.txt — the Audio Overview customization prompt
# ----------------------------------------------------------------------


def _steering_prompt(spec: PlanSpec, lang: str) -> str:
    s = _STRINGS[lang]
    low, high = TARGET_MINUTES

    if lang == "en":
        return "\n".join(
            [
                f"Audience: {s['listener']}",
                "",
                f"Cover every benefit in the source, in the order it is written. "
                f"Aim for {low} to {high} minutes.",
                "",
                "Rules, in order of importance:",
                "1. Use ONLY the source document. If a benefit, dollar amount, "
                "doctor, drug, or pharmacy is not in the source, do not mention "
                "it — not as an example, not as a comparison, not as an aside.",
                "2. Say every dollar amount exactly as written. Never round, "
                "never say 'about', never estimate what something 'usually' costs.",
                "3. Read the required disclaimer word for word at the start and "
                "again at the end.",
                "4. Do not compare this plan to any other plan or carrier, and "
                "do not say it is better, cheaper, or the best choice.",
                "5. Do not tell the listener what care to get or what drug to "
                "take. Explain what the plan pays, not what they should do.",
                "6. If the source does not answer something a listener might "
                "ask, say the number on the back of the member ID card is where "
                "to get that answer.",
                "",
                "Tone: two people talking to a neighbor who just signed up. "
                "Warm, unhurried, plain words. No hype, no urgency, no sales.",
                f"Language: English.",
                "",
                f"Plan: {spec.display_name()}.",
            ]
        )

    return "\n".join(
        [
            f"Audiencia: {s['listener']}",
            "",
            f"Cubra cada beneficio del documento, en el orden en que esta "
            f"escrito. Apunte a {low} a {high} minutos.",
            "",
            "Reglas, en orden de importancia:",
            "1. Use SOLO el documento fuente. Si un beneficio, cantidad, medico, "
            "medicina o farmacia no esta en la fuente, no lo mencione — ni como "
            "ejemplo, ni como comparacion, ni de paso.",
            "2. Diga cada cantidad en dolares exactamente como esta escrita. "
            "Nunca redondee, nunca diga 'como', nunca estime.",
            "3. Lea el aviso obligatorio palabra por palabra al principio y otra "
            "vez al final.",
            "4. No compare este plan con ningun otro plan o compania, y no diga "
            "que es mejor, mas barato, ni la mejor opcion.",
            "5. No le diga a quien escucha que atencion buscar ni que medicina "
            "tomar. Explique lo que paga el plan, no lo que debe hacer.",
            "6. Si la fuente no responde algo, diga que el numero al reverso de "
            "la tarjeta de miembro es donde se obtiene esa respuesta.",
            "",
            "Tono: dos personas hablando con un vecino que acaba de inscribirse. "
            "Calido, sin prisa, palabras sencillas. Sin exageracion, sin urgencia, "
            "sin venta.",
            "Idioma: espanol neutro, apto para un publico caribeno y "
            "sudamericano en el sur de la Florida.",
            "",
            f"Plan: {spec.display_name()}.",
        ]
    )


# ----------------------------------------------------------------------
# delivery.md — what the member receives
# ----------------------------------------------------------------------


def _delivery_message(spec: PlanSpec, lang: str) -> str:
    """The signup message, with placeholders the send step fills in."""
    if lang == "en":
        body = [
            "# Delivery message (English)",
            "",
            "Placeholders: `{{first_name}}`, `{{audio_link}}`.",
            "",
            "## Text message",
            "",
            f"Hi {{{{first_name}}}}, this is Manny. Welcome to "
            f"{spec.plan_name}. I made you a short audio that walks through "
            "what your plan actually covers — you can listen in the car or "
            "before bed instead of reading the booklet.",
            "",
            "{{audio_link}}",
            "",
            "Your written Summary of Benefits is the official document; the "
            "audio is a plain-language walkthrough of it. Any question at all, "
            f"call me{_phone_suffix(spec.agent_phone)}.",
            "",
            "## Email subject",
            "",
            f"Your {spec.plan_name} benefits — a short audio walkthrough",
            "",
        ]
        return "\n".join(body)

    body = [
        "# Mensaje de entrega (Espanol)",
        "",
        "Marcadores: `{{first_name}}`, `{{audio_link}}`.",
        "",
        "## Mensaje de texto",
        "",
        f"Hola {{{{first_name}}}}, le habla Manny. Bienvenido a "
        f"{spec.plan_name}. Le prepare un audio corto que explica lo que su "
        "plan realmente cubre — puede escucharlo en el carro o antes de dormir "
        "en vez de leer el folleto.",
        "",
        "{{audio_link}}",
        "",
        "Su Resumen de Beneficios escrito es el documento oficial; el audio es "
        "una explicacion en palabras sencillas. Cualquier pregunta, "
        f"llameme{_phone_suffix(spec.agent_phone)}.",
        "",
        "## Asunto del correo",
        "",
        f"Sus beneficios de {spec.plan_name} — un audio corto que lo explica",
        "",
    ]
    return "\n".join(body)


def _phone_suffix(phone: str) -> str:
    return f" at {phone}" if phone else ""


# ----------------------------------------------------------------------
# review.md — the accuracy gate
# ----------------------------------------------------------------------


def _review_checklist(
    spec: PlanSpec, lang: str, gaps: List[str], unfilled: List[str]
) -> str:
    lines = [
        f"# Accuracy review — {spec.display_name()} ({lang})",
        "",
        "Nothing from this kit reaches a member until every box is checked and "
        "this file is signed. The audio is synthetic; the liability is not.",
        "",
        f"- Source of record: **{spec.sob_source}**",
        f"- Spec last verified: **{spec.sob_verified_on}** by **{spec.verified_by}**",
        "",
        "## Before generating audio",
        "",
        "- [ ] Every benefit in `source.md` matches the SOB line it came from, "
        "including the in-network column (not out-of-network).",
        "- [ ] The plan year in `source.md` is the year the member is enrolled in.",
        f"- [ ] The counties listed ({', '.join(spec.counties)}) are the counties "
        "this member lives in.",
        "- [ ] The disclaimer is the exact text the carrier requires for this "
        "material. See `docs/compliance.md`.",
        "",
        "## After generating audio, listen to the whole thing",
        "",
        "- [ ] Every dollar amount spoken matches `source.md`.",
        "- [ ] The hosts did not invent a benefit, a carrier, a drug, a doctor, "
        "or a comparison to another plan.",
        "- [ ] The disclaimer is audible at the start and the end.",
        "- [ ] No sentence tells the member what care to seek.",
        "- [ ] The hosts did not describe themselves as the plan or as Medicare.",
        "",
    ]

    if lang == "es":
        lines += [
            "## Spanish-specific",
            "",
            "- [ ] A native Spanish speaker listened end to end.",
            "- [ ] Benefit names were not left in English mid-sentence.",
            "",
        ]

    if unfilled:
        lines += [
            "## BLOCKED — figures nobody has read off the SOB",
            "",
            f"This kit contains `{SOB_PLACEHOLDER}` markers, so it is still a "
            "scaffold rather than a plan. Open the Summary of Benefits, type the "
            "real values into the plan spec, and rebuild. Delete rows this plan "
            "does not offer instead of marking them $0:",
            "",
        ]
        lines += [f"- {gap}" for gap in unfilled]
        lines += [""]

    if gaps:
        lines += [
            "## BLOCKED — untranslated fields",
            "",
            f"This kit contains `{TRANSLATION_MARKER}` markers. Fill these in on "
            "the plan spec and rebuild before generating audio:",
            "",
        ]
        lines += [f"- {gap}" for gap in gaps]
        lines.append("")

    lines += [
        "## Sign-off",
        "",
        "- Reviewed by: ______________________",
        "- Date: ______________________",
        "- Audio file: ______________________",
        "",
    ]

    return "\n".join(lines)
