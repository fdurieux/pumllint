"""Lint engine: wires config, rule registry, parser and reporters together."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from .model import Diagram, Severity, Violation
from .parser import parse_file
from .rules import CrossDiagramRule, Rule, discover

_SORT_KEY = lambda v: (v.file_path, v.line, v.rule_id)  # noqa: E731


class Engine:
    def __init__(self, config: dict | None = None):
        self.config = config or {}
        rules_cfg: dict = self.config.get("rules", {})

        # Profile selection: `profile:` names the active profile; the
        # `profiles:` map may extend it with enable-lists (activate
        # profile-gated rules by id/name) and escalations (severity overrides
        # for any rule, e.g. SEQ001: blocker).
        profile: str | None = self.config.get("profile")
        self.profile = profile  # source of truth for scoring's C7 profile cap
        profiles_map: dict = self.config.get("profiles") or {}
        profile_cfg: dict = (profiles_map.get(profile) or {}) if profile else {}
        enable_keys = {str(k).lower() for k in (profile_cfg.get("enable") or [])}
        escalate = {
            str(k).lower(): str(v).lower()
            for k, v in (profile_cfg.get("escalate") or {}).items()
        }

        self.rules: list[Rule] = []
        self.cross_rules: list[CrossDiagramRule] = []
        # Per-diagram counts of findings hidden by inline suppressions in the
        # most recent grouped run, keyed by id(diagram) — see suppressed_count.
        self._suppressed_counts: dict[int, int] = {}
        for rule_id, cls in sorted(discover().items()):
            if cls.profiles and not (
                (profile is not None and profile in cls.profiles)
                or rule_id.lower() in enable_keys
                or cls.name.lower() in enable_keys
            ):
                continue  # profile-gated rule, profile not active
            cfg = _rule_config(rules_cfg, rule_id, cls.name)
            if cfg is False:
                continue  # disabled
            cfg = cfg if isinstance(cfg, dict) else {}
            rule = cls(cfg)
            esc = escalate.get(rule_id.lower()) or escalate.get(cls.name.lower())
            if esc:  # profile escalation wins over rule-level severity
                rule.severity = Severity(esc)
            if isinstance(rule, CrossDiagramRule):
                self.cross_rules.append(rule)
            else:
                self.rules.append(rule)

    # -- running ----------------------------------------------------------
    def lint_diagram(self, diagram: Diagram) -> list[Violation]:
        """Violations for one diagram, sorted by (file, line, rule id).

        The single-diagram unit the maturity scorer consumes; the flat and
        grouped accessors below both build on it.
        """
        violations, _ = self._lint_diagram(diagram)
        return violations

    def _lint_diagram(self, diagram: Diagram) -> tuple[list[Violation], int]:
        """(kept violations, count of findings hidden by inline suppressions)."""
        honor_suppressions = self.config.get("suppressions", True) is not False
        violations: list[Violation] = []
        suppressed = 0
        for rule in self.rules:
            if "*" not in rule.applies_to and diagram.diagram_type not in rule.applies_to:
                continue
            for v in rule.check(diagram):
                if honor_suppressions and _is_suppressed(diagram, rule, v):
                    suppressed += 1
                    continue
                violations.append(v)
        return sorted(violations, key=_SORT_KEY), suppressed

    def lint_diagrams(self, diagrams: Iterable[Diagram]) -> list[Violation]:
        # Flatten the grouped result so flat and grouped output are identical
        # by construction, not by parallel implementations.
        violations = [v for _, vs in self.lint_diagrams_grouped(diagrams) for v in vs]
        return sorted(violations, key=_SORT_KEY)

    def lint_diagrams_grouped(
        self, diagrams: Iterable[Diagram]
    ) -> list[tuple[Diagram, list[Violation]]]:
        """One (diagram, its-violations) pair per diagram — the per-unit input
        for maturity scoring. Flattening this yields the same set as
        :meth:`lint_diagrams`; cross-diagram findings land in the group of the
        diagram that owns their file/line. Also records how many findings each
        diagram's inline suppressions hid — see :meth:`suppressed_count`."""
        diagrams = list(diagrams)
        cross, cross_suppressed = self._cross_violations(diagrams)
        counts: dict[int, int] = {}
        groups: list[tuple[Diagram, list[Violation]]] = []
        for d in diagrams:
            vs, suppressed = self._lint_diagram(d)
            counts[id(d)] = suppressed + cross_suppressed.get(id(d), 0)
            extra = cross.get(id(d))
            if extra:
                vs = sorted(vs + extra, key=_SORT_KEY)
            groups.append((d, vs))
        self._suppressed_counts = counts
        return groups

    def suppressed_count(self, diagram: Diagram) -> int:
        """Findings hidden by this diagram's inline suppressions in the most
        recent grouped run (0 for diagrams outside that run).

        Suppressed findings are excluded from the group's violations — and so
        from lint output and maturity scores. Reporters surface this count so
        a suppressed-clean diagram stays distinguishable from a clean one.
        """
        return self._suppressed_counts.get(id(diagram), 0)

    def _cross_violations(
        self, diagrams: list[Diagram]
    ) -> tuple[dict[int, list[Violation]], dict[int, int]]:
        """Cross-diagram findings, and per-diagram counts of the ones hidden
        by inline suppressions, both keyed by ``id()`` of the owning diagram.

        Active only for batches of more than one diagram (SCORING.md §6); each
        rule sees only the diagrams matching its ``applies_to``, and needs at
        least two of them to compare.
        """
        out: dict[int, list[Violation]] = {}
        suppressed: dict[int, int] = {}
        if len(diagrams) < 2 or not self.cross_rules:
            return out, suppressed
        honor_suppressions = self.config.get("suppressions", True) is not False
        for rule in self.cross_rules:
            applicable = [
                d for d in diagrams
                if "*" in rule.applies_to or d.diagram_type in rule.applies_to
            ]
            if len(applicable) < 2:
                continue
            for v in rule.check_all(applicable):
                owner = _owning_diagram(v, applicable)
                if owner is None:
                    # Never drop a finding for want of an owner: fall back to
                    # the first diagram in the same file, then the first
                    # applicable diagram in the batch.
                    owner = next(
                        (d for d in applicable if d.file_path == v.file_path),
                        applicable[0],
                    )
                if honor_suppressions and _is_suppressed(owner, rule, v):
                    suppressed[id(owner)] = suppressed.get(id(owner), 0) + 1
                    continue
                out.setdefault(id(owner), []).append(v)
        return out, suppressed

    def lint_paths(self, paths: Iterable[str | Path]) -> list[Violation]:
        return self.lint_diagrams(self._parse_paths(paths))

    def lint_paths_grouped(
        self, paths: Iterable[str | Path]
    ) -> list[tuple[Diagram, list[Violation]]]:
        return self.lint_diagrams_grouped(self._parse_paths(paths))

    @staticmethod
    def _parse_paths(paths: Iterable[str | Path]) -> list[Diagram]:
        diagrams: list[Diagram] = []
        for f in collect_files(paths):
            diagrams.extend(parse_file(f))
        return diagrams


PUML_EXTENSIONS = (".puml", ".plantuml", ".iuml", ".wsd")

_GLOB_CHARS = "*?["


def _is_pattern(text: str) -> bool:
    return any(ch in text for ch in _GLOB_CHARS)


def _expand(pattern: Path) -> list[Path]:
    """Filesystem matches for a glob argument, in stable order.

    Only the part of the pattern from its first wildcard component onward is
    globbed; everything before it is used as a literal base directory.
    ``Path.glob`` rejects an absolute pattern outright, and matching literal
    components through it is both slower and wrong on Windows, where a path
    may name a directory by its 8.3 short form (``RUNNER~1``) that no
    directory listing contains.
    """
    parts = pattern.parts
    first = next((i for i, part in enumerate(parts) if _is_pattern(part)), None)
    if first is None:  # the glob character was in a component we cannot glob
        return []
    base = Path(*parts[:first]) if first else Path()
    rel = Path(*parts[first:])
    try:
        return sorted(base.glob(rel.as_posix()))
    except (ValueError, OSError, NotImplementedError):  # malformed, unreadable
        return []


def _shape_hint(p: Path) -> str:
    """A hint about how the *argument* is malformed, if it obviously is.

    Shared by both error builders: a mistyped argument is just as likely to
    carry a wildcard as not, and the hint is what makes the error useful.
    """
    text = str(p)
    if text.startswith("~"):
        return (
            " — '~' is expanded by the shell, not by pumllint; pass the full "
            "path (or drop the quotes so the shell expands it)"
        )
    if text.endswith('"'):
        return (
            " — the trailing quote suggests a PowerShell path ending in a "
            'backslash ("C:\\dir\\" swallows the closing quote); drop the '
            "trailing backslash"
        )
    return ""


def _missing_path_error(p: Path) -> str:
    """Why one bad argument is bad, in a sentence — not just the path echoed back."""
    return f"no such file or directory: {p}{_shape_hint(p)}"


def _no_match_error(p: Path, filtered: int, suffixes: set[str]) -> str:
    """Why a pattern that expanded found nothing usable."""
    if filtered:
        return (
            f"no diagram files match pattern '{p}': {filtered} path(s) matched "
            f"but none had a diagram extension ({', '.join(sorted(suffixes))})"
        )
    note = _shape_hint(p)
    if not note and os.name == "nt":
        note = (
            " — PowerShell and cmd.exe do not expand wildcards for native "
            "programs, so pumllint expanded it itself and found nothing; "
            "`pumllint .` lints the whole directory"
        )
    return f"no files match pattern '{p}'{note}"


def collect_files(paths: Iterable[str | Path], exts=PUML_EXTENSIONS) -> list[Path]:
    """Every diagram file under *paths*, de-duplicated, in stable order.

    Each argument resolves in this order, so nothing that already works
    changes meaning:

    1. A directory is recursed for *exts*, matched case-insensitively — a
       hand-named ``Diagram.PUML`` is not silently skipped on a case-sensitive
       filesystem.
    2. An existing path is taken as-is, whatever its extension: naming a file
       explicitly is an explicit choice.
    3. Only when neither holds and the argument contains a glob character is
       it expanded as a pattern. POSIX shells expand globs before pumllint
       sees them, so this branch is dead there; PowerShell and ``cmd.exe`` do
       not expand for native programs, and without it ``pumllint *.puml``
       fails on Windows in a directory full of diagrams. Pattern matches are
       filtered by extension — a pattern is a bulk selector like a directory,
       so ``pumllint *`` must not feed ``README.md`` to the parser.

    Every argument is checked before anything is reported, so one typo lists
    all the bad arguments at once rather than only the first.
    """
    suffixes = {str(e).lower() for e in exts}
    files: list[Path] = []
    seen: set[Path] = set()
    problems: list[str] = []

    def _add(f: Path) -> None:
        if f not in seen:
            seen.add(f)
            files.append(f)

    def _recurse(d: Path) -> list[Path]:
        # Suffix first: a string test rejects almost everything for free, and
        # is_file() is a stat syscall per surviving entry.
        return sorted(
            f for f in d.rglob("*") if f.suffix.lower() in suffixes and f.is_file()
        )

    for p in map(Path, paths):
        if p.is_dir():
            for f in _recurse(p):
                _add(f)
        elif p.exists():
            _add(p)
        elif _is_pattern(str(p)):
            matches = _expand(p)
            kept = 0
            for m in matches:
                if m.is_dir():
                    for f in _recurse(m):
                        _add(f)
                    kept += 1
                elif m.suffix.lower() in suffixes:
                    _add(m)
                    kept += 1
            if not kept:
                problems.append(_no_match_error(p, len(matches), suffixes))
        else:
            problems.append(_missing_path_error(p))

    if problems:
        # Never a partial report: a report that looks complete beside exit 2
        # is worse than no report, so one bad argument fails the whole run.
        raise FileNotFoundError("; ".join(problems))
    return files


def _owning_diagram(v: Violation, diagrams: list[Diagram]) -> Diagram | None:
    """The diagram whose file and line span contain this violation.

    An unterminated diagram (``end_line is None``) spans to the start of the
    next diagram in the file, so the *latest* matching start wins — otherwise
    an unterminated first block would swallow every later block's findings.
    """
    owner: Diagram | None = None
    for d in diagrams:
        end = d.end_line if d.end_line is not None else float("inf")
        if d.file_path == v.file_path and d.start_line <= v.line <= end:
            if owner is None or d.start_line > owner.start_line:
                owner = d
    return owner


def _is_suppressed(diagram: Diagram, rule: Rule, v: Violation) -> bool:
    """True when an inline ``' pumllint: disable`` comment covers this finding."""
    for s in diagram.suppressions:
        if s.line is not None and s.line != v.line:
            continue
        if "*" in s.rule_keys or rule.id.lower() in s.rule_keys or rule.name.lower() in s.rule_keys:
            return True
    return False


def _rule_config(rules_cfg: dict, rule_id: str, rule_name: str):
    """Rule config may be keyed by id (SEQ001) or name (undeclared-participant).

    Value semantics: False/"off" disables; True/None -> defaults; dict -> options.

    A table also disables, via ``enabled = false`` inside it. That spelling is
    the natural one the moment a rule carries options — ``[rules.GEN001]`` with
    ``enabled = false`` reads as a disable to anyone writing TOML — and it used
    to fall through this function as *options*, leaving the rule armed while the
    config said it was off. Silent, and it cost a real experiment: a "rules
    disabled" control that was running every rule (issue #37). ``enabled`` is
    consumed here and never reaches the rule, so it is not an option name any
    rule can also use.
    """
    raw = rules_cfg.get(rule_id, rules_cfg.get(rule_name))
    if raw in (False, "off", "disabled"):
        return False
    if raw in (None, True, "on", "enabled"):
        return {}
    if isinstance(raw, dict) and "enabled" in raw:
        opts = {k: v for k, v in raw.items() if k != "enabled"}
        return opts if raw["enabled"] else False
    return raw
