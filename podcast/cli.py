"""Command line for the benefits podcast pipeline.

    python podcast/cli.py build                            # build every kit
    python podcast/cli.py --target plans/h1234-001-2026.json build --lang es
    python podcast/cli.py status
    python podcast/cli.py record-audio h1234-001-2026 en --file audio/....m4a
    python podcast/cli.py approve h1234-001-2026 en --by "Manny Leon"
    python podcast/cli.py publish h1234-001-2026 en --link https://...
    python podcast/cli.py check h1234-001-2026 en          # safe to send?

The steps between ``build`` and ``record-audio`` happen by hand in NotebookLM;
see ``docs/notebooklm-workflow.md``.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import List, Sequence

from catalog import Catalog, CatalogError
from episode import build_kit
from planspec import PlanSpec, PlanSpecError, SUPPORTED_LANGUAGES, load_all
from skeleton import SOB_PLACEHOLDER, blank_spec

HERE = Path(__file__).resolve().parent
DEFAULT_PLANS = HERE / "plans"
DEFAULT_KITS = HERE / "kits"
DEFAULT_CATALOG = HERE / "catalog.json"

# Manny's home service area. Benefits vary by county inside one contract, so
# this is a starting point to correct per plan, not a safe default to ignore.
DEFAULT_COUNTIES = ("Miami-Dade", "Broward")


def _portable(path: Path) -> str:
    """Store paths relative to ``podcast/`` so the catalog survives a clone."""
    try:
        return str(path.resolve().relative_to(HERE))
    except ValueError:
        return str(path)


def _load_specs(target: Path) -> List[PlanSpec]:
    if target.is_dir():
        return load_all(target)
    return [PlanSpec.load(target)]


def cmd_new_plan(args: argparse.Namespace) -> int:
    spec = blank_spec(
        plan_id=args.plan_id,
        plan_name=args.name,
        carrier=args.carrier,
        plan_year=args.year,
        plan_type=args.type,
        counties=args.county or list(DEFAULT_COUNTIES),
        verified_by=args.by,
        verified_on=args.on,
    )

    out_dir = Path(args.out)
    destination = out_dir / f"{spec.slug()}.json"
    if destination.exists() and not args.force:
        print(
            f"error: {destination} already exists; pass --force to overwrite it",
            file=sys.stderr,
        )
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    spec.save(destination)

    gaps = len(spec.untranslated())
    print(f"scaffolded {spec.display_name()}")
    print(f"  -> {destination}")
    print(f"  {len(spec.benefits)} rows, {gaps} field(s) to fill in")
    print(
        f"\nNext: open it against the Summary of Benefits and replace every "
        f"{SOB_PLACEHOLDER}.\nDelete rows this plan does not offer rather than "
        f"marking them $0. Then `build`."
    )
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    specs = _load_specs(Path(args.target))
    catalog = Catalog.load(args.catalog)
    languages = args.lang or list(SUPPORTED_LANGUAGES)

    blocked = 0
    for spec in specs:
        for lang in languages:
            kit = build_kit(spec, lang)
            directory = kit.write(args.out)
            catalog.register_kit(spec, lang, _portable(directory))

            if kit.complete:
                print(f"built  {kit.slug}/{lang}  -> {directory}")
            else:
                blocked += 1
                reasons = []
                if kit.unfilled:
                    reasons.append(f"{len(kit.unfilled)} unread from the SOB")
                if kit.translation_gaps:
                    reasons.append(f"{len(kit.translation_gaps)} untranslated")
                print(
                    f"BLOCKED {kit.slug}/{lang} -> {directory} "
                    f"({', '.join(reasons)}; see review.md)"
                )

    catalog.save()

    if blocked:
        print(
            f"\n{blocked} kit(s) still have blocking fields. Do not record "
            f"audio for those until the plan spec is filled in.",
            file=sys.stderr,
        )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    specs = _load_specs(Path(args.target))
    catalog = Catalog.load(args.catalog)

    report = catalog.status_report(specs)
    if not report:
        print("Nothing built yet.")
        return 0

    for line in report:
        print(line)
    return 0


def cmd_record_audio(args: argparse.Namespace) -> int:
    catalog = Catalog.load(args.catalog)
    entry = catalog.record_audio(args.slug, args.lang, args.file, args.link or "")
    catalog.save()
    print(f"{entry.key}: {entry.status}")
    print("Next: listen to it end to end against review.md, then `approve`.")
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    catalog = Catalog.load(args.catalog)
    entry = catalog.approve(args.slug, args.lang, args.by, args.on)
    catalog.save()
    print(f"{entry.key}: {entry.status} by {entry.approved_by} on {entry.approved_on}")
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    catalog = Catalog.load(args.catalog)
    entry = catalog.publish(args.slug, args.lang, args.on, args.link or "")
    catalog.save()
    print(f"{entry.key}: {entry.status} -> {entry.audio_link}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    specs = _load_specs(Path(args.target))
    catalog = Catalog.load(args.catalog)

    matches = [s for s in specs if s.slug() == args.slug]
    if not matches:
        print(f"No plan spec with slug {args.slug!r} in {args.target}", file=sys.stderr)
        return 1

    entry = catalog.deliverable(matches[0], args.lang)
    print(f"OK — {entry.key} is safe to send: {entry.audio_link}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="podcast", description="MedicareManny plan benefits podcast pipeline"
    )
    parser.add_argument(
        "--catalog", default=str(DEFAULT_CATALOG), help="catalog JSON path"
    )
    parser.add_argument(
        "--target",
        default=str(DEFAULT_PLANS),
        help="plan spec file or directory (default: podcast/plans)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser(
        "new-plan", help="scaffold a blank plan spec ready to fill from an SOB"
    )
    p_new.add_argument("--plan-id", required=True, help="contract-PBP, e.g. H1036-001")
    p_new.add_argument("--name", required=True, help="marketed plan name")
    p_new.add_argument("--carrier", required=True)
    p_new.add_argument("--year", required=True, type=int, help="contract year")
    p_new.add_argument("--type", required=True, help="HMO, PPO, HMO D-SNP, PDP, ...")
    p_new.add_argument(
        "--county",
        action="append",
        help=f"service-area county (repeatable; default: {', '.join(DEFAULT_COUNTIES)})",
    )
    p_new.add_argument("--by", default="Manny Leon", help="who will verify the spec")
    p_new.add_argument("--on", default=date.today().isoformat())
    p_new.add_argument("--out", default=str(DEFAULT_PLANS), help="plans directory")
    p_new.add_argument(
        "--force", action="store_true", help="overwrite an existing spec"
    )
    p_new.set_defaults(func=cmd_new_plan)

    p_build = sub.add_parser("build", help="generate episode kits")
    p_build.add_argument(
        "--lang",
        action="append",
        choices=list(SUPPORTED_LANGUAGES),
        help="language to build (repeatable; default: all)",
    )
    p_build.add_argument("--out", default=str(DEFAULT_KITS), help="kit output root")
    p_build.set_defaults(func=cmd_build)

    p_status = sub.add_parser("status", help="show episode status, flagging stale audio")
    p_status.set_defaults(func=cmd_status)

    p_audio = sub.add_parser("record-audio", help="record the generated NotebookLM file")
    p_audio.add_argument("slug")
    p_audio.add_argument("lang", choices=list(SUPPORTED_LANGUAGES))
    p_audio.add_argument("--file", required=True, help="path to the downloaded audio")
    p_audio.add_argument("--link", help="hosted URL, if it already has one")
    p_audio.set_defaults(func=cmd_record_audio)

    p_approve = sub.add_parser("approve", help="record the accuracy sign-off")
    p_approve.add_argument("slug")
    p_approve.add_argument("lang", choices=list(SUPPORTED_LANGUAGES))
    p_approve.add_argument("--by", required=True, help="who listened to it")
    p_approve.add_argument("--on", default=date.today().isoformat())
    p_approve.set_defaults(func=cmd_approve)

    p_publish = sub.add_parser("publish", help="make an approved episode deliverable")
    p_publish.add_argument("slug")
    p_publish.add_argument("lang", choices=list(SUPPORTED_LANGUAGES))
    p_publish.add_argument("--link", help="member-facing audio URL")
    p_publish.add_argument("--on", default=date.today().isoformat())
    p_publish.set_defaults(func=cmd_publish)

    p_check = sub.add_parser("check", help="is this episode safe to send?")
    p_check.add_argument("slug")
    p_check.add_argument("lang", choices=list(SUPPORTED_LANGUAGES))
    p_check.set_defaults(func=cmd_check)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return int(args.func(args))
    except (PlanSpecError, CatalogError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
