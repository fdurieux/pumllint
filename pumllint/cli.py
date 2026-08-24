"""Command-line interface.

Five commands:
  pumllint <paths> [options]          lint (default; no subcommand keyword)
  pumllint score <paths> [options]    maturity scoring (see SCORING.md)
  pumllint fix <paths> [options]      auto-fix mechanical findings
  pumllint trace <paths> [options]    requirement-coverage matrix
  pumllint schema <report>            print the JSON Schema for a -f json report

Each command has its own --help (e.g. `pumllint score --help`).

Exit codes: 0 = clean / at-or-above gate, 1 = lint violations at/above
--fail-on (lint), a diagram below --min-level or a --baseline regression
(score), pending fixes under --dry-run (fix), or a tripped --fail-on-*
trace gate, 2 = usage/config error. Designed to drop straight into a CI
step.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import load_config
from .engine import PUML_EXTENSIONS, Engine, collect_files
from .model import SEVERITY_ORDER as _SEV_ORDER
from .model import Severity
from .parser import parse_file
from .reporters import get_reporter
from .reporters.base import ASCII_GLYPHS, formats_supporting, sanitize_terminal
from .rules import discover
from .schema import SCHEMA_NAMES, load_schema
from .scoring import score_groups
from .syntax import check_files


# The commands/exit-codes overview from the module docstring, shown as the
# epilog of `pumllint --help` — the only place a user can discover the
# subcommands, since dispatch happens before argparse (see main()).
_COMMANDS_EPILOG = (__doc__ or "").partition("\n\n")[2]


def _add_version_argument(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--version", action="version", version=f"pumllint {__version__}"
    )


def _add_common_arguments(p: argparse.ArgumentParser, *, formats: list[str]) -> None:
    """Arguments shared by the lint and score commands. ``formats`` is the
    set the command's reporters actually support — enforced via choices."""
    _add_version_argument(p)
    p.add_argument("paths", nargs="*", help=".puml files or directories (recursed)")
    p.add_argument("-c", "--config", help="Config file (yaml/toml/json); auto-detected otherwise")
    p.add_argument(
        "--profile",
        help="Activate a rule profile (e.g. codegen); overrides `profile:` in the config",
    )
    p.add_argument(
        "-f", "--format", default="text", choices=formats,
        help="Output format (default: text)",
    )
    p.add_argument("-o", "--output", help="Write report to file instead of stdout")
    p.add_argument(
        "--no-suppressions",
        action="store_true",
        help="Ignore inline \"' pumllint: disable\" comments (check everything)",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pumllint",
        description="Semantic linter for PlantUML diagrams",
        epilog=_COMMANDS_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_common_arguments(p, formats=formats_supporting("render"))
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
    _add_common_arguments(p, formats=formats_supporting("render_maturity"))
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
    _add_version_argument(p)
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


def build_trace_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pumllint trace",
        description="Requirement-coverage matrix: which requirement IDs the "
        "diagrams realize, which IDs no diagram references, which diagrams "
        "reference nothing — plus references to IDs the inventory does not "
        "know. References are read from exactly the carriers GEN007 checks: "
        "the diagram name plus title/header/footer/caption/notes.",
    )
    _add_version_argument(p)
    p.add_argument("paths", nargs="*", help=".puml files or directories (recursed)")
    p.add_argument("-c", "--config", help="Config file (yaml/toml/json); auto-detected otherwise")
    p.add_argument(
        "--pattern",
        help="Requirement-ID regex (e.g. 'REQ-\\d+|ADR-\\d+'); defaults to the "
        "configured rules.requirement-link pattern",
    )
    p.add_argument(
        "--requirements",
        metavar="FILE",
        help="Inventory list: one ID per line (text), or a JSON/YAML array of "
        "IDs — strings or objects with an 'id' (extra snapshot columns are "
        "ignored); may be combined with --requirements-scan",
    )
    p.add_argument(
        "--requirements-scan",
        metavar="PATH",
        help="Build the inventory by scanning a docs file or tree "
        "(*.md/*.txt/*.adoc/*.rst) with the pattern",
    )
    p.add_argument(
        "-f", "--format", default="text", choices=formats_supporting("render_trace"),
        help="Output format (default: text)",
    )
    p.add_argument("-o", "--output", help="Write report to file instead of stdout")
    p.add_argument(
        "--fail-on-uncovered",
        action="store_true",
        help="Exit 1 if any inventory ID is referenced by no diagram",
    )
    p.add_argument(
        "--fail-on-unlinked",
        action="store_true",
        help="Exit 1 if any diagram references no requirement ID",
    )
    p.add_argument(
        "--fail-on-unknown-ref",
        action="store_true",
        help="Exit 1 if any diagram references an ID missing from the inventory",
    )
    return p


def build_schema_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pumllint schema",
        description="Print the JSON Schema (draft 2020-12) for a machine-readable "
        "report — the contract for `-f json` output. The badge and sonar formats "
        "follow shields.io's and SonarQube's own schemas and are not covered.",
    )
    _add_version_argument(p)
    p.add_argument(
        "report",
        choices=list(SCHEMA_NAMES),
        help="Which report: 'lint' (pumllint -f json), 'score' (pumllint "
        "score -f json) or 'trace' (pumllint trace -f json)",
    )
    p.add_argument("-o", "--output", help="Write the schema to a file instead of stdout")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "score":
        return _run_score(argv[1:])
    if argv and argv[0] == "fix":
        return _run_fix(argv[1:])
    if argv and argv[0] == "trace":
        return _run_trace(argv[1:])
    if argv and argv[0] == "schema":
        return _run_schema(argv[1:])
    return _run_lint(argv)


def _encode_safely(text: str, stream) -> str:
    """*text* rendered so writing it to *stream* cannot raise.

    Windows attaches the console's UTF-8 codec only to a real console: the
    moment output is redirected, piped or captured, ``sys.stdout`` switches to
    the ANSI code page (cp1252 and friends), where the report's ✔/✖ raise
    UnicodeEncodeError — losing the entire report and inverting the exit code.

    Reconfiguring the stream to UTF-8 would be the obvious fix and is the
    wrong one: PowerShell 5.1 re-decodes a native program's bytes with
    ``[Console]::OutputEncoding`` (cp850/437 by default), so it trades a
    crash for mojibake. Downgrading only what the destination genuinely
    cannot encode leaves POSIX output byte-identical.
    """
    encoding = getattr(stream, "encoding", None)
    if not encoding:  # StringIO under test: assume it takes anything
        return text
    try:
        text.encode(encoding)
        return text  # the common case, POSIX included: byte-identical
    except UnicodeEncodeError:
        pass
    except LookupError:  # the stream names a codec Python does not have
        encoding = "ascii"

    # Substitute per character, not per report: an é or an em dash the code
    # page renders perfectly must survive untouched — only the characters it
    # genuinely cannot encode are replaced, decorations by their ASCII
    # equivalent and everything else (a CJK participant name, say) by a
    # visible escape.
    out = []
    for ch in text:
        try:
            ch.encode(encoding)
        except UnicodeEncodeError:
            out.append(
                ASCII_GLYPHS.get(ch)
                or ch.encode(encoding, "backslashreplace").decode(encoding)
            )
        else:
            out.append(ch)
    return "".join(out)


def _out(text: str = "") -> None:
    print(_encode_safely(text, sys.stdout))


def _err(text: str) -> None:
    print(_encode_safely(text, sys.stderr), file=sys.stderr)


def _collect_input_files(paths: list[str]) -> list[Path]:
    """Diagram files under *paths*, warning when the search comes up empty.

    A linter that silently reports "no issues" because it looked at nothing
    is worse than one that fails: say so on stderr, so a mistyped path or a
    directory holding no diagram sources is visible in the CI log.
    """
    files = collect_files(paths)
    if not files:
        where = ", ".join(str(p) for p in paths)
        _err(
            f"warning: no PlantUML files found in {where} "
            f"(looked for {', '.join(PUML_EXTENSIONS)}) — nothing was checked"
        )
    return files


def _parse_input_files(files: list[Path]):
    """Parse *files*, warning about any that yielded no diagram."""
    diagrams = [d for f in files for d in parse_file(f)]
    parsed = {d.file_path for d in diagrams}
    # .iuml is the include-fragment extension: having no @startuml of its own
    # is what such a file is for, so it is not worth a warning.
    empty = [
        f
        for f in files
        if f.as_posix() not in parsed and f.suffix.lower() != ".iuml"
    ]
    if empty:
        shown = ", ".join(str(f) for f in empty[:5])
        more = f" (+{len(empty) - 5} more)" if len(empty) > 5 else ""
        _err(
            f"warning: {len(empty)} file(s) contained no @startuml block and "
            f"were not checked: {shown}{more} — pumllint lints "
            "@startuml…@enduml sources; @startmindmap / @startjson / "
            "@startsalt / @startgantt blocks are not linted"
        )
    return diagrams


def _run_lint(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)

    if args.list_rules:
        for rid, cls in sorted(discover().items()):
            scope = ",".join(cls.applies_to)
            prof = f" {{profile: {','.join(cls.profiles)}}}" if cls.profiles else ""
            _out(f"{rid}  {cls.name:<30} [{cls.default_severity.value:<8}] {cls.dimension.value} ({scope}){prof} {cls.description}")
        return 0

    if not args.paths:
        _err("error: no paths given (or use --list-rules)")
        return 2

    try:
        config = _apply_cli_overrides(load_config(args.config), args)
        engine = Engine(config)
        violations = engine.lint_diagrams(_parse_input_files(_collect_input_files(args.paths)))
        report = get_reporter(args.format).render(violations)
    except (FileNotFoundError, ValueError) as e:
        _err(f"error: {e}")
        return 2

    _emit(report, args.output, args.format)

    threshold = _SEV_ORDER.index(Severity(args.fail_on))
    failing = [v for v in violations if _SEV_ORDER.index(v.severity) >= threshold]
    return 1 if failing else 0


def _run_score(argv: list[str]) -> int:
    args = build_score_parser().parse_args(argv)

    if not args.paths:
        _err("error: no paths given")
        return 2
    if args.update_baseline and not args.baseline:
        _err("error: --update-baseline requires --baseline FILE")
        return 2

    # The old baseline is loaded up front: the reporters annotate the report
    # with trend/deltas against it, and the ratchet compares against it later.
    baseline_data = None
    if args.baseline and Path(args.baseline).exists():
        try:
            from .baseline import load_baseline

            baseline_data = load_baseline(args.baseline)
        except (OSError, ValueError) as e:
            _err(f"error: {e}")
            return 2

    try:
        config = _apply_cli_overrides(load_config(args.config), args)
        scoring_cfg = config.get("scoring") or {}
        engine = Engine(config)
        files = _collect_input_files(args.paths)
        groups = engine.lint_diagrams_grouped(_parse_input_files(files))
        syntax_results = None
        if args.check_syntax or scoring_cfg.get("syntax_gate"):
            syntax_results = check_files(
                files,
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
        _err(f"error: {e}")
        return 2

    _emit(report, args.output, args.format)

    gated = args.min_level is not None or args.baseline
    if gated and not results:
        _err(
            "error: a gate was requested but no diagrams were scored "
            "(no parseable @startuml blocks under the given paths)"
        )
        return 2

    failed = False
    if args.baseline:
        try:
            failed |= _apply_baseline(args, results, baseline_data)
        except OSError as e:
            _err(f"error: {e}")
            return 2
    if args.min_level is not None:
        failed |= any(r.level < args.min_level for _, r in results)
    return 1 if failed else 0


def _run_fix(argv: list[str]) -> int:
    args = build_fix_parser().parse_args(argv)
    if not args.paths:
        _err("error: no paths given")
        return 2

    try:
        config = _apply_cli_overrides(load_config(args.config), args)
        from .fixer import fix_paths

        results = fix_paths(_collect_input_files(args.paths), config)
    except (FileNotFoundError, ValueError) as e:
        _err(f"error: {e}")
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
            sys.stdout.write(_encode_safely("".join(diff), sys.stdout))
        n = sum(len(r.fixes) for r in changed)
        _out(
            f"would apply {n} fix(es) in {len(changed)} file(s)"
            if changed
            else "✔ Nothing to fix."
        )
        return 1 if changed else 0

    for r in changed:
        # newline="" or Windows text mode re-translates every "\n", turning the
        # CRLF apply_fixes deliberately produced into "\r\r\n" and rewriting
        # every line of an LF file.
        r.path.write_text(r.fixed, encoding=r.encoding, newline="")
        for f in r.fixes:
            _out(sanitize_terminal(f"{r.path}:{f.line}: [{f.rule_id}] {f.description}"))
    if not changed:
        _out("✔ Nothing to fix.")
        return 0
    n = sum(len(r.fixes) for r in changed)
    remaining = Engine(config).lint_paths([r.path for r in changed])
    note = f"; {len(remaining)} finding(s) remain (run pumllint to see them)" if remaining else ""
    _out(f"✔ Applied {n} fix(es) in {len(changed)} file(s){note}")
    return 0


def _run_trace(argv: list[str]) -> int:
    args = build_trace_parser().parse_args(argv)
    if not args.paths:
        _err("error: no paths given")
        return 2
    if not args.requirements and not args.requirements_scan:
        _err(
            "error: no inventory given — pass --requirements FILE and/or "
            "--requirements-scan PATH"
        )
        return 2

    from .parser import parse_file
    from .trace import (
        build_matrix,
        compile_pattern,
        load_inventory,
        pattern_from_config,
        scan_inventory,
    )

    try:
        config = load_config(args.config)
        raw = args.pattern or pattern_from_config(config)
        if not raw:
            _err(
                "error: no requirement-ID pattern — pass --pattern "
                "(e.g. 'REQ-\\d+|ADR-\\d+'), or configure "
                "rules.requirement-link.pattern"
            )
            return 2
        origin = (
            "--pattern" if args.pattern else "config rules.requirement-link.pattern"
        )
        pattern = compile_pattern(raw, origin)
        inventory: list[str] = []
        if args.requirements:
            inventory.extend(
                load_inventory(
                    args.requirements,
                    on_warning=lambda m: _err(f"warning: {m}"),
                )
            )
        if args.requirements_scan:
            inventory.extend(scan_inventory(args.requirements_scan, pattern))
        inventory = list(dict.fromkeys(inventory))  # union, first-seen order
        diagrams = _parse_input_files(_collect_input_files(args.paths))
        result = build_matrix(diagrams, inventory, pattern)
        report = get_reporter(args.format).render_trace(result)
    except (FileNotFoundError, ValueError, NotImplementedError) as e:
        _err(f"error: {e}")
        return 2

    _emit(report, args.output, args.format)

    failed = (
        (args.fail_on_uncovered and any(not r.covered for r in result.requirements))
        or (args.fail_on_unlinked and bool(result.unlinked_diagrams))
        or (args.fail_on_unknown_ref and bool(result.unknown_references))
    )
    return 1 if failed else 0


def _run_schema(argv: list[str]) -> int:
    args = build_schema_parser().parse_args(argv)
    _emit(json.dumps(load_schema(args.report), indent=2), args.output, "json")
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
        _err(f"baseline: {verb} {len(results)} diagram level(s) in {path}")
        return False
    regressions = find_regressions(baseline_data, results)
    for reg in regressions:
        # reg.key embeds the diagram name (file content) — sanitize like the
        # text reporter does.
        _err(
            sanitize_terminal(
                f"regression: {reg.key}: Level {reg.current_level} "
                f"(baseline {reg.baseline_level})"
            )
        )
    return bool(regressions)


def _emit(report: str, output: str | None, fmt: str = "text") -> None:
    """Write *report* to a file or stdout.

    A machine format goes to stdout as UTF-8 bytes rather than through the
    text layer: json/sonar/badge/html are consumed by another program, and a
    console code page must not get the chance to substitute characters inside
    them. Only the human-readable text report is downgraded when the
    destination cannot render it.
    """
    if output:
        Path(output).write_text(report + "\n", encoding="utf-8", newline="")
        return
    buffer = getattr(sys.stdout, "buffer", None)
    if fmt != "text" and buffer is not None:
        sys.stdout.flush()
        buffer.write((report + "\n").encode("utf-8"))
        buffer.flush()
        return
    _out(report)


if __name__ == "__main__":
    raise SystemExit(main())
