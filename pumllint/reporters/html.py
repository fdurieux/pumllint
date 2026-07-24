"""HTML maturity report: a single self-contained file for architect reviews.

Score-only, like the badge: the report communicates maturity levels, gap
reports and baseline trends to reviewers who never run the CLI — a lint run
has nothing architect-facing to say. Everything is inlined (styles included,
no scripts, no external requests) so the file renders offline as a CI
artifact, wiki attachment or email. Output is deliberately deterministic —
no timestamps — so two runs over the same model set produce byte-identical,
diffable files.

Layout follows the product thesis "the set is only as trustworthy as its
weakest diagram": the model-set verdict leads, and diagram cards are sorted
worst-first.
"""

from __future__ import annotations

from html import escape
from typing import Iterable

from ..baseline import compute_deltas
from ..model import Diagram, Violation
from ..scoring import LEVEL_NAMES, MaturityResult, aggregate_scores
from .base import Reporter, reporter
from .builtin import _Baseline, _diagram_label, _result_keys

# shields.io level palette (matches the badge reporter's color names).
_LEVEL_HEX = {1: "#e05d44", 2: "#fe7d37", 3: "#dfb317", 4: "#a4a61d", 5: "#4c1"}

_CSS = """\
:root { color-scheme: light dark; }
body { font-family: system-ui, -apple-system, sans-serif; margin: 2rem auto;
       max-width: 60rem; padding: 0 1rem; line-height: 1.5;
       color: #1a1a1a; background: #fff; }
h1 { font-size: 1.5rem; } h2 { font-size: 1.1rem; margin: 0; }
.pill { display: inline-block; color: #fff; border-radius: 1em;
        padding: 0.1em 0.7em; font-weight: 600; white-space: nowrap;
        text-shadow: 0 1px 1px rgb(0 0 0 / 35%); }
.card { border: 1px solid #d0d0d0; border-radius: 8px; padding: 1rem 1.25rem;
        margin: 1rem 0; }
.card header { display: flex; justify-content: space-between; gap: 1rem;
               align-items: baseline; flex-wrap: wrap; }
.meta { color: #666; font-size: 0.85rem; }
.trend { font-style: italic; color: #666; }
table.dims { border-collapse: collapse; margin: 0.75rem 0; width: 100%; }
table.dims td { padding: 0.15em 0.6em 0.15em 0; font-size: 0.85rem; }
.bar { background: #eee; border-radius: 3px; width: 100%; height: 0.6em; }
.bar > div { background: #4c1; border-radius: 3px; height: 100%; }
.bar > div.low { background: #e05d44; }
ul.gap { margin: 0.25rem 0 0; padding-left: 1.25rem; }
ul.gap li { margin: 0.25rem 0; }
code, .finding { font-family: ui-monospace, monospace; font-size: 0.85em; }
ul.findings { list-style: none; padding-left: 1rem; margin: 0.25rem 0; }
footer { margin-top: 2rem; color: #888; font-size: 0.8rem; }
@media (prefers-color-scheme: dark) {
  body { color: #ddd; background: #181818; }
  .card { border-color: #3a3a3a; }
  .meta, .trend { color: #999; }
  .bar { background: #333; }
}
"""


def _pill(level: int, name: str) -> str:
    return (
        f'<span class="pill" style="background:{_LEVEL_HEX[level]}">'
        f"Level {level} — {escape(name)}</span>"
    )


def _dim_rows(r: MaturityResult) -> str:
    rows = []
    for dim, ds in r.dimensions.items():
        low = ' class="low"' if ds.score < 70 else ""
        rows.append(
            f"<tr><td><code>{escape(dim.value)}</code></td>"
            f"<td>{ds.score:.0f}</td>"
            f'<td style="width:70%"><div class="bar">'
            f'<div{low} style="width:{ds.score:.0f}%"></div></div></td></tr>'
        )
    return f'<table class="dims">{"".join(rows)}</table>'


def _finding(f: Violation) -> str:
    return (
        f'<li class="finding">{escape(f.rule_id)} {escape(f.severity.value)} '
        f"{escape(f.file_path)}:{f.line} — {escape(f.message)}</li>"
    )


def _gap_section(r: MaturityResult) -> str:
    if not r.gap_report:
        return ""
    target = r.level + 1
    items = []
    for g in r.gap_report:
        findings = (
            f'<ul class="findings">{"".join(_finding(f) for f in g.findings)}</ul>'
            if g.findings
            else ""
        )
        items.append(f"<li>{escape(g.message)}{findings}</li>")
    return (
        f"<p><strong>To reach Level {target} ({escape(LEVEL_NAMES[target])}):"
        f'</strong></p><ul class="gap">{"".join(items)}</ul>'
    )


@reporter
class HtmlReporter(Reporter):
    format_name = "html"

    def render(self, violations: Iterable[Violation]) -> str:
        raise ValueError("format 'html' supports only the score command")

    def render_maturity(
        self,
        results: Iterable[tuple[Diagram, MaturityResult]],
        *,
        baseline: _Baseline = None,
    ) -> str:
        results = list(results)
        keys = _result_keys(results, baseline)
        deltas = compute_deltas(baseline, results) if baseline is not None else {}
        agg = aggregate_scores(results)

        if agg is None:
            summary = "<p>No diagrams to score.</p>"
        else:
            set_trend = ""
            base_levels = [baseline[k].level for k in keys if baseline and k in baseline]
            if base_levels and min(base_levels) != agg.level:
                set_trend = (
                    f' <span class="trend">(Level {min(base_levels)} → '
                    f"{agg.level} since last baseline)</span>"
                )
            summary = (
                f"<p>{_pill(agg.level, agg.level_name)} "
                f"<strong>{agg.composite:.0f}/100</strong> weighted across "
                f"{agg.diagram_count} diagram(s), {agg.element_count} "
                f"element(s).{set_trend}</p>"
            )

        # Worst-first: the set is only as trustworthy as its weakest diagram.
        order = sorted(
            zip(results, keys),
            key=lambda rk: (rk[0][1].level, rk[0][1].composite, _diagram_label(rk[0][0])),
        )
        cards = []
        for (diagram, r), key in order:
            trend = ""
            if baseline is not None:
                d = deltas.get(key)
                if d is None:
                    trend = '<span class="trend">new since baseline</span>'
                elif d.delta != 0:
                    trend = (
                        f'<span class="trend">Level {d.baseline_level} → '
                        f"{d.current_level} since last baseline</span>"
                    )
            cards.append(
                '<section class="card"><header>'
                f"<h2>{escape(_diagram_label(diagram))}</h2>"
                f"{_pill(r.level, r.level_name)}</header>"
                f'<p class="meta">{r.composite:.0f}/100 · '
                f"{escape(diagram.diagram_type)} diagram · "
                f"{r.element_count} element(s) {trend}</p>"
                f"{_dim_rows(r)}{_gap_section(r)}</section>"
            )

        from .. import __version__

        return (
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            "<title>pumllint maturity report</title>\n"
            f"<style>{_CSS}</style>\n</head>\n<body>\n"
            "<h1>pumllint maturity report</h1>\n"
            f"{summary}\n{''.join(cards)}\n"
            f"<footer>generated by pumllint {escape(__version__)}</footer>\n"
            "</body>\n</html>\n"
        )
