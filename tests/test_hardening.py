"""Hardening regressions (docs/security-hardening-assessment.md F4 + F6).

F4 — a malformed regex in a rule option is a *config* error: ValueError
naming the rule and option (the CLI maps it to exit 2), never a raw
``re.error`` traceback that CI would misread as lint findings.

F6 — terminal-bound output neutralizes control characters, so diagram
content cannot smuggle ANSI/OSC escape sequences or spoofed log lines
into terminals and CI logs.
"""

import contextlib
import io
import tempfile
from pathlib import Path

from pumllint.cli import main
from pumllint.engine import Engine
from pumllint.model import Dimension, Severity, Violation
from pumllint.parser import parse_source
from pumllint.reporters.base import sanitize_terminal
from pumllint.reporters.builtin import TextReporter

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


# --- F4: malformed option regexes across every pattern-taking rule --------

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


def test_explicitly_null_option_is_a_config_error_not_a_crash():
    """A key written with an explicit null must not reach the rule body.

    ``options.get(name)`` cannot tell "absent" from "present and null", so a
    null reached the rule and crashed it — ``AttributeError`` on a pattern
    deref, ``TypeError`` on an int or list option. Both escape as **exit 1**,
    which CI reads as lint findings; issue #37's whole point is that a broken
    config must be loud. Thirteen call sites had that shape, so the guard
    lives in ``Rule.__init__`` and these cases span all three value kinds.
    """
    cases = [
        ({"rules": {"CLS001": {"class_pattern": None}}}, _CLASS, "CLS001", "class_pattern"),
        ({"rules": {"CLS001": {"member_pattern": None}}}, _CLASS, "CLS001", "member_pattern"),
        ({"rules": {"participant-naming": {"pattern": None}}}, _SEQ, "GEN004", "pattern"),
        ({"rules": {"ACT005": {"pattern": None}}}, _ACTIVITY, "ACT005", "pattern"),
        ({"profile": "codegen", "rules": {"SEQ103": {"pattern": None}}}, _SEQ, "SEQ103", "pattern"),
        ({"rules": {"GEN009": {"max": None}}}, _SEQ, "GEN009", "max"),
        ({"rules": {"SEQ011": {"max": None}}}, _SEQ, "SEQ011", "max"),
        ({"rules": {"GEN003": {"allowed": None}}}, _SEQ, "GEN003", "allowed"),
        ({"rules": {"ACT006": {"verbs": None}}}, _ACTIVITY, "ACT006", "verbs"),
    ]
    for config, source, *needles in cases:
        _expect_config_error(config, source, *needles)


def test_omitting_an_option_still_means_unset():
    """The guard must reject only *explicit* null, never a missing key.

    GEN006/GEN007 go dormant when no `pattern` is configured, through the same
    ``.get`` that returns None — so a guard that could not tell the two apart
    would turn every unconfigured convention rule into a config error.
    """
    violations = Engine({"rules": {"GEN006": True, "GEN007": True}}).lint_diagrams(
        parse_source(_SEQ, "t.puml")
    )
    assert not [v for v in violations if v.rule_id in ("GEN006", "GEN007")]


def test_valid_custom_pattern_still_enforced():
    violations = Engine({"rules": {"participant-naming": {"pattern": "^[a-z]+$"}}}).lint_diagrams(
        parse_source(_SEQ, "t.puml")
    )
    gen004 = [v for v in violations if v.rule_id == "GEN004"]
    assert gen004, "custom pattern should flag FrontOffice/Bob"
    assert "^[a-z]+$" in gen004[0].message


def test_dormant_property_matches_the_early_return():
    """The five gated rules now test ``self.dormant`` instead of their own
    option, so the listing and the engine share one notion. Pin the notion:
    unset *and* empty both mean dormant; a configured value arms the rule;
    no other rule is ever dormant."""
    from pumllint.rules import discover

    rules = discover()
    gated = {
        "GEN006": ("pattern", "", "(?i)owner"),
        "GEN007": ("pattern", "", "REQ-\\d+"),
        "UC002": ("verbs", [], ["place"]),
        "ACT006": ("verbs", [], ["place"]),
        "SEQ010": ("require_explicit_order", False, True),
    }
    for rid, (key, empty, armed) in gated.items():
        cls = rules[rid]
        assert cls({}).dormant is True, rid
        assert cls({key: empty}).dormant is True, rid
        assert cls({key: armed}).dormant is False, rid
    for rid, cls in rules.items():
        if rid not in gated:
            assert cls({}).dormant is False, rid


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


# --- F6: control characters never reach terminal output -------------------

def _violation(message: str) -> Violation:
    return Violation(
        rule_id="GEN003",
        message=message,
        file_path="evil.puml",
        line=3,
        severity=Severity.MAJOR,
        dimension=Dimension.SEMANTIC,
    )


def test_text_reporter_neutralizes_escape_sequences():
    out = TextReporter().render([_violation("pre \x1b]0;owned\x07 post")])
    assert "\x1b" not in out and "\x07" not in out
    assert "�" in out
    assert "pre" in out and "post" in out


def test_text_reporter_blocks_log_line_spoofing():
    out = TextReporter().render([_violation("x\n✔ No issues found.")])
    # The injected newline must not survive as a real line break.
    assert "✔ No issues found." not in out.splitlines()
    assert "x�✔" in out


def test_sanitize_terminal_keeps_legitimate_text():
    assert sanitize_terminal("état → done\tok") == "état → done\tok"
    assert sanitize_terminal("a\rb\x9bc") == "a�b�c"
