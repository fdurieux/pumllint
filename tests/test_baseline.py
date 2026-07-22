"""Baseline/ratchet tests (0.6.0). Plain assert functions so the
zero-dependency runner exercises them too.
"""

import json
import tempfile
from pathlib import Path

from pumllint.baseline import (
    BaselineEntry,
    diagram_keys,
    find_regressions,
    load_baseline,
    write_baseline,
)
from pumllint.engine import Engine
from pumllint.parser import parse_source
from pumllint.scoring import score_groups

_TWO_NAMED = (
    "@startuml One\nAlice -> Bob : hi\n@enduml\n"
    "@startuml Two\nAlice -> Bob : hi\n@enduml\n"
)
_TWO_UNNAMED = (
    "@startuml\nAlice -> Bob : hi\n@enduml\n"
    "@startuml\nAlice -> Bob : hi\n@enduml\n"
)


def _score(src: str, path: str = "m.puml"):
    diagrams = parse_source(src, path)
    return score_groups(Engine({}).lint_diagrams_grouped(diagrams))


def test_named_diagrams_key_on_file_and_name():
    diagrams = parse_source(_TWO_NAMED, "m.puml")
    assert diagram_keys(diagrams) == ["m.puml::One", "m.puml::Two"]


def test_unnamed_diagrams_key_on_ordinal():
    diagrams = parse_source(_TWO_UNNAMED, "m.puml")
    assert diagram_keys(diagrams) == ["m.puml::#0", "m.puml::#1"]


def test_duplicate_names_stay_unique():
    src = (
        "@startuml Dup\nAlice -> Bob : hi\n@enduml\n"
        "@startuml Dup\nAlice -> Bob : hi\n@enduml\n"
    )
    keys = diagram_keys(parse_source(src, "m.puml"))
    assert keys[0] == "m.puml::Dup"
    assert keys[1] != keys[0]


def test_write_then_load_round_trips():
    results = _score(_TWO_NAMED)
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "b.json"
        write_baseline(p, results)
        loaded = load_baseline(p)
    assert set(loaded) == {"m.puml::One", "m.puml::Two"}
    for key, (_, r) in zip(diagram_keys(d for d, _ in results), results):
        assert loaded[key].level == r.level


def test_regression_detected_only_on_drop():
    results = _score(_TWO_NAMED)
    keys = diagram_keys(d for d, _ in results)
    level = results[0][1].level
    baseline = {
        keys[0]: BaselineEntry(level=level + 1, composite=0.0),  # current is worse
        keys[1]: BaselineEntry(level=max(1, level - 1), composite=0.0),  # improved
    }
    regs = find_regressions(baseline, results)
    assert [r.key for r in regs] == [keys[0]]
    assert regs[0].baseline_level == level + 1
    assert regs[0].current_level == level


def test_new_diagrams_are_not_regressions():
    assert find_regressions({}, _score(_TWO_NAMED)) == []


def test_version_mismatch_is_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "b.json"
        p.write_text(json.dumps({"version": 99, "diagrams": {}}), encoding="utf-8")
        try:
            load_baseline(p)
        except ValueError as e:
            assert "version" in str(e)
        else:
            assert False, "expected ValueError for a version mismatch"


def test_invalid_json_is_a_value_error():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "b.json"
        p.write_text("{not json", encoding="utf-8")
        try:
            load_baseline(p)
        except ValueError:
            pass
        else:
            assert False, "expected ValueError for invalid JSON"


# --- trend/delta (0.7.0) ----------------------------------------------------

def test_compute_deltas_reports_movement_per_baselined_diagram():
    from pumllint.baseline import compute_deltas

    results = _score(_TWO_NAMED)
    keys = diagram_keys(d for d, _ in results)
    lvl0, lvl1 = results[0][1].level, results[1][1].level
    baseline = {
        keys[0]: BaselineEntry(level=lvl0 - 1, composite=0.0),  # improved
        keys[1]: BaselineEntry(level=lvl1, composite=0.0),      # unchanged
    }
    deltas = compute_deltas(baseline, results)
    assert set(deltas) == {keys[0], keys[1]}
    assert deltas[keys[0]].delta == 1
    assert deltas[keys[0]].baseline_level == lvl0 - 1
    assert deltas[keys[1]].delta == 0


def test_compute_deltas_skips_diagrams_new_since_baseline():
    from pumllint.baseline import compute_deltas

    results = _score(_TWO_NAMED)
    keys = diagram_keys(d for d, _ in results)
    baseline = {keys[0]: BaselineEntry(level=results[0][1].level + 1, composite=0.0)}
    deltas = compute_deltas(baseline, results)
    assert set(deltas) == {keys[0]}  # keys[1] is new -> no delta entry
    assert deltas[keys[0]].delta == -1  # regression shows as negative
