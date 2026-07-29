"""Hardening regressions (docs/security-hardening-assessment.md F4).

A malformed regex in a rule option is a *config* error: ValueError naming
the rule and option (the CLI maps it to exit 2), never a raw ``re.error``
traceback that CI would misread as lint findings.
"""

import contextlib
import io
import tempfile
from pathlib import Path

from pumllint.cli import main
from pumllint.engine import Engine
from pumllint.parser import parse_source

_SEQ = """\
@startuml demo
title T
actor Bob
participant FrontOffice
Bob -> FrontOffice : ask()
FrontOffice --> Bob : answer
@enduml
"""

_CLASS = """\
@startuml classes
title T
class Foo {
  +bar()
}
@enduml
"""

_ACTIVITY = """\
@startuml flow
title T
|Ops|
start
:Do thing;
stop
@enduml
"""


def _expect_config_error(config: dict, source: str, *needles: str) -> None:
    try:
        Engine(config).lint_diagrams(parse_source(source, "t.puml"))
    except ValueError as e:
        msg = str(e)
        for needle in needles:
            assert needle in msg, (needle, msg)
        return
    raise AssertionError("expected ValueError for malformed config regex")


def test_bad_regex_is_a_config_error_not_a_traceback():
    cases = [
        ({"rules": {"participant-naming": {"pattern": "("}}}, _SEQ, "GEN004", "pattern"),
        ({"rules": {"GEN004": {"per_kind": {"actor": "("}}}}, _SEQ, "GEN004", "per_kind.actor"),
        ({"rules": {"owner-tag": {"pattern": "("}}}, _SEQ, "GEN006", "pattern"),
        ({"rules": {"requirement-link": {"pattern": "("}}}, _SEQ, "GEN007", "pattern"),
        ({"rules": {"CLS001": {"class_pattern": "("}}}, _CLASS, "CLS001", "class_pattern"),
        ({"rules": {"CLS001": {"member_pattern": "("}}}, _CLASS, "CLS001", "member_pattern"),
        ({"rules": {"ACT005": {"pattern": "("}}}, _ACTIVITY, "ACT005", "pattern"),
        (
            {"profile": "codegen", "rules": {"SEQ103": {"pattern": "("}}},
            _SEQ,
            "SEQ103",
            "pattern",
        ),
    ]
    for config, source, *needles in cases:
        _expect_config_error(config, source, *needles)


def test_non_string_pattern_is_a_config_error_too():
    _expect_config_error(
        {"rules": {"participant-naming": {"pattern": 123}}}, _SEQ, "GEN004"
    )


def test_valid_custom_pattern_still_enforced():
    violations = Engine({"rules": {"participant-naming": {"pattern": "^[a-z]+$"}}}).lint_diagrams(
        parse_source(_SEQ, "t.puml")
    )
    gen004 = [v for v in violations if v.rule_id == "GEN004"]
    assert gen004, "custom pattern should flag FrontOffice/Bob"
    assert "^[a-z]+$" in gen004[0].message


def test_empty_pattern_keeps_dormant_rules_dormant():
    # GEN006/GEN007 treat a missing/empty pattern as "not configured".
    violations = Engine({"rules": {"owner-tag": {"pattern": ""}}}).lint_diagrams(
        parse_source(_SEQ, "t.puml")
    )
    assert not [v for v in violations if v.rule_id == "GEN006"]


def test_bad_regex_reaches_cli_as_exit_2():
    with tempfile.TemporaryDirectory() as tmp:
        puml = Path(tmp) / "d.puml"
        puml.write_text(_SEQ, encoding="utf-8")
        cfg = Path(tmp) / "cfg.json"
        cfg.write_text('{"rules": {"participant-naming": {"pattern": "("}}}', encoding="utf-8")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
            rc = main([str(puml), "-c", str(cfg)])
        assert rc == 2
        assert "GEN004" in stderr.getvalue()
