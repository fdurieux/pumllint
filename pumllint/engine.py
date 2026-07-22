"""Lint engine: wires config, rule registry, parser and reporters together."""

from __future__ import annotations

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
        profiles_map: dict = self.config.get("profiles") or {}
        profile_cfg: dict = (profiles_map.get(profile) or {}) if profile else {}
        enable_keys = {str(k).lower() for k in (profile_cfg.get("enable") or [])}
        escalate = {
            str(k).lower(): str(v).lower()
            for k, v in (profile_cfg.get("escalate") or {}).items()
        }

        self.rules: list[Rule] = []
        self.cross_rules: list[CrossDiagramRule] = []
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
        honor_suppressions = self.config.get("suppressions", True) is not False
        violations: list[Violation] = []
        for rule in self.rules:
            if "*" not in rule.applies_to and diagram.diagram_type not in rule.applies_to:
                continue
            for v in rule.check(diagram):
                if honor_suppressions and _is_suppressed(diagram, rule, v):
                    continue
                violations.append(v)
        return sorted(violations, key=lambda v: (v.file_path, v.line, v.rule_id))

    def lint_diagrams(self, diagrams: Iterable[Diagram]) -> list[Violation]:
        diagrams = list(diagrams)
        violations: list[Violation] = []
        for d in diagrams:
            violations.extend(self.lint_diagram(d))
        for extra in self._cross_violations(diagrams).values():
            violations.extend(extra)
        return sorted(violations, key=_SORT_KEY)

    def lint_diagrams_grouped(
        self, diagrams: Iterable[Diagram]
    ) -> list[tuple[Diagram, list[Violation]]]:
        """One (diagram, its-violations) pair per diagram — the per-unit input
        for maturity scoring. Flattening this yields the same set as
        :meth:`lint_diagrams`; cross-diagram findings land in the group of the
        diagram that owns their file/line."""
        diagrams = list(diagrams)
        cross = self._cross_violations(diagrams)
        groups: list[tuple[Diagram, list[Violation]]] = []
        for d in diagrams:
            vs = self.lint_diagram(d)
            extra = cross.get(id(d))
            if extra:
                vs = sorted(vs + extra, key=_SORT_KEY)
            groups.append((d, vs))
        return groups

    def _cross_violations(self, diagrams: list[Diagram]) -> dict[int, list[Violation]]:
        """Cross-diagram findings keyed by ``id()`` of the owning diagram.

        Active only for batches of more than one diagram (SCORING.md §6); each
        rule sees only the diagrams matching its ``applies_to``, and needs at
        least two of them to compare.
        """
        out: dict[int, list[Violation]] = {}
        if len(diagrams) < 2 or not self.cross_rules:
            return out
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
                    continue
                if honor_suppressions and _is_suppressed(owner, rule, v):
                    continue
                out.setdefault(id(owner), []).append(v)
        return out

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


def collect_files(paths: Iterable[str | Path], exts=(".puml", ".plantuml", ".iuml", ".wsd")) -> list[Path]:
    files: list[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            for ext in exts:
                files.extend(sorted(p.rglob(f"*{ext}")))
        elif p.exists():
            files.append(p)
        else:
            raise FileNotFoundError(p)
    return files


def _owning_diagram(v: Violation, diagrams: list[Diagram]) -> Diagram | None:
    """The diagram whose file and line span contain this violation."""
    for d in diagrams:
        end = d.end_line if d.end_line is not None else float("inf")
        if d.file_path == v.file_path and d.start_line <= v.line <= end:
            return d
    return None


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
    """
    raw = rules_cfg.get(rule_id, rules_cfg.get(rule_name))
    if raw in (False, "off", "disabled"):
        return False
    if raw in (None, True, "on", "enabled"):
        return {}
    return raw
