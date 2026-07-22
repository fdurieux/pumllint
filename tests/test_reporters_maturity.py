"""Reporter maturity-output tests (Phase 5). Plain assert functions so the
zero-dependency runner exercises them too.
"""

import json

from pumllint.engine import Engine
from pumllint.parser import parse_source
from pumllint.reporters import get_reporter
from pumllint.scoring import score_groups

# Unnamed diagram with undeclared participants: yields findings across
# dimensions so the result sits below Level 5 with a non-empty gap report.
_SRC = "@startuml\nAlice -> Bob : hi\n@enduml\n"

_DIMENSIONS = {"DIM-SEM", "DIM-CMP", "DIM-CON", "DIM-TRC", "DIM-RDB", "DIM-AMB"}


def _results(src: str = _SRC):
    diagrams = parse_source(src, "order.puml")
    groups = Engine({}).lint_diagrams_grouped(diagrams)
    return score_groups(groups)


def test_text_reporter_shows_level_and_gap():
    results = _results()
    _, r = results[0]
    out = get_reporter("text").render_maturity(results)
    assert "order.puml" in out
    assert f"Level {r.level} ({r.level_name})" in out
    assert "/100" in out
    # gap report renders iff there is one
    assert ("To reach Level" in out) == bool(r.gap_report)


def test_text_reporter_clean_diagram_has_no_gap_section():
    src = (
        "@startuml Clean\n"
        "title Clean flow\n"
        "participant Alice\n"
        "participant Bob\n"
        "Alice -> Bob : greet()\n"
        "Bob --> Alice : ack\n"
        "@enduml\n"
    )
    results = _results(src)
    out = get_reporter("text").render_maturity(results)
    assert "Level" in out
    _, r = results[0]
    if not r.gap_report:
        assert "To reach Level" not in out


def test_json_reporter_emits_maturity_object():
    results = _results()
    payload = json.loads(get_reporter("json").render_maturity(results))
    assert set(payload) == {"diagrams", "modelSet"}
    assert len(payload["diagrams"]) == 1
    entry = payload["diagrams"][0]
    assert entry["file"] == "order.puml"
    maturity = entry["maturity"]
    assert set(maturity) == {
        "level", "levelName", "score", "syntaxOk", "elementCount", "dimensions", "gapReport"
    }
    assert isinstance(maturity["level"], int)
    assert set(maturity["dimensions"]) == _DIMENSIONS
    assert isinstance(maturity["gapReport"], list)


def test_json_reporter_emits_model_set_summary():
    results = _results()
    payload = json.loads(get_reporter("json").render_maturity(results))
    ms = payload["modelSet"]
    assert set(ms) == {"level", "levelName", "score", "diagramCount", "elementCount"}
    # one diagram: the set summary mirrors it
    _, r = results[0]
    assert ms["level"] == r.level
    assert ms["score"] == round(r.composite, 2)
    assert ms["diagramCount"] == 1


def test_text_reporter_shows_model_set_line():
    out = get_reporter("text").render_maturity(_results())
    assert "Model set: Level" in out


def test_json_gap_findings_are_structured():
    results = _results()
    _, r = results[0]
    if not r.gap_report:
        return  # nothing to assert
    payload = json.loads(get_reporter("json").render_maturity(results))
    gap = payload["diagrams"][0]["maturity"]["gapReport"][0]
    assert set(gap) >= {"kind", "message", "findings"}
    for f in gap["findings"]:
        assert set(f) == {"ruleId", "severity", "message", "file", "line"}


def test_sonar_reporter_emits_one_synthetic_issue_per_diagram():
    results = _results()
    payload = json.loads(get_reporter("sonar").render_maturity(results))
    assert len(payload["issues"]) == len(results)
    issue = payload["issues"][0]
    assert issue["ruleId"] == "pumllint-maturity"
    assert issue["primaryLocation"]["message"].startswith("Level ")
    assert issue["primaryLocation"]["filePath"] == "order.puml"
    assert payload["rules"][0]["id"] == "pumllint-maturity"


def test_empty_results_render_gracefully():
    assert get_reporter("text").render_maturity([]) == "No diagrams to score."
    payload = json.loads(get_reporter("json").render_maturity([]))
    assert payload == {"diagrams": [], "modelSet": None}
    assert json.loads(get_reporter("sonar").render_maturity([]))["issues"] == []
