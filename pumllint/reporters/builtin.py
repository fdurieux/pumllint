"""Built-in reporters: text (humans), json (machines), sonar (SonarQube),
badge (shields.io endpoint)."""

from __future__ import annotations

import json
from collections import Counter
from typing import Iterable, Optional

from ..baseline import BaselineEntry, compute_deltas, diagram_keys
from ..model import Diagram, Severity, Violation
from ..rules import discover
from ..scoring import LEVEL_NAMES, MaturityResult, aggregate_scores
from ..trace import DiagramRef, FeatureRef, TraceResult
from .base import Reporter, format_score, reporter, sanitize_terminal

_Baseline = Optional[dict[str, BaselineEntry]]


def _site_label(s: "DiagramRef | FeatureRef") -> str:
    base = f"{s.file} [{s.name}]" if s.name else s.file
    # Line 0 is a feature-side site carried by the file name: there is no
    # line to open, so none is printed.
    return f"{base}:{s.line}" if s.line else base


def _site_to_dict(s: "DiagramRef | FeatureRef") -> dict:
    return {"file": s.file, "name": s.name, "line": s.line}


def _feature_site_to_dict(s: FeatureRef) -> dict:
    return {
        "file": s.file,
        "name": s.name,
        "line": s.line,
        "scenario": s.scenario,
        "scenarioLine": s.scenario_line,
    }


def _feature_sites_label(sites: Iterable[FeatureRef]) -> str:
    """Feature-side sites grouped per file: the file-level site as
    ``file [name]:line`` (no line for a file-name ID), then the scenarios
    in brackets as ``scenario:heading-line`` — where the reader opens."""
    groups: dict[tuple[str, Optional[str]], list[FeatureRef]] = {}
    for s in sites:
        groups.setdefault((s.file, s.name), []).append(s)
    parts = []
    for (file, name), refs in groups.items():
        base = f"{file} [{name}]" if name else file
        file_level = [r for r in refs if r.scenario is None]
        if file_level and file_level[0].line:
            base += f":{file_level[0].line}"
        scns = [f"{r.scenario}:{r.scenario_line}" for r in refs if r.scenario is not None]
        parts.append(f"{base} ({', '.join(scns)})" if scns else base)
    return ", ".join(parts)


def _result_keys(results: list[tuple[Diagram, MaturityResult]], baseline: _Baseline) -> list:
    """Baseline lookup key per result, or Nones when not in ratchet mode."""
    if baseline is None:
        return [None] * len(results)
    return diagram_keys(d for d, _ in results)


def _diagram_label(d: Diagram) -> str:
    return f"{d.file_path} [{d.name}]" if d.name else d.file_path


def _violation_to_dict(v: Violation) -> dict:
    """The one JSON shape for a violation, shared by lint and maturity output."""
    return {
        "ruleId": v.rule_id,
        "severity": v.severity.value,
        "message": v.message,
        "file": v.file_path,
        "line": v.line,
    }


def _gap_to_dict(g) -> dict:
    return {
        "kind": g.kind,
        "message": g.message,
        "dimension": g.dimension.value if g.dimension else None,
        "current": round(g.current, 2) if g.current is not None else None,
        "required": g.required,
        "findings": [_violation_to_dict(f) for f in g.findings],
    }


def _maturity_to_dict(r: MaturityResult) -> dict:
    return {
        "level": r.level,
        "levelName": r.level_name,
        "score": round(r.composite, 2),
        "syntaxOk": r.syntax_ok,
        "elementCount": r.element_count,
        "suppressedCount": r.suppressed_count,
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
            sanitize_terminal(
                f"{v.file_path}:{v.line}: [{v.rule_id}/{v.severity.value}] {v.message}"
            )
            for v in violations
        ]
        counts = Counter(v.severity for v in violations)
        summary = ", ".join(f"{n} {s.value}" for s, n in sorted(counts.items(), key=lambda kv: kv[0].value))
        lines.append(f"\n✖ {len(violations)} issue(s): {summary}")
        return "\n".join(lines)

    def render_maturity(
        self,
        results: Iterable[tuple[Diagram, MaturityResult]],
        *,
        baseline: _Baseline = None,
        syntax_gate_ran: bool = False,
    ) -> str:
        results = list(results)
        if not results:
            return "No diagrams to score."
        keys = _result_keys(results, baseline)
        deltas = compute_deltas(baseline, results) if baseline is not None else {}
        blocks = []
        for (diagram, r), key in zip(results, keys):
            header = (
                f"{_diagram_label(diagram)}: Level {r.level} ({r.level_name}) — {format_score(r.composite)}/100"
            )
            if r.suppressed_count:  # a suppressed-clean run must say so
                header += f" ({r.suppressed_count} suppressed)"
            if r.deduplicated_count:  # merged base/profile twins, same duty
                header += f" ({r.deduplicated_count} duplicate(s) merged)"
            if baseline is not None:
                d = deltas.get(key)
                if d is None:
                    header += "  (new since baseline)"
                elif d.delta != 0:
                    header += (
                        f"  (Level {d.baseline_level} → {d.current_level} since last baseline)"
                    )
            lines = [sanitize_terminal(header)]
            if r.gap_report:
                target = r.level + 1
                lines.append(f"  To reach Level {target} ({LEVEL_NAMES[target]}):")
                for g in r.gap_report:
                    lines.append(
                        sanitize_terminal(f"    • {g.message}{' — fix:' if g.findings else ''}")
                    )
                    for f in g.findings:
                        lines.append(
                            sanitize_terminal(
                                f"        {f.rule_id} {f.severity.value:<6} "
                                f"{f.file_path}:{f.line}  {f.message}"
                            )
                        )
            blocks.append("\n".join(lines))
        agg = aggregate_scores(results)
        set_line = (
            f"Model set: Level {agg.level} ({agg.level_name}) — "
            f"{format_score(agg.composite)}/100 weighted across {agg.diagram_count} diagram(s)"
        )
        if agg.diagram_count > 1 and len({r.level for _, r in results}) > 1:
            worst_diagram, worst = min(
                results,
                key=lambda dr: (dr[1].level, dr[1].composite, _diagram_label(dr[0])),
            )
            set_line += f" — worst: {_diagram_label(worst_diagram)} (Level {worst.level})"
        if agg.suppressed_count:
            set_line += f" ({agg.suppressed_count} finding(s) suppressed)"
        if agg.deduplicated_count:
            set_line += f" ({agg.deduplicated_count} duplicate finding(s) merged)"
        if baseline is not None:
            base_levels = [baseline[k].level for k in keys if k in baseline]
            if base_levels and min(base_levels) != agg.level:
                set_line += f"  (Level {min(base_levels)} → {agg.level} since last baseline)"
        blocks.append(set_line)
        if not syntax_gate_ran:
            blocks.append(
                "Syntax gate: not run — DIM-SYN unchecked; Level verdicts "
                "assume valid syntax (enable with --check-syntax or "
                "scoring.syntax_gate)."
            )
        return "\n\n".join(blocks)

    def render_trace(self, result: TraceResult) -> str:
        covered = sum(1 for r in result.requirements if r.covered)
        total = len(result.requirements)
        clean = (
            covered == total
            and not result.unknown_references
            and not result.unlinked_diagrams
        )
        if clean:
            summary = (
                f"✔ Requirement coverage: {covered}/{total} covered "
                f"across {result.diagram_count} diagram(s)"
            )
        else:
            parts = [f"{total - covered} uncovered"]
            if result.unknown_references:
                parts.append(f"{len(result.unknown_references)} unknown reference(s)")
            if result.unlinked_diagrams:
                parts.append(f"{len(result.unlinked_diagrams)} unlinked diagram(s)")
            summary = (
                f"Requirement coverage: {covered}/{total} covered — "
                f"{', '.join(parts)} — across {result.diagram_count} diagram(s)"
            )
        lines = [sanitize_terminal(summary)]
        if result.verification_ran:
            lines.append(sanitize_terminal(self._verification_summary(result)))
        lines.append("")
        for r in result.requirements:
            if r.covered:
                sites = ", ".join(_site_label(s) for s in r.covered_by)
                row = f"{r.id}  ← {sites}"
                if result.verification_ran:
                    if r.verified:
                        row += f"  ✔ {_feature_sites_label(r.verified_by)}"
                    else:
                        row += "  ✖ unverified"
            else:
                row = f"{r.id}  ✖ uncovered"
                if r.verified:
                    # Tested but not modelled: said on the row, counted in
                    # neither verification bucket (TraceResult.verified).
                    row += f" (tested, not modelled: {_feature_sites_label(r.verified_by)})"
            lines.append(sanitize_terminal(row))
        if result.unknown_references:
            lines.append("")
            lines.append(
                "Unknown references (not in the inventory — a typo, or the inventory is stale):"
            )
            for u in result.unknown_references:
                sites = ", ".join(_site_label(s) for s in u.cited_by)
                lines.append(sanitize_terminal(f"  {u.id}  ← {sites}"))
        if result.unlinked_diagrams:
            lines.append("")
            lines.append("Unlinked diagrams (no requirement reference):")
            for d in result.unlinked_diagrams:
                label = f"{d.file} [{d.name}]" if d.name else d.file
                lines.append(sanitize_terminal(f"  {label} ({d.diagram_type})"))
        if result.unknown_feature_references:
            lines.append("")
            lines.append(
                "Unknown feature references (not in the inventory — a typo, or the inventory is stale):"
            )
            for u in result.unknown_feature_references:
                lines.append(sanitize_terminal(f"  {u.id}  ← {_feature_sites_label(u.cited_by)}"))
        if result.unlinked_features:
            lines.append("")
            lines.append("Unlinked feature files (no requirement reference):")
            for f in result.unlinked_features:
                lines.append(sanitize_terminal(f"  {_site_label(f)}"))
        if result.unlinked_scenarios:
            lines.append("")
            lines.append(
                "Unlinked scenarios (no requirement reference, in a file that has one):"
            )
            lines.append(sanitize_terminal(f"  {_feature_sites_label(result.unlinked_scenarios)}"))
        return "\n".join(lines)

    @staticmethod
    def _verification_summary(result: TraceResult) -> str:
        """The second summary line: the model measured against the tests.

        The denominator is the modelled requirements (covered rows), never
        the inventory — an unmodelled requirement is already the
        ``uncovered`` direction on the line above.
        """
        verified = len(result.verified)
        modelled = sum(1 for r in result.requirements if r.covered)
        parts = []
        if result.unverified:
            parts.append(f"{len(result.unverified)} unverified")
        if result.unknown_feature_references:
            parts.append(
                f"{len(result.unknown_feature_references)} unknown feature reference(s)"
            )
        if result.unlinked_features:
            parts.append(f"{len(result.unlinked_features)} unlinked feature file(s)")
        if result.unlinked_scenarios:
            parts.append(f"{len(result.unlinked_scenarios)} unlinked scenario(s)")
        head = f"Verification: {verified}/{modelled} modelled requirement(s) referenced by a feature file"
        tail = (
            f"across {result.feature_count} feature file(s), "
            f"{result.scenario_count} scenario(s)"
        )
        if not parts:
            return f"✔ {head} {tail}"
        return f"{head} — {', '.join(parts)} — {tail}"


@reporter
class JsonReporter(Reporter):
    format_name = "json"

    def render(self, violations: Iterable[Violation]) -> str:
        return json.dumps([_violation_to_dict(v) for v in violations], indent=2)

    def render_maturity(
        self,
        results: Iterable[tuple[Diagram, MaturityResult]],
        *,
        baseline: _Baseline = None,
        syntax_gate_ran: bool = False,
    ) -> str:
        results = list(results)
        keys = _result_keys(results, baseline)
        agg = aggregate_scores(results)
        deltas = compute_deltas(baseline, results) if baseline is not None else {}

        def _delta(key) -> Optional[dict]:
            d = deltas.get(key)
            if d is None:
                return None
            return {"level": d.baseline_level, "delta": d.delta}

        model_set = None
        if agg is not None:
            base_levels = [baseline[k].level for k in keys if baseline and k in baseline]
            model_set = {
                "level": agg.level,
                "levelName": agg.level_name,
                "score": round(agg.composite, 2),
                "diagramCount": agg.diagram_count,
                "elementCount": agg.element_count,
                "suppressedCount": agg.suppressed_count,
                "baseline": None
                if not base_levels
                else {"level": min(base_levels), "delta": agg.level - min(base_levels)},
            }
        return json.dumps(
            {
                "diagrams": [
                    {
                        "file": diagram.file_path,
                        "name": diagram.name,
                        "diagramType": diagram.diagram_type,
                        "maturity": _maturity_to_dict(r),
                        "baseline": _delta(key),
                    }
                    for (diagram, r), key in zip(results, keys)
                ],
                "modelSet": model_set,
                # Run-level: whether the DIM-SYN gate executed at all. With it,
                # every syntaxOk above is a tri-state — true/false when the
                # gate ran, "not checked" when it did not — which is what the
                # text report's "Syntax gate: not run" line says (issue #30).
                "syntaxGateRan": syntax_gate_ran,
            },
            indent=2,
        )

    def render_trace(self, result: TraceResult) -> str:
        covered = sum(1 for r in result.requirements if r.covered)
        ran = result.verification_ran

        def _row(r) -> dict:
            row = {
                "id": r.id,
                "covered": r.covered,
                "coveredBy": [_site_to_dict(s) for s in r.covered_by],
            }
            if ran:
                row["verified"] = r.verified
                row["verifiedBy"] = [_feature_site_to_dict(s) for s in r.verified_by]
            return row

        summary = {
            "requirementCount": len(result.requirements),
            "coveredCount": covered,
            "uncoveredCount": len(result.requirements) - covered,
            "unknownReferenceCount": len(result.unknown_references),
            "unlinkedDiagramCount": len(result.unlinked_diagrams),
            "diagramCount": result.diagram_count,
        }
        payload = {
            "requirements": [_row(r) for r in result.requirements],
            "unknownReferences": [
                {
                    "id": u.id,
                    "citedBy": [_site_to_dict(s) for s in u.cited_by],
                }
                for u in result.unknown_references
            ],
            "unlinkedDiagrams": [
                {"file": d.file, "name": d.name, "diagramType": d.diagram_type}
                for d in result.unlinked_diagrams
            ],
            "summary": summary,
        }
        if ran:
            # Additive, and only when the side ran: without --features the
            # payload is byte-identical to the v1 shape.
            payload["unknownFeatureReferences"] = [
                {
                    "id": u.id,
                    "citedBy": [_feature_site_to_dict(s) for s in u.cited_by],
                }
                for u in result.unknown_feature_references
            ]
            payload["unlinkedFeatures"] = [
                {"file": f.file, "name": f.name} for f in result.unlinked_features
            ]
            payload["unlinkedScenarios"] = [
                {"file": f.file, "name": f.name, "scenario": f.scenario, "scenarioLine": f.scenario_line}
                for f in result.unlinked_scenarios
            ]
            summary.update(
                {
                    "featureCount": result.feature_count,
                    "scenarioCount": result.scenario_count,
                    "verifiedCount": len(result.verified),
                    "unverifiedCount": len(result.unverified),
                    "unknownFeatureReferenceCount": len(result.unknown_feature_references),
                    "unlinkedFeatureCount": len(result.unlinked_features),
                    "unlinkedScenarioCount": len(result.unlinked_scenarios),
                }
            )
        return json.dumps(payload, indent=2)


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

    def render_maturity(
        self,
        results: Iterable[tuple[Diagram, MaturityResult]],
        *,
        baseline: _Baseline = None,
        syntax_gate_ran: bool = False,
    ) -> str:
        """The Generic Issue format carries issues, not measures, so maturity is
        surfaced as one synthetic ``info`` issue per diagram (SCORING.md §5).
        ``baseline`` is accepted but unused — the issue schema has no place for
        trend facts."""
        results = list(results)
        issues = []
        for diagram, r in results:
            obstacles = (
                f"; {len(r.gap_report)} obstacle(s) to Level {r.level + 1}"
                if r.gap_report
                else ""
            )
            suppressed = (
                f"; {r.suppressed_count} finding(s) suppressed"
                if r.suppressed_count
                else ""
            )
            issues.append(
                {
                    "ruleId": self.MATURITY_RULE_ID,
                    "primaryLocation": {
                        "message": (
                            f"Level {r.level} ({r.level_name}) — "
                            f"composite {format_score(r.composite)}/100{obstacles}{suppressed}"
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


# --- Badge -----------------------------------------------------------------

_BADGE_COLORS = {1: "red", 2: "orange", 3: "yellow", 4: "yellowgreen", 5: "brightgreen"}


@reporter
class BadgeReporter(Reporter):
    """shields.io *endpoint* JSON for the model-set maturity level.

    Publish the file somewhere raw-fetchable (CI artifact, gh-pages, the repo
    itself) and embed
    ``https://img.shields.io/endpoint?url=<raw-json-url>`` in the README.
    Score-only: the badge states a model-set fact, so there is nothing
    meaningful to render for a lint run.
    """

    format_name = "badge"

    def render_maturity(
        self,
        results: Iterable[tuple[Diagram, MaturityResult]],
        *,
        baseline: _Baseline = None,
        syntax_gate_ran: bool = False,
    ) -> str:
        agg = aggregate_scores(list(results))
        if agg is None:
            message, color = "no diagrams", "lightgrey"
        else:
            message = f"Level {agg.level} — {agg.level_name}"
            color = _BADGE_COLORS[agg.level]
        return json.dumps(
            {
                "schemaVersion": 1,
                "label": "pumllint maturity",
                "message": message,
                "color": color,
            },
            indent=2,
        )
