"""Command-line interface.

Six commands:
  pumllint <paths> [options]          lint (default; no subcommand keyword)
  pumllint score <paths> [options]    maturity scoring (see SCORING.md)
  pumllint fix <paths> [options]      auto-fix mechanical findings
  pumllint trace <paths> [options]    requirement-coverage matrix
  pumllint schema <report>            print the JSON Schema for a -f json report
  pumllint lsp [options]              language server over stdio (editor use)

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
from .config import config_warnings, load_config
from .engine import PUML_EXTENSIONS, Engine, _rule_config, collect_files
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
        help="Rewrite --baseline FILE with the current levels (accept the status "
        "quo); entries of files not scored this run are kept while the file "
        "exists, so a partial run does not shrink FILE",
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
        "(*.md/*.txt/*.adoc/*.rst) with the pattern — each file's name is "
        "matched as well as its text, so filename-carried IDs are found",
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


def _run_lsp(argv: list[str]) -> int:
    """Serve diagnostics over LSP on stdio.

    The one subcommand that does not print a report: stdout carries the
    JSON-RPC stream, so everything here that would normally go through
    :func:`_out` goes to stderr instead, and :func:`pumllint.lsp.serve`
    rebinds ``sys.stdout`` for the same reason.
    """
    p = argparse.ArgumentParser(
        prog="pumllint lsp",
        description=(
            "Language Server Protocol front-end: publishes the same findings "
            "as `pumllint lint`, in the editor, as you type."
        ),
    )
    _add_version_argument(p)
    p.add_argument("--config", help="Path to a config file (default: auto-discover)")
    p.add_argument(
        "--profile",
        help="Activate a rule profile (e.g. codegen); overrides `profile:` in the config",
    )
    p.add_argument(
        "--no-suppressions",
        action="store_true",
        help="Ignore inline \"' pumllint: disable\" comments",
    )
    p.add_argument(
        "--fail-on",
        default="major",
        choices=[s.value for s in _SEV_ORDER],
        help=(
            "Minimum severity shown as an LSP Error — the same threshold and "
            "default as `pumllint lint --fail-on`, so the editor underlines "
            "exactly what CI would reject (default: major)"
        ),
    )
    args = p.parse_args(argv)

    from .lsp import serve

    try:
        return serve(
            config_path=args.config,
            fail_on=Severity(args.fail_on),
            profile=args.profile,
            no_suppressions=args.no_suppressions,
        )
    except KeyboardInterrupt:
        return 0


def main(argv: list[str] | None = None) -> int:
    # _SUBCOMMANDS is defined at the foot of this module, once every handler
    # exists; main() reads it at call time, so the order is not a problem.
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in _SUBCOMMANDS:
        return _SUBCOMMANDS[argv[0]](argv[1:])
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
    _warn_hidden_declarations(diagrams)
    return diagrams


def _declares_nothing_behind_includes(d) -> bool:
    """True when this diagram's declarations may hide behind ``!include``.

    The predicate behind the disclosure below: the diagram carries at least
    one include directive and declares no entity — the shape an ``!include``d
    shared-declaration file produces, since pumllint never expands the
    preprocessor.

    Two shapes qualify, and the second is the severe one:

    * the include hid *some* declarations — entities are named but every one
      of them is implicit;
    * the include hid *everything* — the diagram parses to no entity and no
      modelled content at all, so even the implicit names are gone.

    ``element_count`` is what separates that second shape from a diagram this
    predicate must stay quiet about: activity and use-case diagrams carry
    their content in nodes and links rather than in the participant/class/
    state entities counted here, so an activity diagram that includes a theme
    has no entities yet is fully modelled. Testing entities alone would call
    it undeclared and warn on a file whose content pumllint can see perfectly
    well.
    """
    if not any(x.kind == "include" for x in d.directives):
        return False
    entities = list(d.participants.values()) + list(d.classes.values()) + list(
        d.states.values()
    )
    if any(e.declared for e in entities):
        return False
    return bool(entities) or d.element_count == 0


def _warn_hidden_declarations(diagrams) -> None:
    """Disclose diagrams whose declarations pumllint cannot see.

    A diagram that ``!include``s its declarations parses with only implicit
    entities, so the cross-diagram (XD) identity checks and every
    declared-entity rule go silent — and the maturity score *rises* for it
    (docs/cross-diagram-relationships-evaluation.md, G3). A gate that scores
    a file it half-read must say so: warn on stderr, like the "nothing was
    checked" warning — never a finding, never an exit-code change.
    """
    hidden = [d for d in diagrams if _declares_nothing_behind_includes(d)]
    if not hidden:
        return
    shown = ", ".join(d.file_path for d in hidden[:5])
    more = f" (+{len(hidden) - 5} more)" if len(hidden) > 5 else ""
    _err(
        f"warning: {len(hidden)} diagram(s) contain '!include' but declare "
        f"nothing: {shown}{more} — pumllint does not expand preprocessor "
        "directives, so declarations inside included files are invisible to "
        "cross-diagram (XD) identity checks and declared-entity rules"
    )


def _load_config(path: str | None) -> dict:
    """``load_config`` plus the disclosure of keys nothing will read.

    Warnings go to stderr and never touch the exit code — the same posture as
    the "nothing was checked" and hidden-declarations disclosures. A config
    that names a rule which does not exist is silent otherwise, and issue #37
    records what that cost: a "rules disabled" control that was quietly
    running every rule.
    """
    cfg = load_config(path)
    known = {rid.lower() for rid in discover()} | {
        cls.name.lower() for cls in discover().values()
    }
    for warning in config_warnings(cfg, known):
        _err(warning)
    return cfg


def _list_rules(cfg: dict) -> int:
    """The catalog, annotated with what *this* config does to each rule.

    It used to print before the config was even loaded, so the output was
    byte-identical with and without ``-c`` or ``--profile`` — the one command
    whose job is "tell me what will run" could not answer the question. Each
    row now carries the effective severity and, where the config changes
    something, a state tag.

    Not annotated: DORMANT. Whether a convention-gated rule will actually do
    anything is decided by an early return inside its own ``check()`` body,
    which nothing declares; surfacing it needs the per-rule option
    declaration that config key-checking also wants, and the two belong in
    one change.
    """
    rules_cfg = cfg.get("rules", {}) or {}
    profile = cfg.get("profile")
    profiles_map = cfg.get("profiles") or {}
    profile_cfg = (profiles_map.get(profile) or {}) if profile else {}
    enabled_ids = {str(k).lower() for k in (profile_cfg.get("enable") or [])}
    escalate = {
        str(k).lower(): str(v).lower()
        for k, v in (profile_cfg.get("escalate") or {}).items()
    }
    for rid, cls in sorted(discover().items()):
        rule_cfg = _rule_config(rules_cfg, rid, cls.name)
        severity = cls.default_severity.value
        tags = []
        if rule_cfg is False:
            tags.append("disabled")
        elif cls.profiles and not (
            profile in cls.profiles or rid.lower() in enabled_ids or cls.name.lower() in enabled_ids
        ):
            tags.append(f"off (needs profile: {','.join(cls.profiles)})")
        override = (rule_cfg or {}).get("severity") if isinstance(rule_cfg, dict) else None
        for key in (rid.lower(), cls.name.lower()):
            if key in escalate:
                override = escalate[key]
        if override and str(override) != severity:
            tags.append(f"severity {severity} -> {override}")
            severity = str(override)
        scope = ",".join(cls.applies_to)
        prof = f" {{profile: {','.join(cls.profiles)}}}" if cls.profiles else ""
        state = f" [{'; '.join(tags)}]" if tags else ""
        _out(
            f"{rid}  {cls.name:<30} [{severity:<8}] {cls.dimension.value} "
            f"({scope}){prof}{state} {cls.description}"
        )
    return 0


def _run_lint(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)

    if args.list_rules:
        try:
            cfg = _apply_cli_overrides(_load_config(args.config), args)
        except (FileNotFoundError, ValueError) as e:
            _err(f"error: {e}")
            return 2
        return _list_rules(cfg)

    if not args.paths:
        _err("error: no paths given (or use --list-rules)")
        return 2

    try:
        config = _apply_cli_overrides(_load_config(args.config), args)
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
    # It is keyed the way the file stores keys (relative to the file's own
    # directory); once the run is scored it is re-keyed onto the run's own
    # keys, which is what every consumer looks up.
    from .baseline import compute_deltas, load_baseline, resolve_baseline

    baseline_data = None
    if args.baseline and Path(args.baseline).exists():
        try:
            baseline_data = load_baseline(args.baseline)
        except (OSError, ValueError) as e:
            _err(f"error: {e}")
            return 2
        if baseline_data.version == 1:
            _err(
                f"baseline: {args.baseline} is a version 1 file, keyed on the "
                "path spellings of the run that recorded it; --update-baseline "
                "(while the ratchet is green) rewrites it in the version 2 "
                "form, keyed relative to the file itself"
            )

    try:
        config = _apply_cli_overrides(_load_config(args.config), args)
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
        baseline_view = (
            resolve_baseline(baseline_data, results) if baseline_data is not None else None
        )
        report = get_reporter(args.format).render_maturity(
            results,
            baseline=baseline_view,
            syntax_gate_ran=syntax_results is not None,
        )
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

    if baseline_data and results and not compute_deltas(baseline_view, results):
        # A ratchet that matches nothing passes everything, by the "new
        # diagrams pass" rule — say so, since the likelier reading is that
        # the baseline was recorded elsewhere or has been moved.
        _err(
            f"warning: none of the {len(results)} scored diagram(s) has an entry "
            f"in {args.baseline} — they pass the ratchet as new since baseline; "
            "if they are not new, the baseline was recorded elsewhere or has "
            "been moved (its keys are paths relative to the file's directory)"
        )

    failed = False
    if args.baseline:
        try:
            failed |= _apply_baseline(args, results, baseline_view, baseline_data)
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
        config = _apply_cli_overrides(_load_config(args.config), args)
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
        config = _load_config(args.config)
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
        if not inventory:
            # Same contract as the lint path's "nothing was checked": an input
            # that yielded nothing is said out loud, on stderr, without moving
            # the exit code. Without it an empty inventory is indistinguishable
            # from a stale one, and every correct reference is reported as
            # unknown — blaming the diagram for the inventory's silence.
            sources = " and ".join(
                s
                for s in (
                    f"--requirements {args.requirements}" if args.requirements else "",
                    f"--requirements-scan {args.requirements_scan}"
                    if args.requirements_scan
                    else "",
                )
                if s
            )
            _err(
                f"warning: requirements inventory is empty ({sources} yielded no "
                f"IDs matching {pattern.pattern!r}) — "
                f"{len(result.unknown_references)} diagram reference(s) were "
                f"compared against nothing"
            )
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


def _apply_baseline(args: argparse.Namespace, results, baseline_view, previous) -> bool:
    """Record or ratchet against ``args.baseline``; True means regression.

    ``previous`` is the old baseline as loaded — keyed as the file keys
    itself, None when the file did not exist — and ``baseline_view`` the
    same re-keyed onto this run's keys, which fed the report's deltas. With
    ``--update-baseline`` the file is rewritten from the run merged into
    ``previous`` (``write_baseline``): files scored this run are replaced,
    files not scored are kept while they exist.
    """
    from .baseline import find_regressions, write_baseline

    path = Path(args.baseline)
    if previous is None:
        write_baseline(path, results)
        _err(f"baseline: recorded {len(results)} diagram level(s) in {path}")
        return False
    if args.update_baseline:
        kept, dropped = write_baseline(path, results, previous=previous)
        notes = []
        if kept:
            notes.append(f"{len(kept)} kept for files not scored this run")
        if dropped:
            notes.append(f"{len(dropped)} dropped for files not found relative to {path}")
        detail = f" ({', '.join(notes)})" if notes else ""
        _err(f"baseline: updated {len(results)} diagram level(s) in {path}{detail}")
        return False
    regressions = find_regressions(baseline_view, results)
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


# The subcommand keywords, mapped to their handlers — the single enumeration
# of the command set. main() dispatches through it and the packaging guards
# derive from it, rather than each freezing a list by hand: a hand-frozen
# list is how `lsp` came to ship absent from --help despite two tests whose
# docstrings promised the epilog "must name every command".
#
# Defined here, below every handler, so the table can name the functions
# directly instead of deferring the lookup through thunks.
#
# `lint` is deliberately absent: it is the default, reached without a
# keyword, so `pumllint lint x.puml` treats "lint" as a path.
_SUBCOMMANDS = {
    "score": _run_score,
    "fix": _run_fix,
    "trace": _run_trace,
    "schema": _run_schema,
    "lsp": _run_lsp,
}

# Commands the composite GitHub Action does not accept. A stdio language
# server has no meaning as a CI step, so action.yml rejects it with exit 2;
# naming the exclusion here keeps that deliberate and visible to the
# packaging guard, instead of looking like the omission it resembles.
_ACTION_EXCLUDED = frozenset({"lsp"})


if __name__ == "__main__":
    raise SystemExit(main())
