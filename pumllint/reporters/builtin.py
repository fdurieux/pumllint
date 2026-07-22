"""Built-in reporters: text (humans), json (machines), sonar (SonarQube)."""

from __future__ import annotations

import json
from collections import Counter
from typing import Iterable

from ..model import Severity, Violation
from ..rules import discover
from .base import Reporter, reporter


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
