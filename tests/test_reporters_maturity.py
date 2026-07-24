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

# Clean except for one self-message hidden by an inline suppression: scores
# like a clean diagram but must be reported as suppressed-clean.
_SUPPRESSED_SRC = (
    "@startuml Flow\n"
    "title Flow\n"
    "participant Alice\n"
    "participant Bob\n"
    "' pumllint: disable=SEQ006\n"
    "Alice -> Alice : tick()\n"
    "Alice -> Bob : go()\n"
    "Bob --> Alice : ok\n"
    "@enduml\n"
)

_DIMENSIONS = {"DIM-SEM", "DIM-CMP", "DIM-CON", "DIM-TRC", "DIM-RDB", "DIM-AMB"}


def _results(src: str = _SRC):
    diagrams = parse_source(src, "order.puml")
    engine = Engine({})
    groups = engine.lint_diagrams_grouped(diagrams)
    return score_groups(groups, engine=engine)


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
        "level", "levelName", "score", "syntaxOk", "elementCount",
        "suppressedCount", "dimensions", "gapReport"
    }
    assert isinstance(maturity["level"], int)
    assert set(maturity["dimensions"]) == _DIMENSIONS
    assert isinstance(maturity["gapReport"], list)


def test_json_reporter_emits_model_set_summary():
    results = _results()
    payload = json.loads(get_reporter("json").render_maturity(results))
    ms = payload["modelSet"]
    assert set(ms) == {
        "level", "levelName", "score", "diagramCount", "elementCount",
        "suppressedCount", "baseline"
    }
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


# --- suppressed-findings disclosure (0.19.0) --------------------------------
# A suppressed-clean diagram must never render identically to a clean one:
# every report carries the per-diagram count of findings hidden by inline
# suppressions (the score itself is unchanged — golden scores stay frozen).

def test_text_reporter_annotates_suppressed_findings():
    out = get_reporter("text").render_maturity(_results(_SUPPRESSED_SRC))
    assert "(1 suppressed)" in out              # per-diagram header
    assert "(1 finding(s) suppressed)" in out   # model-set line


def test_text_reporter_stays_silent_without_suppressions():
    assert "suppressed" not in get_reporter("text").render_maturity(_results())


def test_json_reporter_emits_suppressed_counts():
    payload = json.loads(get_reporter("json").render_maturity(_results(_SUPPRESSED_SRC)))
    assert payload["diagrams"][0]["maturity"]["suppressedCount"] == 1
    assert payload["modelSet"]["suppressedCount"] == 1

    clean = json.loads(get_reporter("json").render_maturity(_results()))
    assert clean["diagrams"][0]["maturity"]["suppressedCount"] == 0
    assert clean["modelSet"]["suppressedCount"] == 0


def test_html_reporter_annotates_suppressed_findings():
    out = get_reporter("html").render_maturity(_results(_SUPPRESSED_SRC))
    assert "1 finding(s) suppressed inline" in out
    assert "suppressed" not in get_reporter("html").render_maturity(_results())


def test_sonar_reporter_mentions_suppressed_findings():
    payload = json.loads(get_reporter("sonar").render_maturity(_results(_SUPPRESSED_SRC)))
    assert "1 finding(s) suppressed" in payload["issues"][0]["primaryLocation"]["message"]


def test_suppression_annotation_does_not_change_the_score():
    honoured = _results(_SUPPRESSED_SRC)[0][1]
    diagrams = parse_source(_SUPPRESSED_SRC, "order.puml")
    engine = Engine({"suppressions": False})
    audited = score_groups(engine.lint_diagrams_grouped(diagrams), engine=engine)[0][1]
    # Suppression hides a real finding, so the audited score is lower — and
    # the honoured run must disclose the count rather than absorb it silently.
    assert honoured.suppressed_count == 1
    assert audited.suppressed_count == 0
    assert audited.composite < honoured.composite


def test_empty_results_render_gracefully():
    assert get_reporter("text").render_maturity([]) == "No diagrams to score."
    payload = json.loads(get_reporter("json").render_maturity([]))
    assert payload == {"diagrams": [], "modelSet": None}
    assert json.loads(get_reporter("sonar").render_maturity([]))["issues"] == []


# --- trend/delta annotations (0.7.0) ---------------------------------------

def _baseline_for(results, offset: int = 0):
    """A synthetic baseline recording each result's level shifted by offset."""
    from pumllint.baseline import BaselineEntry, diagram_keys

    keys = diagram_keys(d for d, _ in results)
    return {
        k: BaselineEntry(level=r.level + offset, composite=0.0)
        for k, (_, r) in zip(keys, results)
    }


def test_text_reporter_shows_delta_against_baseline():
    results = _results()
    out = get_reporter("text").render_maturity(
        results, baseline=_baseline_for(results, offset=-1)  # improved since
    )
    _, r = results[0]
    assert f"(Level {r.level - 1} → {r.level} since last baseline)" in out


def test_text_reporter_unchanged_level_prints_no_delta():
    results = _results()
    out = get_reporter("text").render_maturity(results, baseline=_baseline_for(results))
    assert "since last baseline" not in out
    assert "new since baseline" not in out


def test_text_reporter_marks_diagrams_new_since_baseline():
    out = get_reporter("text").render_maturity(_results(), baseline={})
    assert "(new since baseline)" in out


def test_json_reporter_emits_baseline_deltas():
    results = _results()
    payload = json.loads(
        get_reporter("json").render_maturity(
            results, baseline=_baseline_for(results, offset=-1)
        )
    )
    _, r = results[0]
    assert payload["diagrams"][0]["baseline"] == {"level": r.level - 1, "delta": 1}
    assert payload["modelSet"]["baseline"] == {"level": r.level - 1, "delta": 1}


def test_json_reporter_baseline_is_null_without_ratchet():
    payload = json.loads(get_reporter("json").render_maturity(_results()))
    assert payload["diagrams"][0]["baseline"] is None
    assert payload["modelSet"]["baseline"] is None


# --- badge (0.7.0) ----------------------------------------------------------

def test_badge_reporter_emits_shields_endpoint_json():
    results = _results()
    payload = json.loads(get_reporter("badge").render_maturity(results))
    _, r = results[0]
    assert payload["schemaVersion"] == 1
    assert payload["label"] == "pumllint maturity"
    assert payload["message"] == f"Level {r.level} — {r.level_name}"
    assert payload["color"] in {"red", "orange", "yellow", "yellowgreen", "brightgreen"}


def test_badge_reporter_handles_an_empty_set():
    payload = json.loads(get_reporter("badge").render_maturity([]))
    assert payload["message"] == "no diagrams"
    assert payload["color"] == "lightgrey"


def test_badge_reporter_rejects_lint_output():
    try:
        get_reporter("badge").render([])
    except ValueError as e:
        assert "score" in str(e)
    else:
        assert False, "expected ValueError for badge lint rendering"


# --- html (0.15.0) ----------------------------------------------------------

def test_html_reporter_emits_self_contained_report():
    import re

    results = _results()
    _, r = results[0]
    out = get_reporter("html").render_maturity(results)
    assert out.startswith("<!DOCTYPE html>")
    assert "pumllint maturity report" in out
    assert f"Level {r.level} — {r.level_name}" in out
    assert "order.puml" in out
    assert ("To reach Level" in out) == bool(r.gap_report)
    # self-contained: no external scripts, stylesheets, images or fonts
    assert not re.search(r'(src|href)="', out)
    assert "<script" not in out


def test_html_reporter_sorts_diagrams_worst_first():
    src = (
        "@startuml good\ntitle Good\nparticipant A\nparticipant B\n"
        "A -> B : go()\nB --> A : ok\n@enduml\n"
        "@startuml\nAlice -> Bob :\nalt maybe\nAlice -> Bob : retry\n@enduml\n"
    )
    results = _results(src)
    out = get_reporter("html").render_maturity(results)
    levels = {r.level for _, r in results}
    assert len(levels) > 1, "fixture must span levels"
    worst = min(results, key=lambda dr: dr[1].level)[0]
    best = max(results, key=lambda dr: dr[1].level)[0]
    from pumllint.reporters.builtin import _diagram_label

    assert out.index(_diagram_label(worst)) < out.index(_diagram_label(best))


def test_html_reporter_escapes_untrusted_text():
    src = '@startuml <img>\ntitle T\nparticipant A\nA -> A : <script>alert(1)</script>\n@enduml\n'
    out = get_reporter("html").render_maturity(_results(src))
    assert "<script>alert" not in out
    assert "<img>" not in out.split("<h2>")[1].split("</h2>")[0].replace("&lt;img&gt;", "")


def test_html_reporter_annotates_baseline_trends():
    results = _results()
    _, r = results[0]
    out = get_reporter("html").render_maturity(
        results, baseline=_baseline_for(results, offset=-1)
    )
    assert f"Level {r.level - 1} → {r.level} since last baseline" in out
    out_new = get_reporter("html").render_maturity(results, baseline={})
    assert "new since baseline" in out_new


def test_html_reporter_is_deterministic():
    results = _results()
    assert (
        get_reporter("html").render_maturity(results)
        == get_reporter("html").render_maturity(results)
    )


def test_html_reporter_handles_an_empty_set():
    out = get_reporter("html").render_maturity([])
    assert "No diagrams to score." in out


def test_html_reporter_rejects_lint_output():
    try:
        get_reporter("html").render([])
    except ValueError as e:
        assert "score" in str(e)
    else:
        assert False, "expected ValueError for html lint rendering"
