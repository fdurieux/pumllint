"""Command-line interface.

Two commands:
  pumllint <paths> [options]          lint (default; no subcommand keyword)
  pumllint score <paths> [options]    maturity scoring (see SCORING.md)

Exit codes: 0 = clean / at-or-above gate, 1 = lint violations at/above
--fail-on (lint) or a diagram below --min-level (score), 2 = usage/config error.
Designed to drop straight into a CI step.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .engine import Engine, collect_files
from .model import Severity
from .reporters import get_reporter
from .rules import discover
from .scoring import score_groups
from .syntax import check_files

_SEV_ORDER = [Severity.INFO, Severity.MINOR, Severity.MAJOR, Severity.CRITICAL, Severity.BLOCKER]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pumllint", description="Semantic linter for PlantUML diagrams")
    p.add_argument("paths", nargs="*", help=".puml files or directories (recursed)")
    p.add_argument("-c", "--config", help="Config file (yaml/toml/json); auto-detected otherwise")
    p.add_argument(
        "--profile",
        help="Activate a rule profile (e.g. codegen); overrides `profile:` in the config",
    )
    p.add_argument("-f", "--format", default="text", help="Output format: text | json | sonar")
    p.add_argument("-o", "--output", help="Write report to file instead of stdout")
    p.add_argument(
        "--fail-on",
        default="major",
        choices=[s.value for s in _SEV_ORDER],
        help="Minimum severity that causes exit code 1 (default: major)",
    )
    p.add_argument("--list-rules", action="store_true", help="List available rules and exit")
    p.add_argument(
        "--no-suppressions",
        action="store_true",
        help="Ignore inline \"' pumllint: disable\" comments (report everything)",
    )
    return p


def build_score_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pumllint score", description="Maturity scoring for PlantUML diagrams"
    )
    p.add_argument("paths", nargs="*", help=".puml files or directories (recursed)")
    p.add_argument("-c", "--config", help="Config file (yaml/toml/json); auto-detected otherwise")
    p.add_argument(
        "--profile",
        help="Activate a rule profile (e.g. codegen); overrides `profile:` in the config",
    )
    p.add_argument("-f", "--format", default="text", help="Output format: text | json | sonar")
    p.add_argument("-o", "--output", help="Write report to file instead of stdout")
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
        "--no-suppressions",
        action="store_true",
        help="Ignore inline \"' pumllint: disable\" comments (score everything)",
    )
    return p


def _apply_cli_overrides(config: dict, args: argparse.Namespace) -> dict:
    if args.no_suppressions:
        config = {**config, "suppressions": False}
    if args.profile:
        config = {**config, "profile": args.profile}
    return config


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "score":
        return _run_score(argv[1:])
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
        report = get_reporter(args.format).render_maturity(results)
    except (FileNotFoundError, ValueError, NotImplementedError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    _emit(report, args.output)

    if args.min_level is not None:
        if not results:
            print(
                "error: --min-level given but no diagrams were scored "
                "(no parseable @startuml blocks under the given paths)",
                file=sys.stderr,
            )
            return 2
        below = [r for _, r in results if r.level < args.min_level]
        return 1 if below else 0
    return 0


def _emit(report: str, output: str | None) -> None:
    if output:
        Path(output).write_text(report + "\n", encoding="utf-8")
    else:
        print(report)


if __name__ == "__main__":
    raise SystemExit(main())
