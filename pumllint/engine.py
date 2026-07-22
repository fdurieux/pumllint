"""Lint engine: wires config, rule registry, parser and reporters together."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .model import Diagram, Severity, Violation
from .parser import parse_file
from .rules import Rule, discover


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
            self.rules.append(rule)

    # -- running ----------------------------------------------------------
    def lint_diagrams(self, diagrams: Iterable[Diagram]) -> list[Violation]:
        honor_suppressions = self.config.get("suppressions", True) is not False
        violations: list[Violation] = []
        for d in diagrams:
            for rule in self.rules:
                if "*" not in rule.applies_to and d.diagram_type not in rule.applies_to:
                    continue
                for v in rule.check(d):
                    if honor_suppressions and _is_suppressed(d, rule, v):
                        continue
                    violations.append(v)
        return sorted(violations, key=lambda v: (v.file_path, v.line, v.rule_id))

    def lint_paths(self, paths: Iterable[str | Path]) -> list[Violation]:
        diagrams: list[Diagram] = []
        for f in collect_files(paths):
            diagrams.extend(parse_file(f))
        return self.lint_diagrams(diagrams)


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
