"""Drift guard for the round-table talk in talks/semantic-linting-round-table/.

Slides 4 and 5 show what pumllint reports on two committed diagram pairs,
and the speaker notes quote the credit process's maturity level. These tests
run the tool on the same files and assert both directions — the tool still
reports what the slides show, and the slide scripts still show what the tool
reports. Same pact as tests/test_xd_demo.py: change either side deliberately,
then rebuild and republish the talk (``sh build.sh --publish``, see the
talk's README).

The published copy under docs/talks/ is built output (PowerPoint and PDF are
not byte-reproducible); the last test only checks that every file its
landing page links to is there.

Plain assert functions; in-process ``main()`` with redirected streams so
nothing prints under the zero-dependency runner.
"""

import contextlib
import io
import re
from collections import Counter
from pathlib import Path

from pumllint.cli import main

_ROOT = Path(__file__).resolve().parents[1]
_TALK = _ROOT / "talks" / "semantic-linting-round-table"
_DIAGRAMS = _TALK / "diagrams"
_CONFIG = _DIAGRAMS / "lint.toml"  # built-in defaults, not the repository's conventions
_SITE = _ROOT / "docs" / "talks" / "semantic-linting-round-table"

_FINDING = re.compile(r"([^/\\\s]+\.puml):\d+: \[(\w+)/(\w+)\]")


def _run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = main(argv)
    return rc, out.getvalue(), err.getvalue()


def _pair(folder: str) -> list[str]:
    return [str(p) for p in sorted((_DIAGRAMS / folder).glob("*.puml"))] + ["-c", str(_CONFIG)]


def _findings(text: str) -> Counter:
    """(file, rule, severity) of every finding line, counted."""
    return Counter(_FINDING.findall(text))


def _source(name: str) -> str:
    return (_TALK / name).read_text(encoding="utf-8")


def test_credit_flow_reports_exactly_what_slide_4_shows():
    rc, out, _ = _run(_pair("credit-flow"))
    assert _findings(out) == Counter({
        ("credit-application.puml", "ACT003", "minor"): 2,  # then and else unlabelled
        ("credit-application.puml", "ACT002", "major"): 1,  # the flow never ends
        ("credit-decision.puml", "SEQ007", "minor"): 1,     # alt with no condition
    }), out
    assert rc == 1  # the major finding fails the build, as slide 4 says
    slide = _source("slides/credit-flow.js")
    for chip in ("ACT003 · minor", "ACT002 · major", "SEQ007 · minor"):
        assert chip in slide, f"slide 4 no longer shows {chip!r}"


def test_credit_process_scores_level_4_as_the_notes_say():
    """Slide 10's notes: Level 4 (Precise) while carrying a build-failing major —
    business processes are gated on findings, not on level."""
    _, out, _ = _run(["score"] + _pair("credit-flow"))
    assert "[credit-application]: Level 4 (Precise)" in out, out
    assert "scores Level 4 (Precise) while it carries a major finding" in _source("notes.js")


def test_order_service_reports_xd002_on_both_files_as_slide_5_shows():
    rc, out, _ = _run(_pair("order-service"))
    assert _findings(out) == Counter({
        ("checkout.puml", "XD002", "minor"): 1,
        ("refund.puml", "XD002", "minor"): 1,
        # Neither file has a title; the slide leaves GEN001 out and the
        # talk's README says so.
        ("checkout.puml", "GEN001", "minor"): 1,
        ("refund.puml", "GEN001", "minor"): 1,
    }), out
    assert rc == 0  # minors only: below the default --fail-on major
    assert "GEN001" in _source("README.md")
    slide = _source("slides/order-service.js")
    assert "XD002" in slide


def test_slide_5_draws_the_committed_diagrams():
    """Slide 5 renders the two files from data in its script: the stereotype
    and the two messages of each must be the ones in the .puml file."""
    slide = _source("slides/order-service.js")
    drawn = re.findall(
        r"file: '(\w+)\.puml', name: '\w+', st: '(\w+)', m1: '([^']+)', m2: '([^']+)'", slide
    )
    assert len(drawn) == 2, "slide 5 should draw exactly the two files"
    for name, stereotype, m1, m2 in drawn:
        text = (_DIAGRAMS / "order-service" / f"{name}.puml").read_text(encoding="utf-8")
        assert f"participant OrderService <<{stereotype}>>" in text, name
        assert f": {m1}" in text and f": {m2}" in text, name


def test_published_landing_page_links_resolve():
    page = (_SITE / "index.html").read_text(encoding="utf-8")
    local = [h for h in re.findall(r'(?:href|src)="([^"]+)"', page) if "://" not in h]
    assert {"deck.pdf", "deck.pptx", "speaker-notes.pdf", "team-handout.pdf", "overview.jpg"} <= set(local)
    for name in local:
        assert (_SITE / name).is_file(), f"docs/talks/.../index.html links {name}, which is missing"
    assert "{{" not in page, "the landing page was copied without its version and date filled in"
