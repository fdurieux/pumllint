"""Drift guard for docs/business-processes.md and its committed corpus.

The guide quotes live tool output (the nine findings on the draft process,
the clean run on the conforming one, the draft's vacuous Level 4 score);
these tests run the same commands against the committed files under
docs/process-demo/ and assert both directions — the tool still produces
what the page quotes, and the page still quotes what the tool produces.
Same pact as tests/test_xd_demo.py: change either side deliberately, and
this file says so.

Plain assert functions; in-process ``main()`` with redirected streams so
nothing prints under the zero-dependency runner.
"""

import contextlib
import io
from pathlib import Path

from pumllint.cli import main
from pumllint.config import config_warnings, load_config
from pumllint.rules import discover

_ROOT = Path(__file__).resolve().parents[1]
_DEMO = _ROOT / "docs" / "process-demo"
_PAGE = _ROOT / "docs" / "business-processes.md"
_CONFIG = _DEMO / "conventions.toml"
_DRAFT = "order_to_cash_draft.puml"
_GOOD = "order_to_cash.puml"


def _run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = main(argv)
    return rc, out.getvalue(), err.getvalue()


def _findings(text: str, name: str) -> set[str]:
    """The ':<line>: [ID/severity] message' tail of every finding line for
    ``name`` — path-prefix independent, so absolute (test) and relative
    (page) spellings compare equal, on every platform."""
    return {
        line.split(name, 1)[1].rstrip()
        for line in text.splitlines()
        if name in line and "] " in line
    }


def test_draft_reports_exactly_the_nine_findings_the_guide_quotes():
    rc, out, err = _run([str(_DEMO / _DRAFT), "-c", str(_CONFIG)])
    assert rc == 1  # four majors under the default --fail-on
    assert "9 issue(s): 4 major, 5 minor" in out
    assert err == ""  # a clean config: no unknown-key disclosure
    live = _findings(out, _DRAFT)
    quoted = _findings(_PAGE.read_text(encoding="utf-8"), _DRAFT)
    assert len(live) == 9, live
    assert live == quoted, (live ^ quoted)
    ids = {f.split("[", 1)[1].split("/", 1)[0] for f in live}
    assert ids == {"ACT002", "ACT003", "ACT005", "ACT006", "GEN006", "GEN007"}


def test_conforming_process_is_clean_as_documented():
    rc, out, err = _run([str(_DEMO / _GOOD), "-c", str(_CONFIG)])
    assert rc == 0
    assert "No issues found" in out
    assert err == ""
    assert "No issues found" in _PAGE.read_text(encoding="utf-8")


def test_draft_score_is_the_vacuous_level_4_the_guide_warns_about():
    rc, out, _ = _run(["score", str(_DEMO / _DRAFT), "-c", str(_CONFIG)])
    assert rc == 0  # no --min-level: score never gates on its own
    assert "Level 4 (Precise) — 84.9/100" in out, out
    page = _PAGE.read_text(encoding="utf-8")
    assert "Level 4 at 84.9/100" in page


def test_conventions_config_is_valid_and_silent():
    cfg = load_config(_CONFIG)
    assert config_warnings(cfg, discover()) == []
    rules = cfg["rules"]
    # the two dormant governance rules are armed, and ACT006 is escalated
    assert rules["owner-tag"]["pattern"] and rules["requirement-link"]["pattern"]
    assert rules["verb-first-activity"]["severity"] == "major"


def test_guide_carries_the_positioning_and_ambiguity_caveats():
    page = _PAGE.read_text(encoding="utf-8")
    # ROADMAP (BPMN ecosystem note): the ACT pack is positioned as
    # "activity diagrams, not BPMN", in the same breath, or not at all.
    assert "activity diagrams, not BPMN" in page
    # ROADMAP (DIM-AMB coverage residual): the composite is not evidence of
    # unambiguity for activity diagrams, and the guide must say so.
    assert "not evidence that a process" in page and "DIM-AMB" in page
    # and the guide points BPMN users at the tool built for BPMN
    assert "bpmnlint" in page
