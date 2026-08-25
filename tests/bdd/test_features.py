"""Bind every generated ``.feature`` to the canonical step vocabulary.

The step definitions here implement the small, fixed grammar that the RULES.md
Gherkin is written against (see tools/extract_features.py). Adding a rule to the
spec needs no new steps — only a scenario expressed in this vocabulary.
"""

import re
import tomllib
from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

from pumllint.engine import Engine
from pumllint.parser import parse_source

# Bind the per-rule feature files (<ID>.feature) to the steps below.
# scoring.feature has its own vocabulary — see test_scoring_feature.py.
_FEATURES = Path(__file__).parent / "features"
scenarios(*sorted(
    str(p) for p in _FEATURES.glob("*.feature")
    if re.fullmatch(r"[A-Z]{2,3}\d{3}", p.stem)
))


# -- Given -------------------------------------------------------------------

@given("the diagram:")
def given_diagram(context, docstring):
    context["source"] = docstring


@given("the configuration:")
def given_configuration(context, docstring):
    context["config"] = tomllib.loads(docstring)


@given(parsers.parse('the "{profile}" profile is active'))
def given_profile(context, profile):
    context["profile"] = profile


# -- When --------------------------------------------------------------------

@when("the linter runs")
def when_linter_runs(context):
    config = dict(context["config"])
    if context["profile"]:
        config["profile"] = context["profile"]
    engine = Engine(config)
    diagrams = parse_source(context["source"], "test.puml")
    context["violations"] = engine.lint_diagrams(diagrams)


# -- Then --------------------------------------------------------------------

def _matching(context, rule_id):
    return [v for v in context["violations"] if v.rule_id == rule_id]


# The Then vocabulary uses ``parsers.re`` (not ``parse``) so that both articles
# ("a"/"an") bind, and the trailing ``$`` keeps the overlapping "…is reported",
# "…with severity", and "…on line N" variants unambiguous.
_ID = r'(?P<rule_id>[A-Z]{2,3}\d{3})'
_SEV = r'(?P<severity>\w+)'
_LINE = r'(?P<line>\d+)'


@then("no issues are reported")
def then_no_issues(context):
    assert context["violations"] == [], context["violations"]


@then(parsers.re(rf'no "{_ID}" issue is reported$'))
def then_no_rule_issue(context, rule_id):
    assert not _matching(context, rule_id), _matching(context, rule_id)


@then(parsers.re(rf'no "{_ID}" issue is reported on line {_LINE}$'))
def then_no_rule_issue_on_line(context, rule_id, line):
    line = int(line)
    hits = [v for v in _matching(context, rule_id) if v.line == line]
    assert not hits, f"expected no {rule_id} issue on line {line}; got {hits}"


@then(parsers.re(rf'an? "{_ID}" issue is reported$'))
def then_rule_issue(context, rule_id):
    assert _matching(context, rule_id), f"expected a {rule_id} issue; got {context['violations']}"


@then(parsers.re(rf'an? "{_ID}" issue with severity "{_SEV}" is reported$'))
def then_rule_issue_severity(context, rule_id, severity):
    hits = _matching(context, rule_id)
    assert hits, f"expected a {rule_id} issue; got {context['violations']}"
    assert any(v.severity.value == severity for v in hits), \
        f"{rule_id} severities were {[v.severity.value for v in hits]}, expected {severity}"


@then(parsers.re(rf'an? "{_ID}" issue is reported on line {_LINE}$'))
def then_rule_issue_on_line(context, rule_id, line):
    line = int(line)
    lines = [v.line for v in _matching(context, rule_id)]
    assert line in lines, f"expected a {rule_id} issue on line {line}; got lines {lines}"


@then(parsers.re(rf'an? "{_ID}" issue with severity "{_SEV}" is reported on line {_LINE}$'))
def then_rule_issue_severity_line(context, rule_id, severity, line):
    line = int(line)
    hits = [v for v in _matching(context, rule_id) if v.line == line]
    assert hits, f"expected a {rule_id} issue on line {line}; got {_matching(context, rule_id)}"
    assert any(v.severity.value == severity for v in hits), \
        f"{rule_id}@{line} severities were {[v.severity.value for v in hits]}, expected {severity}"
