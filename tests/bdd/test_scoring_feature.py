"""Step definitions for the SCORING.md executable spec (features/scoring.feature).

Three scenario families, three drivers:

- Abstract level/gap scenarios ("composite score 92", "DIM-TRC has a score of
  35") drive :func:`assign_level` + :func:`build_gap_report` directly with
  declared numbers — synthetic ``DimensionScore`` objects seeded with matching
  minor/info findings so gap-report assertions have real content to list.
- Integrity-cap scenarios (C4-C7) run the real :func:`score` on constructed
  diagrams.
- CI-gate scenarios run the real CLI (``pumllint score --min-level N``) on
  temp files crafted to land on the stated level.
"""

from pytest_bdd import given, parsers, scenarios, then, when

from pumllint.cli import main as cli_main
from pumllint.model import Diagram, Dimension, Message, Participant, Severity, Violation
from pumllint.scoring import (
    DimensionScore,
    ScoringConfig,
    assign_level,
    build_gap_report,
    score,
)

scenarios("features/scoring.feature")

_ELEMENTS = 10  # synthetic element count backing the declared-score scenarios


def _findings(severity: Severity, dimension: Dimension, n: int = 1) -> list[Violation]:
    return [
        Violation(rule_id="TST001", message="synthetic finding", file_path="spec.puml",
                  line=i + 1, severity=severity, dimension=dimension)
        for i in range(n)
    ]


def _seed_findings(penalty: float, dimension: Dimension) -> list[Violation]:
    """Minor/info findings whose weights sum to (at least) ``penalty``.

    Deliberately no majors/blockers — those flags are set by their own explicit
    Given steps, so declared-score seeding must never trip a severity gate.
    """
    out: list[Violation] = []
    remaining = penalty
    for sev, weight in ((Severity.MINOR, 2.0), (Severity.INFO, 0.5)):
        while remaining >= weight:
            out.extend(_findings(sev, dimension))
            remaining -= weight
    if remaining > 0:
        out.extend(_findings(Severity.INFO, dimension))
    return out


def _set_dim(context, dimension: Dimension, value: float) -> None:
    penalty = (100.0 - value) * _ELEMENTS / context["cfg"].k
    ds = context["dims"][dimension]
    ds.score = float(value)
    ds.penalty = penalty
    ds.violations = _seed_findings(penalty, dimension)


def _mk_diagram(n_participants: int, n_messages: int, diagram_type: str = "sequence") -> Diagram:
    parts = {
        f"P{i}": Participant(name=f"P{i}", kind="participant", line=i + 1, declared=True)
        for i in range(n_participants)
    }
    msgs = [
        Message(source="P0", target="P0", label="m()", line=50 + i, arrow="->")
        for i in range(n_messages)
    ]
    return Diagram(
        file_path="spec.puml", name="Spec", start_line=1, end_line=None,
        diagram_type=diagram_type, participants=parts, messages=msgs,
    )


# Real .puml sources that land on the stated maturity level with default
# config: 2 elements -> C6 caps at 3; a clean titled 4-element flow -> 4 (C7).
_LEVEL_SOURCES = {
    3: "@startuml X\ntitle T\nparticipant Alice\nAlice -> Alice : check()\n@enduml\n",
    4: (
        "@startuml Flow\ntitle Flow\nparticipant Alice\nparticipant Bob\n"
        "Alice -> Bob : greet()\nBob --> Alice : ack\n@enduml\n"
    ),
}


# -- Given -------------------------------------------------------------------

@given("default scoring configuration")
def given_default_config(context):
    cfg = ScoringConfig()
    context.update(
        cfg=cfg,
        syntax_ok=True,
        composite=None,
        dims={
            d: DimensionScore(dimension=d, score=100.0, penalty=0.0, weight=w, violations=[])
            for d, w in cfg.dimension_weights.items()
        },
        has_blocker=False,
        has_major=False,
        active_profile=None,
        diagram=None,
        level=None,
        gap=None,
        exit_code=None,
    )


@given(parsers.parse("a syntactically valid diagram with composite score {n:d}"))
def given_composite(context, n):
    context["composite"] = float(n)
    for d in context["dims"]:
        _set_dim(context, d, float(n))


@given("a diagram that fails the plantuml -checkonly gate")
def given_syntax_fails(context):
    context["syntax_ok"] = False


@given(parsers.parse("the diagram would otherwise have a composite score of {n:d}"))
def given_otherwise_composite(context, n):
    if context["diagram"] is None:  # real-diagram scenarios reach the score naturally
        context["composite"] = float(n)
        for d in context["dims"]:
            _set_dim(context, d, float(n))


@given("the diagram has one blocker finding")
def given_one_blocker(context):
    context["has_blocker"] = True
    context["dims"][Dimension.SEMANTIC].violations.extend(
        _findings(Severity.BLOCKER, Dimension.SEMANTIC)
    )


@given("the diagram has no blocker findings")
def given_no_blockers(context):
    pass  # the default


@given("the diagram has no major findings")
def given_no_majors(context):
    pass  # the default


@given("the diagram has exactly one major finding")
def given_one_major(context):
    context["has_major"] = True
    context["dims"][Dimension.SEMANTIC].violations.extend(
        _findings(Severity.MAJOR, Dimension.SEMANTIC)
    )


@given(parsers.parse("every dimension score is at least {n:d}"))
def given_every_dim_at_least(context, n):
    for d, ds in context["dims"].items():
        if ds.score < n:
            _set_dim(context, d, float(n))


@given(parsers.parse("dimension {dim} has a score of {n:d}"))
def given_dim_score(context, dim, n):
    _set_dim(context, Dimension(dim), float(n))


@given("the codegen profile is active")
def given_codegen_profile(context):
    context["active_profile"] = "codegen"


@given("a syntactically valid diagram with zero modelled elements")
def given_empty_diagram(context):
    context["diagram"] = _mk_diagram(0, 0)


@given("a diagram whose type is not recognized")
def given_unknown_type(context):
    context["diagram"] = _mk_diagram(4, 0, diagram_type="unknown")


@given(parsers.parse("a clean sequence diagram with {n:d} modelled elements"))
def given_clean_small_diagram(context, n):
    context["diagram"] = _mk_diagram(1, n - 1)


@given("a clean sequence diagram scored without the codegen profile")
def given_clean_without_profile(context):
    context["diagram"] = _mk_diagram(3, 3)
    context["active_profile"] = None


@given("the diagram would otherwise reach Level 5")
def given_otherwise_level_5(context):
    pass  # the clean diagram does; the When step proves it


@given(parsers.parse("a diagram scored at maturity level {n:d}"))
def given_file_at_level(context, n, tmp_path):
    puml = tmp_path / "d.puml"
    puml.write_text(_LEVEL_SOURCES[n], encoding="utf-8")
    cfg = tmp_path / "cfg.json"
    cfg.write_text("{}", encoding="utf-8")  # isolate from the repo's pumllint.yaml
    context.update(file=puml, cfgfile=cfg, outfile=tmp_path / "out.txt")


# -- When --------------------------------------------------------------------

@when("the scoring reporter runs")
def when_scoring_runs(context):
    if context["diagram"] is not None:  # real path (integrity-cap scenarios)
        result = score(
            [], context["diagram"],
            syntax_ok=context["syntax_ok"], active_profile=context["active_profile"],
        )
        context["level"], context["gap"] = result.level, result.gap_report
        return
    cfg = context["cfg"]
    level, _name = assign_level(
        context["composite"],
        {d: ds.score for d, ds in context["dims"].items()},
        has_blocker=context["has_blocker"],
        has_major_or_worse=context["has_major"] or context["has_blocker"],
        syntax_ok=context["syntax_ok"],
        cfg=cfg,
        active_profile=context["active_profile"],
    )
    context["level"] = level
    context["gap"] = build_gap_report(
        level, context["composite"], context["dims"], _ELEMENTS,
        context["syntax_ok"], cfg, active_profile=context["active_profile"],
    )


@when(parsers.parse("pumllint score runs with --min-level {n:d}"))
def when_cli_score_runs(context, n):
    context["exit_code"] = cli_main([
        "score", str(context["file"]), "-c", str(context["cfgfile"]),
        "--min-level", str(n), "-o", str(context["outfile"]),
    ])


# -- Then --------------------------------------------------------------------

def _kinds(context) -> list[str]:
    return [g.kind for g in context["gap"]]


def _item(context, kind: str):
    matches = [g for g in context["gap"] if g.kind == kind]
    assert matches, f"no '{kind}' gap item; kinds were {_kinds(context)}"
    return matches[0]


@then(parsers.parse("the maturity level is {n:d}"))
def then_level_is(context, n):
    assert context["level"] == n, f"expected level {n}, got {context['level']}"


@then("no dimension scores are reported")
def then_no_dimension_scores(context):
    # The report stops at the gate: nothing dimension- or composite-shaped.
    assert not any(g.kind in ("dimension", "composite") for g in context["gap"]), _kinds(context)


@then("the gap report states the syntax gate must pass first")
def then_syntax_gap(context):
    assert _kinds(context) == ["syntax"]
    assert "syntax gate" in _item(context, "syntax").message


@then(parsers.parse("the gap report lists the highest-weight findings needed to reach composite {n:d}"))
def then_composite_gap(context, n):
    item = _item(context, "composite")
    assert item.required == float(n)
    assert item.findings, "composite gap item lists no findings"
    weights = [ScoringConfig().severity_weights[f.severity] for f in item.findings]
    assert weights == sorted(weights, reverse=True), "findings not heaviest-first"


@then("the gap report lists the blocker finding as the sole obstacle to Level 3")
def then_blocker_sole_obstacle(context):
    assert _kinds(context) == ["blocker"], _kinds(context)
    assert len(_item(context, "blocker").findings) == 1


@then(parsers.parse("the gap report lists {dim} findings required to lift the dimension above {n:d}"))
def then_dim_gap_lift_above(context, dim, n):
    _assert_dimension_item(context, dim, n)


@then(parsers.parse("the gap report lists {dim} findings required to reach {n:d}"))
def then_dim_gap_reach(context, dim, n):
    _assert_dimension_item(context, dim, n)


def _assert_dimension_item(context, dim, n):
    wanted = Dimension(dim)
    matches = [g for g in context["gap"] if g.kind == "dimension" and g.dimension is wanted]
    assert matches, f"no dimension gap item for {dim}; kinds were {_kinds(context)}"
    item = matches[0]
    assert item.required == float(n)
    assert item.findings, f"{dim} gap item lists no findings"


@then("the gap report lists the major finding as the sole obstacle to Level 5")
def then_major_sole_obstacle(context):
    assert _kinds(context) == ["severity"], _kinds(context)
    assert len(_item(context, "severity").findings) == 1


@then("the gap report states the diagram has no modelled content")
def then_content_gap(context):
    assert _kinds(context) == ["content"], _kinds(context)
    assert "no modelled content" in _item(context, "content").message


@then(parsers.parse("the gap report states Level 4 requires at least {n:d} elements"))
def then_min_elements_gap(context, n):
    item = _item(context, "content")
    assert item.required == float(n)


@then("the gap report states Level 5 requires the codegen profile")
def then_profile_gap(context):
    item = _item(context, "profile")
    assert "codegen" in item.message


@then("the exit code is non-zero")
def then_exit_nonzero(context):
    assert context["exit_code"] != 0


@then("the exit code is zero")
def then_exit_zero(context):
    assert context["exit_code"] == 0
