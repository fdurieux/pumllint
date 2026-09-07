"""JSON report schema contract tests (0.18.0).

The `-f json` outputs are public contracts, like the golden scores — these
tests pin them from both directions: every report shape the CLI can emit
must validate against the shipped schema, and the schema's enums must stay
in sync with the code's canonical value sets. Plain asserts, stdlib only.
"""

import json
import tempfile
from pathlib import Path

import importlib.util

from pumllint.config import load_config
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
    assert payload == {"diagrams": [], "modelSet": None, "syntaxGateRan": False}


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


def test_trace_schema_has_teeth():
    from pumllint.trace import build_matrix

    schema = load_schema("trace")
    pattern = __import__("re").compile(r"REQ-\d+")
    diagrams = parse_source("@startuml\ntitle REQ-1\nA -> B : x\n@enduml\n", "t.puml")
    good = json.loads(
        get_reporter("json").render_trace(build_matrix(diagrams, ["REQ-1"], pattern))
    )
    assert validate(good, schema) == []

    extra = json.loads(json.dumps(good))
    extra["requirements"][0]["component"] = "future column"  # additive-only, not yet
    assert any("component" in e for e in validate(extra, schema))

    missing = json.loads(json.dumps(good))
    del missing["summary"]
    assert any("summary" in e for e in validate(missing, schema))


def test_validator_refuses_unsupported_keywords():
    try:
        validate({}, {"format": "uri"})
    except ValueError as e:
        assert "unsupported" in str(e)
    else:
        assert False, "unknown keywords must fail loudly, not pass silently"


def test_validator_supports_anyof():
    schema = {
        "anyOf": [
            {"type": "boolean"},
            {"type": "string", "enum": ["on", "off"]},
            {"type": "object", "properties": {"max": {"type": "integer"}},
             "additionalProperties": False},
        ]
    }
    assert not validate(True, schema)
    assert not validate("off", schema)
    assert not validate({"max": 3}, schema)
    # one alternative declares the value's type: its errors come through verbatim
    assert validate("no", schema) == ["$: 'no' is not one of ['on', 'off']"]
    assert validate({"max": "3"}, schema) == ["$.max: expected integer, got str"]
    assert validate({"mx": 3}, schema) == ["$: unexpected property 'mx'"]
    # no alternative declares the type: one error naming the forms
    assert validate(3, schema) == [
        "$: 3 matches none of the allowed forms (boolean | string | object)"
    ]
    # anyOf is recursed into by the keyword guard, so an unsupported keyword
    # inside a branch still fails loudly
    try:
        validate({}, {"anyOf": [{"oneOf": []}]})
    except ValueError as e:
        assert "oneOf" in str(e)
    else:
        assert False, "unsupported keywords inside anyOf must fail loudly"


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


# --- the config schema (2026-09-07) ------------------------------------------------
#
# The one *input* schema: what pumllint.toml / .yaml / .json may contain.
# Generated from the rule catalog by tools/generate_config_schema.py and pinned
# here the way the Gherkin features are pinned to RULES.md — the committed file
# must equal what the generator derives now.

_GENERATOR = _ROOT / "tools" / "generate_config_schema.py"
_REPO_CONFIGS = (
    "pumllint.toml",
    "docs/pilot-starter-config.toml",
    "docs/xd-demo/lint.toml",
    "docs/xd-demo/distinct.toml",
    "docs/process-demo/conventions.toml",
)


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_config_schema", _GENERATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_committed_config_schema_matches_the_catalog():
    generator = _load_generator()
    on_disk = (_ROOT / "pumllint" / "schemas" / "config.schema.json").read_text(
        encoding="utf-8"
    )
    assert on_disk == generator.render(), (
        "config.schema.json is stale — run: python tools/generate_config_schema.py"
    )
    assert load_schema("config") == generator.build_schema()


def test_config_schema_covers_every_rule_by_id_and_name():
    from pumllint.rules import discover

    rules_props = load_schema("config")["properties"]["rules"]["properties"]
    for rule_id, cls in discover().items():
        assert rules_props[rule_id] == {"$ref": f"#/$defs/{rule_id}"}
        assert rules_props[cls.name] == {"$ref": f"#/$defs/{rule_id}"}
        options = load_schema("config")["$defs"][rule_id]["anyOf"][-1]["properties"]
        assert set(options) == cls.option_keys | {"enabled", "severity"}, rule_id
    assert len(rules_props) == 2 * len(discover())


def test_every_repository_config_validates():
    schema = load_schema("config")
    for rel in _REPO_CONFIGS:
        errors = validate(load_config(_ROOT / rel), schema)
        assert not errors, (rel, errors)


def test_config_schema_accepts_every_rule_value_form():
    schema = load_schema("config")
    for value in (True, False, None, "on", "off", "enabled", "disabled", {},
                  {"enabled": False}, {"severity": "minor", "max": 3}):
        assert not validate({"rules": {"GEN005": value}}, schema), value
    assert not validate({"rules": {"max-elements": {"max": 40}}}, schema)
    assert not validate({"rules": {"GEN005": {"per_type": {"class": 40}}}}, schema)
    assert not validate({"profile": "codegen", "profiles": {"house": {
        "enable": ["SEQ102"], "escalate": {"undeclared-participant": "blocker"}}},
        "suppressions": False}, schema)


def test_config_schema_rejects_what_the_loader_only_warns_about():
    """Each rejection names the path — the editor's squiggle lands on the key."""
    schema = load_schema("config")
    cases = {
        ("$.rules.SEQ001", "only_if_any_declred"):
            {"rules": {"SEQ001": {"only_if_any_declred": True}}},
        ("$", "rulez"): {"rulez": {}},
        ("$.scoring", "mn_level"): {"scoring": {"mn_level": 2}},
        ("$.scoring.thresholds", "l9_composite"):
            {"scoring": {"thresholds": {"l9_composite": 1}}},
        ("$.rules.GEN005.max", "expected integer, got str"):
            {"rules": {"GEN005": {"max": "9"}}},
        ("$.rules.GEN005.max", "got NoneType"): {"rules": {"GEN005": {"max": None}}},
        ("$.rules.SEQ001", "'no' is not one of"): {"rules": {"SEQ001": "no"}},
        ("$.rules", "gen009"): {"rules": {"gen009": False}},  # canonical spellings only
        ("$.profiles.x", "enabel"): {"profiles": {"x": {"enabel": []}}},
        ("$.profiles.x.escalate.GEN001", "'huge' is not one of"):
            {"profiles": {"x": {"escalate": {"GEN001": "huge"}}}},
        ("$.rules.GEN004.per_kind.actor", "expected string"):
            {"rules": {"GEN004": {"per_kind": {"actor": 1}}}},
    }
    for (path, needle), instance in cases.items():
        errors = validate(instance, schema)
        assert len(errors) == 1, (instance, errors)
        assert errors[0].startswith(path + ":") and needle in errors[0], errors


def test_config_schema_enums_match_the_code():
    from pumllint.config import KNOWN_TOP_LEVEL

    schema = load_schema("config")
    assert set(schema["properties"]) == set(KNOWN_TOP_LEVEL)
    assert set(schema["$defs"]["severity"]["enum"]) == {s.value for s in Severity}
    scored = {d.value for d in Dimension} - {Dimension.SYNTAX.value}
    weights = schema["$defs"]["scoring"]["properties"]["dimension_weights"]
    assert set(weights["properties"]) == scored
