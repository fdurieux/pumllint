"""Built-in reporters: text (humans), json (machines), sonar (SonarQube)."""

from __future__ import annotations

import json
from collections import Counter
from typing import Iterable

from ..model import Diagram, Severity, Violation
from ..rules import discover
from ..scoring import LEVEL_NAMES, MaturityResult
from .base import Reporter, reporter


def _diagram_label(d: Diagram) -> str:
    return f"{d.file_path} [{d.name}]" if d.name else d.file_path


def _gap_to_dict(g) -> dict:
    return {
        "kind": g.kind,
        "message": g.message,
        "dimension": g.dimension.value if g.dimension else None,
        "current": round(g.current, 2) if g.current is not None else None,
        "required": g.required,
        "findings": [
            {
                "ruleId": f.rule_id,
                "severity": f.severity.value,
                "message": f.message,
                "file": f.file_path,
                "line": f.line,
            }
            for f in g.findings
        ],
    }


def _maturity_to_dict(r: MaturityResult) -> dict:
    return {
        "level": r.level,
        "levelName": r.level_name,
        "score": round(r.composite, 2),
        "syntaxOk": r.syntax_ok,
        "elementCount": r.element_count,
        "dimensions": {
            dim.value: {
                "score": round(ds.score, 2),
                "penalty": ds.penalty,
                "weight": ds.weight,
            }
            for dim, ds in r.dimensions.items()
        },
        "gapReport": [_gap_to_dict(g) for g in r.gap_report],
    }


@reporter
class TextReporter(Reporter):
    format_name = "text"

    def render(self, violations: Iterable[Violation]) -> str:
        violations = list(violations)
        if not violations:
            return "✔ No issues found."
        lines = [
            f"{v.file_path}:{v.line}: [{v.rule_id}/{v.severity.value}] {v.message}"
            for v in violations
        ]
        counts = Counter(v.severity for v in violations)
        summary = ", ".join(f"{n} {s.value}" for s, n in sorted(counts.items(), key=lambda kv: kv[0].value))
        lines.append(f"\n✖ {len(violations)} issue(s): {summary}")
        return "\n".join(lines)

    def render_maturity(self, results: Iterable[tuple[Diagram, MaturityResult]]) -> str:
        results = list(results)
        if not results:
            return "No diagrams to score."
        blocks = []
        for diagram, r in results:
            lines = [
                f"{_diagram_label(diagram)}: Level {r.level} ({r.level_name}) — {r.composite:.0f}/100"
            ]
            if r.gap_report:
                target = r.level + 1
                lines.append(f"  To reach Level {target} ({LEVEL_NAMES[target]}):")
                for g in r.gap_report:
                    lines.append(f"    • {g.message}{' — fix:' if g.findings else ''}")
                    for f in g.findings:
                        lines.append(
                            f"        {f.rule_id} {f.severity.value:<6} "
                            f"{f.file_path}:{f.line}  {f.message}"
                        )
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)


@reporter
class JsonReporter(Reporter):
    format_name = "json"

    def render(self, violations: Iterable[Violation]) -> str:
        return json.dumps(
            [
                {
                    "ruleId": v.rule_id,
                    "severity": v.severity.value,
                    "message": v.message,
                    "file": v.file_path,
                    "line": v.line,
                }
                for v in violations
            ],
            indent=2,
        )

    def render_maturity(self, results: Iterable[tuple[Diagram, MaturityResult]]) -> str:
        return json.dumps(
            [
                {
                    "file": diagram.file_path,
                    "name": diagram.name,
                    "diagramType": diagram.diagram_type,
                    "maturity": _maturity_to_dict(r),
                }
                for diagram, r in results
            ],
            indent=2,
        )


# --- SonarQube -------------------------------------------------------------

_SONAR_SEVERITY = {
    Severity.INFO: "INFO",
    Severity.MINOR: "LOW",
    Severity.MAJOR: "MEDIUM",
    Severity.CRITICAL: "HIGH",
    Severity.BLOCKER: "BLOCKER",
}


@reporter
class SonarReporter(Reporter):
    """SonarQube Generic Issue Import Format (schema introduced in 10.3).

    Feed the file via ``sonar.externalIssuesReportPaths=pumllint-sonar.json``
    — no SonarQube plugin required.
    """

    format_name = "sonar"
    ENGINE_ID = "pumllint"
    MATURITY_RULE_ID = "pumllint-maturity"

    def render(self, violations: Iterable[Violation]) -> str:
        violations = list(violations)
        registry = discover()
        used_rule_ids = sorted({v.rule_id for v in violations})
        rules = []
        for rid in used_rule_ids:
            cls = registry.get(rid)
            rules.append(
                {
                    "id": rid,
                    "name": cls.name if cls else rid,
                    "description": cls.description if cls else "",
                    "engineId": self.ENGINE_ID,
                    "cleanCodeAttribute": "LOGICAL",
                    "impacts": [
                        {
                            "softwareQuality": "MAINTAINABILITY",
                            "severity": _SONAR_SEVERITY[
                                cls.default_severity if cls else Severity.MAJOR
                            ],
                        }
                    ],
                }
            )
        issues = [
            {
                "ruleId": v.rule_id,
                "primaryLocation": {
                    "message": v.message,
                    "filePath": v.file_path,
                    "textRange": {"startLine": v.line},
                },
            }
            for v in violations
        ]
        return json.dumps({"rules": rules, "issues": issues}, indent=2)

    def render_maturity(self, results: Iterable[tuple[Diagram, MaturityResult]]) -> str:
        """The Generic Issue format carries issues, not measures, so maturity is
        surfaced as one synthetic ``info`` issue per diagram (SCORING.md §5)."""
        results = list(results)
        issues = []
        for diagram, r in results:
            obstacles = (
                f"; {len(r.gap_report)} obstacle(s) to Level {r.level + 1}"
                if r.gap_report
                else ""
            )
            issues.append(
                {
                    "ruleId": self.MATURITY_RULE_ID,
                    "primaryLocation": {
                        "message": (
                            f"Level {r.level} ({r.level_name}) — "
                            f"composite {r.composite:.0f}/100{obstacles}"
                        ),
                        "filePath": diagram.file_path,
                        "textRange": {"startLine": max(1, diagram.start_line)},
                    },
                }
            )
        rule = {
            "id": self.MATURITY_RULE_ID,
            "name": "Maturity level",
            "description": "pumllint maturity score summary (see SCORING.md)",
            "engineId": self.ENGINE_ID,
            "cleanCodeAttribute": "COMPLETE",
            "impacts": [{"softwareQuality": "MAINTAINABILITY", "severity": "INFO"}],
        }
        return json.dumps({"rules": [rule] if issues else [], "issues": issues}, indent=2)
