"""Command-line interface.

Four commands:
  pumllint <paths> [options]          lint (default; no subcommand keyword)
  pumllint score <paths> [options]    maturity scoring (see SCORING.md)
  pumllint fix <paths> [options]      auto-fix mechanical findings
  pumllint schema <report>            print the JSON Schema for a -f json report

Exit codes: 0 = clean / at-or-above gate, 1 = lint violations at/above
--fail-on (lint), a diagram below --min-level or a --baseline regression
(score), or pending fixes under --dry-run (fix), 2 = usage/config error.
Designed to drop straight into a CI step.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config
from .engine import Engine, collect_files
from .model import SEVERITY_ORDER as _SEV_ORDER
from .model import Severity
from .reporters import get_reporter
from .rules import discover
from .schema import SCHEMA_NAMES, load_schema
from .scoring import score_groups
from .syntax import check_files


def _add_common_arguments(p: argparse.ArgumentParser) -> None:
    """Arguments shared by the lint and score commands."""
    p.add_argument("paths", nargs="*", help=".puml files or directories (recursed)")
    p.add_argument("-c", "--config", help="Config file (yaml/toml/json); auto-detected otherwise")
    p.add_argument(
        "--profile",
        help="Activate a rule profile (e.g. codegen); overrides `profile:` in the config",
    )
    p.add_argument(
        "-f", "--format", default="text",
        help="Output format: text | json | sonar | badge | html (badge/html: score only)",
    )
    p.add_argument("-o", "--output", help="Write report to file instead of stdout")
    p.add_argument(
        "--no-suppressions",
        action="store_true",
        help="Ignore inline \"' pumllint: disable\" comments (check everything)",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pumllint", description="Semantic linter for PlantUML diagrams")
    _add_common_arguments(p)
    p.add_argument(
        "--fail-on",
        default="major",
        choices=[s.value for s in _SEV_ORDER],
        help="Minimum severity that causes exit code 1 (default: major)",
    )
    p.add_argument("--list-rules", action="store_true", help="List available rules and exit")
    return p


def build_score_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pumllint score", description="Maturity scoring for PlantUML diagrams"
    )
    _add_common_arguments(p)
    p.add_argument(
        "--min-level",
        type=int,
        choices=[1, 2, 3, 4, 5],
        default=None,
        help="Exit non-zero if any scored diagram is below level N (CI gate)",
    )
    p.add_argument(
        "--check-syntax",
        action="store_true",
        help="Run the DIM-SYN gate (plantuml -checkonly) per file; failures force Level 1",
    )
    p.add_argument(
        "--baseline",
        metavar="FILE",
        help="Ratchet mode: compare per-diagram levels against FILE and exit 1 "
        "only on regression; records the baseline if FILE does not exist yet",
    )
    p.add_argument(
        "--update-baseline",
        action="store_true",
        help="Rewrite --baseline FILE with the current levels (accept the status quo)",
    )
    return p


def _apply_cli_overrides(config: dict, args: argparse.Namespace) -> dict:
    if args.no_suppressions:
        config = {**config, "suppressions": False}
    if args.profile:
        config = {**config, "profile": args.profile}
    return config


def build_fix_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pumllint fix",
        description="Auto-fix mechanical findings (add titles, name diagrams, "
        "declare implicit participants). Nothing is ever invented: only "
        "deterministic, semantics-preserving fixes are applied.",
    )
    p.add_argument("paths", nargs="*", help=".puml files or directories (recursed)")
    p.add_argument("-c", "--config", help="Config file (yaml/toml/json); auto-detected otherwise")
    p.add_argument(
        "--profile",
        help="Activate a rule profile (e.g. codegen); overrides `profile:` in the config",
    )
    p.add_argument(
        "--no-suppressions",
        action="store_true",
        help="Ignore inline \"' pumllint: disable\" comments (fix everything fixable)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the diff without writing; exit 1 if fixes are pending (CI check mode)",
    )
    return p


def build_schema_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pumllint schema",
        description="Print the JSON Schema (draft 2020-12) for a machine-readable "
        "report — the contract for `-f json` output. The badge and sonar formats "
        "follow shields.io's and SonarQube's own schemas and are not covered.",
    )
    p.add_argument(
        "report",
        choices=list(SCHEMA_NAMES),
        help="Which report: 'lint' (pumllint -f json) or 'score' (pumllint score -f json)",
    )
    p.add_argument("-o", "--output", help="Write the schema to a file instead of stdout")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "score":
        return _run_score(argv[1:])
    if argv and argv[0] == "fix":
        return _run_fix(argv[1:])
    if argv and argv[0] == "schema":
        return _run_schema(argv[1:])
    return _run_lint(argv)


def _run_lint(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)

    if args.list_rules:
        for rid, cls in sorted(discover().items()):
            scope = ",".join(cls.applies_to)
            prof = f" {{profile: {','.join(cls.profiles)}}}" if cls.profiles else ""
            print(f"{rid}  {cls.name:<30} [{cls.default_severity.value:<8}] {cls.dimension.value} ({scope}){prof} {cls.description}")
        return 0

    if not args.paths:
        print("error: no paths given (or use --list-rules)", file=sys.stderr)
        return 2

    try:
        config = _apply_cli_overrides(load_config(args.config), args)
        engine = Engine(config)
        violations = engine.lint_paths(args.paths)
        report = get_reporter(args.format).render(violations)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    _emit(report, args.output)

    threshold = _SEV_ORDER.index(Severity(args.fail_on))
    failing = [v for v in violations if _SEV_ORDER.index(v.severity) >= threshold]
    return 1 if failing else 0


def _run_score(argv: list[str]) -> int:
    args = build_score_parser().parse_args(argv)

    if not args.paths:
        print("error: no paths given", file=sys.stderr)
        return 2
    if args.update_baseline and not args.baseline:
        print("error: --update-baseline requires --baseline FILE", file=sys.stderr)
        return 2

    # The old baseline is loaded up front: the reporters annotate the report
    # with trend/deltas against it, and the ratchet compares against it later.
    baseline_data = None
    if args.baseline and Path(args.baseline).exists():
        try:
            from .baseline import load_baseline

            baseline_data = load_baseline(args.baseline)
        except (OSError, ValueError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

    try:
        config = _apply_cli_overrides(load_config(args.config), args)
        scoring_cfg = config.get("scoring") or {}
        engine = Engine(config)
        groups = engine.lint_paths_grouped(args.paths)
        syntax_results = None
        if args.check_syntax or scoring_cfg.get("syntax_gate"):
            syntax_results = check_files(
                collect_files(args.paths),
                command=scoring_cfg.get("syntax_command", "plantuml"),
            )
        results = score_groups(
            groups,
            config=scoring_cfg,
            syntax_results=syntax_results,
            engine=engine,
        )
        report = get_reporter(args.format).render_maturity(results, baseline=baseline_data)
    except (FileNotFoundError, ValueError, NotImplementedError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    _emit(report, args.output)

    gated = args.min_level is not None or args.baseline
    if gated and not results:
        print(
            "error: a gate was requested but no diagrams were scored "
            "(no parseable @startuml blocks under the given paths)",
            file=sys.stderr,
        )
        return 2

    failed = False
    if args.baseline:
        try:
            failed |= _apply_baseline(args, results, baseline_data)
        except OSError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
    if args.min_level is not None:
        failed |= any(r.level < args.min_level for _, r in results)
    return 1 if failed else 0


def _run_fix(argv: list[str]) -> int:
    args = build_fix_parser().parse_args(argv)
    if not args.paths:
        print("error: no paths given", file=sys.stderr)
        return 2

    try:
        config = _apply_cli_overrides(load_config(args.config), args)
        from .fixer import fix_paths

        results = fix_paths(args.paths, config)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    changed = [r for r in results if r.changed]
    if args.dry_run:
        import difflib

        for r in changed:
            diff = difflib.unified_diff(
                r.original.splitlines(keepends=True),
                r.fixed.splitlines(keepends=True),
                fromfile=str(r.path),
                tofile=f"{r.path} (fixed)",
            )
            sys.stdout.write("".join(diff))
        n = sum(len(r.fixes) for r in changed)
        print(
            f"would apply {n} fix(es) in {len(changed)} file(s)"
            if changed
            else "✔ Nothing to fix."
        )
        return 1 if changed else 0

    for r in changed:
        r.path.write_text(r.fixed, encoding="utf-8")
        for f in r.fixes:
            print(f"{r.path}:{f.line}: [{f.rule_id}] {f.description}")
    if not changed:
        print("✔ Nothing to fix.")
        return 0
    n = sum(len(r.fixes) for r in changed)
    remaining = Engine(config).lint_paths([r.path for r in changed])
    note = f"; {len(remaining)} finding(s) remain (run pumllint to see them)" if remaining else ""
    print(f"✔ Applied {n} fix(es) in {len(changed)} file(s){note}")
    return 0


def _run_schema(argv: list[str]) -> int:
    args = build_schema_parser().parse_args(argv)
    _emit(json.dumps(load_schema(args.report), indent=2), args.output)
    return 0


def _apply_baseline(args: argparse.Namespace, results, baseline_data) -> bool:
    """Record or ratchet against ``args.baseline``; True means regression.

    ``baseline_data`` is the already-loaded old baseline (None when the file
    did not exist) — with ``--update-baseline`` it fed the report's deltas
    before being rewritten here.
    """
    from .baseline import find_regressions, write_baseline

    path = Path(args.baseline)
    if args.update_baseline or baseline_data is None:
        write_baseline(path, results)
        verb = "updated" if args.update_baseline else "recorded"
        print(
            f"baseline: {verb} {len(results)} diagram level(s) in {path}",
            file=sys.stderr,
        )
        return False
    regressions = find_regressions(baseline_data, results)
    for reg in regressions:
        print(
            f"regression: {reg.key}: Level {reg.current_level} "
            f"(baseline {reg.baseline_level})",
            file=sys.stderr,
        )
    return bool(regressions)


def _emit(report: str, output: str | None) -> None:
    if output:
        Path(output).write_text(report + "\n", encoding="utf-8")
    else:
        print(report)


if __name__ == "__main__":
    raise SystemExit(main())
