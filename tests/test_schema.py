"""JSON report schema contract tests (0.18.0).

The `-f json` outputs are public contracts, like the golden scores — these
tests pin them from both directions: every report shape the CLI can emit
must validate against the shipped schema, and the schema's enums must stay
in sync with the code's canonical value sets. Plain asserts, stdlib only.
"""

import json
import tempfile
from pathlib import Path

from pumllint.engine import Engine
from pumllint.model import Dimension, Severity
from pumllint.parser import parse_source
from pumllint.reporters import get_reporter
from pumllint.schema import SCHEMA_NAMES, load_schema, validate
from pumllint.scoring import GAP_KINDS, LEVEL_NAMES, score_groups

_ROOT = Path(__file__).resolve().parent.parent
_EXAMPLES = _ROOT / "examples"

# Unnamed diagram with undeclared participants: gaps across dimensions.
_GAPPY_SRC = "@startuml\nAlice -> Bob : hi\n@enduml\n"


def _score_results(src: str = _GAPPY_SRC, path: str = "order.puml"):
    diagrams = parse_source(src, path)
    engine = Engine({})
    return score_groups(engine.lint_diagrams_grouped(diagrams), engine=engine)


def _assert_valid(payload: str, name: str) -> dict:
    instance = json.loads(payload)
    errors = validate(instance, load_schema(name))
    assert not errors, errors
    return instance


def _baseline_for(results, offset: int = 0):
    from pumllint.baseline import BaselineEntry, diagram_keys

    keys = diagram_keys(d for d, _ in results)
    return {
        k: BaselineEntry(level=r.level + offset, composite=0.0)
        for k, (_, r) in zip(keys, results)
    }


# --- the schemas themselves --------------------------------------------------

def test_schemas_declare_their_metadata():
    for name in SCHEMA_NAMES:
        doc = load_schema(name)
        assert doc["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert doc["$id"].endswith(f"{name}.schema.json")
        assert doc["title"]


def test_unknown_schema_name_is_a_clear_error():
    try:
        load_schema("badge")
    except ValueError as e:
        assert "lint" in str(e) and "score" in str(e)
    else:
        assert False, "expected ValueError for unknown schema name"


# --- real reports validate ---------------------------------------------------

def test_lint_report_over_examples_matches_schema():
    violations = Engine({}).lint_paths([str(_EXAMPLES)])
    assert violations, "examples/ must yield findings for this guard to bite"
    payload = _assert_valid(get_reporter("json").render(violations), "lint")
    assert len(payload) == len(violations)


def test_empty_lint_report_matches_schema():
    assert _assert_valid(get_reporter("json").render([]), "lint") == []


def test_score_report_with_gaps_matches_schema():
    results = _score_results()
    assert results[0][1].gap_report, "fixture must produce a gap report"
    payload = _assert_valid(get_reporter("json").render_maturity(results), "score")
    assert payload["diagrams"][0]["maturity"]["gapReport"]


def test_score_report_over_examples_matches_schema():
    """The strongest sweep: every diagram type, clean L5s and L1 wrecks."""
    engine = Engine({})
    groups = engine.lint_paths_grouped([str(_EXAMPLES)])
    results = score_groups(groups, engine=engine)
    assert len(results) >= 10, "examples/ shrank — sweep lost its coverage"
    assert len({r.level for _, r in results}) > 1, "sweep must span levels"
    assert len({d.diagram_type for d, _ in results}) >= 4
    _assert_valid(get_reporter("json").render_maturity(results), "score")


def test_score_report_with_baseline_deltas_matches_schema():
    results = _score_results()
    out = get_reporter("json").render_maturity(
        results, baseline=_baseline_for(results, offset=-1)
    )
    payload = _assert_valid(out, "score")
    assert payload["diagrams"][0]["baseline"]["delta"] == 1
    assert payload["modelSet"]["baseline"]["delta"] == 1


def test_score_report_new_since_baseline_matches_schema():
    # Empty baseline: diagram baseline is null while a ratchet run is active.
    out = get_reporter("json").render_maturity(_score_results(), baseline={})
    payload = _assert_valid(out, "score")
    assert payload["diagrams"][0]["baseline"] is None


def test_empty_score_report_matches_schema():
    payload = _assert_valid(get_reporter("json").render_maturity([]), "score")
    assert payload == {"diagrams": [], "modelSet": None}


# --- the schema has teeth ----------------------------------------------------

def test_schema_rejects_broken_reports():
    schema = load_schema("score")
    good = json.loads(get_reporter("json").render_maturity(_score_results()))

    missing = json.loads(json.dumps(good))
    del missing["modelSet"]
    assert any("modelSet" in e for e in validate(missing, schema))

    extra = json.loads(json.dumps(good))
    extra["diagrams"][0]["surprise"] = 1
    assert any("surprise" in e for e in validate(extra, schema))

    mistyped = json.loads(json.dumps(good))
    mistyped["diagrams"][0]["maturity"]["level"] = "3"
    assert any("level" in e for e in validate(mistyped, schema))

    out_of_range = json.loads(json.dumps(good))
    out_of_range["diagrams"][0]["maturity"]["level"] = 6
    assert any("maximum" in e for e in validate(out_of_range, schema))

    bad_enum = [{"ruleId": "X", "severity": "warning", "message": "m", "file": "f", "line": 1}]
    assert any("severity" in e for e in validate(bad_enum, load_schema("lint")))


def test_validator_refuses_unsupported_keywords():
    try:
        validate({}, {"format": "uri"})
    except ValueError as e:
        assert "unsupported" in str(e)
    else:
        assert False, "unknown keywords must fail loudly, not pass silently"


def test_validator_type_semantics():
    # bool is not a JSON integer/number, even though Python says otherwise
    assert validate(True, {"type": "integer"})
    assert validate(True, {"type": "number"})
    assert not validate(3, {"type": "number"})
    assert not validate(None, {"type": ["string", "null"]})
    assert validate(6, {"type": "integer", "maximum": 5})
    assert validate(0, {"type": "integer", "minimum": 1})


# --- enum sync with the code's canonical sets --------------------------------

def test_schema_enums_match_the_code():
    score = load_schema("score")
    defs = score["$defs"]
    severities = {s.value for s in Severity}
    dims = {d.value for d in Dimension}

    assert set(defs["violation"]["properties"]["severity"]["enum"]) == severities
    lint_violation = load_schema("lint")["$defs"]["violation"]
    assert set(lint_violation["properties"]["severity"]["enum"]) == severities

    assert set(defs["levelName"]["enum"]) == set(LEVEL_NAMES.values())
    assert defs["level"]["minimum"] == min(LEVEL_NAMES)
    assert defs["level"]["maximum"] == max(LEVEL_NAMES)

    # DIM-SYN is a gate, not a scored dimension — everything else must appear
    scored = dims - {Dimension.SYNTAX.value}
    dim_schema = defs["maturity"]["properties"]["dimensions"]
    assert set(dim_schema["required"]) == scored
    assert set(dim_schema["properties"]) == scored

    assert set(defs["gap"]["properties"]["kind"]["enum"]) == set(GAP_KINDS)
    assert set(defs["gap"]["properties"]["dimension"]["enum"]) == dims | {None}


# --- CLI ---------------------------------------------------------------------

def test_cli_schema_command_emits_the_shipped_schema():
    from pumllint.cli import main

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "score.schema.json"
        assert main(["schema", "score", "-o", str(out)]) == 0
        assert json.loads(out.read_text(encoding="utf-8")) == load_schema("score")


def test_cli_schema_command_rejects_unknown_reports():
    import contextlib
    import io

    from pumllint.cli import main

    try:
        with contextlib.redirect_stderr(io.StringIO()):
            main(["schema", "badge"])
    except SystemExit as e:
        assert e.code == 2
    else:
        assert False, "expected argparse to exit 2 for an unknown report"


def test_score_report_with_suppressed_findings_validates():
    src = (
        "@startuml Flow\ntitle Flow\nparticipant Alice\n"
        "' pumllint: disable=SEQ006\nAlice -> Alice : tick()\n@enduml\n"
    )
    payload = get_reporter("json").render_maturity(_score_results(src, "flow.puml"))
    instance = _assert_valid(payload, "score")
    assert instance["diagrams"][0]["maturity"]["suppressedCount"] == 1
    assert instance["modelSet"]["suppressedCount"] == 1
