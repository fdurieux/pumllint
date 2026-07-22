"""Command-line interface.

Exit codes: 0 = clean, 1 = violations at/above --fail-on threshold,
2 = usage/config error. Designed to drop straight into a CI step.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .engine import Engine
from .model import Severity
from .reporters import get_reporter
from .rules import discover

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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list_rules:
        for rid, cls in sorted(discover().items()):
            scope = ",".join(cls.applies_to)
            prof = f" {{profile: {','.join(cls.profiles)}}}" if cls.profiles else ""
            print(f"{rid}  {cls.name:<30} [{cls.default_severity.value:<8}] ({scope}){prof} {cls.description}")
        return 0

    if not args.paths:
        print("error: no paths given (or use --list-rules)", file=sys.stderr)
        return 2

    try:
        config = load_config(args.config)
        if args.no_suppressions:
            config = {**config, "suppressions": False}
        if args.profile:
            config = {**config, "profile": args.profile}
        engine = Engine(config)
        violations = engine.lint_paths(args.paths)
        report = get_reporter(args.format).render(violations)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if args.output:
        Path(args.output).write_text(report + "\n", encoding="utf-8")
    else:
        print(report)

    threshold = _SEV_ORDER.index(Severity(args.fail_on))
    failing = [v for v in violations if _SEV_ORDER.index(v.severity) >= threshold]
    return 1 if failing else 0


if __name__ == "__main__":
    raise SystemExit(main())
