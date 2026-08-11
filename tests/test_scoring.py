"""Unit tests for the maturity scorer (pumllint/scoring.py).

The ``assign_level`` cases are direct lifts of the SCORING.md §7 Gherkin
scenarios; the formula cases validate penalty/density/composite wiring. Plain
assert functions so the zero-dependency runner (tests/run_tests.py) runs them
too.
"""

from pumllint.model import Diagram, Dimension, Message, Participant, Severity, Violation
from pumllint.scoring import (
    LEVEL_NAMES,
    ScoringConfig,
    aggregate_scores,
    assign_level,
    compute_dimension_scores,
    composite_score,
    score,
)

_CFG = ScoringConfig()


def _all(value: float = 100.0) -> dict[Dimension, float]:
    """Per-dimension score map with every weighted dimension at *value*."""
    return {d: value for d in _CFG.dimension_weights}


def _approx(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) < tol


def _seq_diagram(n_participants: int = 1, n_messages: int = 0) -> Diagram:
    parts = {
        f"P{i}": Participant(name=f"P{i}", kind="participant", line=i + 1, declared=True)
        for i in range(n_participants)
    }
    msgs = [
        Message(source="P0", target="P0", label="m", line=100 + i, arrow="->")
        for i in range(n_messages)
    ]
    return Diagram(
        file_path="t.puml", name=None, start_line=1, end_line=None,
        diagram_type="sequence", participants=parts, messages=msgs,
    )


def _viol(severity: Severity, dimension: Dimension, rule_id: str = "X001", line: int = 1) -> Violation:
    return Violation(
        rule_id=rule_id, message="m", file_path="t.puml", line=line,
        severity=severity, dimension=dimension,
    )


# --- assign_level: Level 1 / syntax gate -----------------------------------

def test_syntax_failure_forces_level_1_regardless_of_findings():
    level, name = assign_level(
        95, _all(100), has_blocker=False, has_major_or_worse=False,
        syntax_ok=False, cfg=_CFG,
    )
    assert (level, name) == (1, "Sketchy")


def test_very_low_composite_yields_level_1():
    level, _ = assign_level(
        35, _all(100), has_blocker=False, has_major_or_worse=False,
        syntax_ok=True, cfg=_CFG,
    )
    assert level == 1


# --- assign_level: Level 2 --------------------------------------------------

def test_passing_syntax_with_composite_at_threshold_reaches_level_2():
    level, _ = assign_level(
        40, _all(100), has_blocker=True, has_major_or_worse=True,
        syntax_ok=True, cfg=_CFG,
    )
    assert level == 2


def test_blocker_cap_holds_a_high_scoring_diagram_at_level_2():
    level, name = assign_level(
        92, _all(85), has_blocker=True, has_major_or_worse=True,
        syntax_ok=True, cfg=_CFG,
    )
    assert (level, name) == (2, "Structured")


# --- assign_level: Level 3 --------------------------------------------------

def test_composite_60_with_zero_blockers_reaches_level_3():
    level, name = assign_level(
        60, _all(100), has_blocker=False, has_major_or_worse=False,
        syntax_ok=True, cfg=_CFG,
    )
    assert (level, name) == (3, "Disciplined")


def test_weak_dimension_cap_holds_diagram_at_level_3():
    scores = _all(100)
    scores[Dimension.TRACEABILITY] = 35  # below C3 floor; L4 would otherwise pass
    level, _ = assign_level(
        78, scores, has_blocker=False, has_major_or_worse=False,
        syntax_ok=True, cfg=_CFG,
    )
    assert level == 3


# --- assign_level: Level 4 --------------------------------------------------

def test_composite_75_strong_completeness_low_ambiguity_reaches_level_4():
    scores = _all(80)
    scores[Dimension.COMPLETENESS] = 70
    scores[Dimension.AMBIGUITY] = 70
    level, name = assign_level(
        75, scores, has_blocker=False, has_major_or_worse=False,
        syntax_ok=True, cfg=_CFG,
    )
    assert (level, name) == (4, "Precise")


def test_high_composite_with_ambiguous_labels_stays_at_level_3():
    scores = _all(100)
    scores[Dimension.AMBIGUITY] = 65  # below the L4 gate (70)
    level, _ = assign_level(
        82, scores, has_blocker=False, has_major_or_worse=False,
        syntax_ok=True, cfg=_CFG,
    )
    assert level == 3


# --- assign_level: Level 5 --------------------------------------------------

def test_fully_disciplined_model_reaches_generation_ready():
    level, name = assign_level(
        91, _all(80), has_blocker=False, has_major_or_worse=False,
        syntax_ok=True, cfg=_CFG, active_profile="codegen",
    )
    assert (level, name) == (5, "Method-complete")


def test_a_single_major_finding_blocks_generation_ready():
    level, _ = assign_level(
        94, _all(85), has_blocker=False, has_major_or_worse=True,
        syntax_ok=True, cfg=_CFG, active_profile="codegen",
    )
    assert level == 4


# --- formula wiring ---------------------------------------------------------

def test_major_finding_penalty_and_composite():
    # one major (weight 5) in DIM-SEM on a 5-element diagram: density 1.0,
    # SEM = 100 - 50*1 = 50; composite = 0.20*50 + 0.80*100 = 90.
    diagram = _seq_diagram(n_participants=3, n_messages=2)
    result = score([_viol(Severity.MAJOR, Dimension.SEMANTIC)], diagram)
    sem = result.dimensions[Dimension.SEMANTIC]
    assert sem.penalty == 5.0
    assert _approx(sem.score, 50.0)
    assert result.dimensions[Dimension.COMPLETENESS].score == 100.0
    assert _approx(result.composite, 90.0)


def test_critical_weight_is_eight():
    # one critical in DIM-SEM on an 8-element diagram: 100 - 50*(8/8) = 50.
    diagram = _seq_diagram(n_participants=4, n_messages=4)
    result = score([_viol(Severity.CRITICAL, Dimension.SEMANTIC)], diagram)
    assert _approx(result.dimensions[Dimension.SEMANTIC].score, 50.0)


def test_element_count_guard_and_clamp():
    # empty diagram (0 elements -> denom 1); one minor (2) in DIM-CON:
    # 100 - 50*2 = 0, clamped at 0.
    diagram = _seq_diagram(n_participants=0, n_messages=0)
    result = score([_viol(Severity.MINOR, Dimension.CONSISTENCY)], diagram)
    assert result.element_count == 0
    assert result.dimensions[Dimension.CONSISTENCY].score == 0.0


def test_critical_finding_blocks_level_5_end_to_end():
    # 20-element diagram, single critical in SEM: SEM=80, composite=96, every
    # dimension >= 80 -> would be L5, but critical (>= major) blocks it -> L4.
    diagram = _seq_diagram(n_participants=10, n_messages=10)
    result = score([_viol(Severity.CRITICAL, Dimension.SEMANTIC)], diagram)
    assert result.element_count == 20
    assert _approx(result.dimensions[Dimension.SEMANTIC].score, 80.0)
    assert result.level == 4
    assert result.level_name == "Precise"


def test_clean_diagram_scores_perfectly():
    diagram = _seq_diagram(n_participants=3, n_messages=3)
    result = score([], diagram, active_profile="codegen")
    assert _approx(result.composite, 100.0)
    assert result.level == 5


def test_class_diagram_scores_through_the_normal_pipeline():
    # A parsed class diagram is a recognized type: no C5 cap, and the density
    # denominator is classifiers + relations (SCORING.md §3).
    from pumllint.parser import parse_source

    (diagram,) = parse_source(
        "@startuml shop-model\ntitle Shop model\n"
        "class Customer\nclass Order\nclass Item\nclass Invoice\n"
        'Customer "1" -- "1..*" Order : places\n'
        'Order "1" *-- "1..*" Item\n'
        'Order "1" -- "1" Invoice : billed by\n'
        "@enduml\n"
    )
    assert diagram.diagram_type == "class"
    result = score([], diagram)
    assert result.element_count == 7  # 4 classifiers + 3 relations
    assert _approx(result.composite, 100.0)
    assert result.level == 4  # C7: Level 5 additionally needs the codegen profile
    assert not [g for g in result.gap_report if g.kind == "diagram-type"]


def test_dim_syn_violations_are_not_scored():
    # a violation tagged DIM-SYN (the gate) is ignored by the weighted scorer.
    diagram = _seq_diagram(n_participants=3, n_messages=2)
    result = score([_viol(Severity.BLOCKER, Dimension.SYNTAX)], diagram)
    assert all(ds.penalty == 0.0 for ds in result.dimensions.values())
    # but the blocker still caps the level at 2 (C1).
    assert result.level == 2


def test_scoring_is_deterministic():
    diagram = _seq_diagram(n_participants=4, n_messages=3)
    vs = [_viol(Severity.MAJOR, Dimension.COMPLETENESS), _viol(Severity.MINOR, Dimension.AMBIGUITY)]
    a = score(vs, diagram)
    b = score(vs, diagram)
    assert a.level == b.level
    assert _approx(a.composite, b.composite)
    assert {d: s.score for d, s in a.dimensions.items()} == {d: s.score for d, s in b.dimensions.items()}


def test_config_override_changes_critical_weight():
    diagram = _seq_diagram(n_participants=4, n_messages=4)  # 8 elements
    cfg = {"severity_weights": {"critical": 4}}  # halve critical
    result = score([_viol(Severity.CRITICAL, Dimension.SEMANTIC)], diagram, config=cfg)
    # 100 - 50*(4/8) = 75 instead of 50.
    assert _approx(result.dimensions[Dimension.SEMANTIC].score, 75.0)


# --- gap report (SCORING.md §5 / §7) ---------------------------------------

def _gap_kinds(result) -> list[str]:
    return [g.kind for g in result.gap_report]


def _gap(result, kind):
    return next(g for g in result.gap_report if g.kind == kind)


def test_gap_is_empty_at_generation_ready():
    result = score([], _seq_diagram(3, 3), active_profile="codegen")
    assert result.level == 5
    assert result.gap_report == []


def test_gap_states_syntax_gate_must_pass_first():
    result = score([], _seq_diagram(3, 3), syntax_ok=False)
    assert result.level == 1
    assert _gap_kinds(result) == ["syntax"]


def test_gap_lists_findings_to_reach_composite_40():
    # 1-element diagram; one minor in each of CMP/SEM/AMB zeroes those dims,
    # composite = 0.35*100 = 35 -> Level 1, target composite 40.
    diagram = _seq_diagram(n_participants=1, n_messages=0)
    vs = [
        _viol(Severity.MINOR, Dimension.COMPLETENESS),
        _viol(Severity.MINOR, Dimension.SEMANTIC),
        _viol(Severity.MINOR, Dimension.AMBIGUITY),
    ]
    result = score(vs, diagram)
    assert result.level == 1
    gap = _gap(result, "composite")
    assert gap.required == 40.0
    assert gap.findings  # highest-weight findings needed to clear the floor


def test_gap_lists_blocker_as_sole_obstacle_to_level_3():
    # 100-element diagram; a single blocker barely dents its dimension, so the
    # only thing keeping it at Level 2 is the blocker itself.
    diagram = _seq_diagram(n_participants=50, n_messages=50)
    result = score([_viol(Severity.BLOCKER, Dimension.SEMANTIC)], diagram)
    assert result.level == 2
    assert _gap_kinds(result) == ["blocker"]
    assert len(_gap(result, "blocker").findings) == 1


def test_gap_lists_weak_dimension_to_lift_above_40():
    # 5-element diagram; two majors in DIM-TRC zero it (<40) -> C3 caps at 3.
    diagram = _seq_diagram(n_participants=3, n_messages=2)
    vs = [_viol(Severity.MAJOR, Dimension.TRACEABILITY, line=i) for i in (1, 2)]
    result = score(vs, diagram)
    assert result.level == 3
    gap = _gap(result, "dimension")
    assert gap.dimension == Dimension.TRACEABILITY
    assert gap.required == 40.0
    assert gap.findings  # minimal set to lift DIM-TRC above the floor


def test_gap_lists_ambiguity_findings_to_reach_70():
    # 10-element diagram; major+minor in DIM-AMB -> AMB = 65 (< 70 L4 gate).
    diagram = _seq_diagram(n_participants=5, n_messages=5)
    vs = [
        _viol(Severity.MAJOR, Dimension.AMBIGUITY, line=1),
        _viol(Severity.MINOR, Dimension.AMBIGUITY, line=2),
    ]
    result = score(vs, diagram)
    assert result.level == 3
    gap = _gap(result, "dimension")
    assert gap.dimension == Dimension.AMBIGUITY
    assert gap.required == 70.0
    assert _approx(gap.current, 65.0)


def test_gap_lists_major_as_sole_obstacle_to_level_5():
    # 100-element diagram; a single major keeps composite/dims high but blocks L5.
    diagram = _seq_diagram(n_participants=50, n_messages=50)
    result = score([_viol(Severity.MAJOR, Dimension.SEMANTIC)], diagram, active_profile="codegen")
    assert result.level == 4
    assert _gap_kinds(result) == ["severity"]
    assert len(_gap(result, "severity").findings) == 1


# --- integrity caps C4-C7 (vacuity + profile binding) ----------------------

def test_empty_diagram_is_sketchy_not_generation_ready():
    # C4: zero modelled elements -> Level 1, however clean the (absent) content.
    result = score([], _seq_diagram(0, 0), active_profile="codegen")
    assert result.level == 1
    assert _gap_kinds(result) == ["content"]


def test_unknown_diagram_type_caps_at_structured():
    # C5: unrecognized diagram form cannot claim discipline.
    diagram = _seq_diagram(4, 0)
    diagram.diagram_type = "unknown"
    result = score([], diagram, active_profile="codegen")
    assert result.level == 2
    assert "diagram-type" in _gap_kinds(result)


def test_tiny_diagram_caps_at_disciplined():
    # C6: 2 elements < l4_min_elements(3) -> capped at Level 3.
    result = score([], _seq_diagram(1, 1), active_profile="codegen")
    assert result.level == 3
    gap = _gap(result, "content")
    assert gap.required == 3.0 and gap.current == 2.0


def test_level_5_requires_the_codegen_profile():
    # C7: same clean diagram — L4 without the profile, L5 with it.
    diagram = _seq_diagram(3, 3)
    without = score([], diagram)
    assert without.level == 4
    assert _gap_kinds(without) == ["profile"]
    assert "codegen" in _gap(without, "profile").message
    assert score([], diagram, active_profile="codegen").level == 5


def test_unbalanced_dimension_weights_are_rejected():
    # overriding one weight without rebalancing (sum 1.3) is a config error,
    # not a silently distorted composite.
    try:
        score([], _seq_diagram(3, 3), config={"dimension_weights": {"DIM-SEM": 0.5}})
    except ValueError as e:
        assert "sum to 1.0" in str(e)
    else:
        raise AssertionError("expected ValueError for unbalanced dimension weights")


def test_rebalanced_dimension_weights_are_accepted():
    # Overriding CMP/AMB while keeping the total at 1.0 (defaults: SEM .20,
    # CMP .30, CON .15, TRC .05, RDB .05, AMB .25).
    cfg = {"dimension_weights": {"DIM-CMP": 0.25, "DIM-AMB": 0.30}}  # sums to 1.0
    result = score([], _seq_diagram(3, 3), config=cfg, active_profile="codegen")
    assert result.level == 5


def test_score_groups_takes_profile_truth_from_the_engine():
    # Regression (C7): when the engine is passed, its actual profile decides
    # the Level-5 cap — a caller-asserted label cannot override it.
    diagram = _seq_diagram(3, 3)

    class _BaseEngine:
        profile = None

    class _CodegenEngine:
        profile = "codegen"

    from pumllint.scoring import score_groups

    capped = score_groups([(diagram, [])], engine=_BaseEngine(), active_profile="codegen")
    assert capped[0][1].level == 4  # engine truth wins over the label

    certified = score_groups([(diagram, [])], engine=_CodegenEngine())
    assert certified[0][1].level == 5


def test_profile_binding_is_configurable():
    diagram = _seq_diagram(3, 3)
    off = score([], diagram, config={"l5_requires_profile": None})
    assert off.level == 5
    renamed = score([], diagram, config={"l5_requires_profile": "strict"}, active_profile="strict")
    assert renamed.level == 5


# --- model-set aggregation (0.6.0) -----------------------------------------

def test_aggregate_of_nothing_is_none():
    assert aggregate_scores([]) is None


def test_aggregate_takes_worst_level_and_element_weighted_composite():
    clean_d = _seq_diagram(3, 3)
    clean = score([], clean_d, active_profile="codegen")
    dirty_d = _seq_diagram(1, 1)
    dirty = score(
        [_viol(Severity.BLOCKER, Dimension.SEMANTIC)], dirty_d, active_profile="codegen"
    )
    agg = aggregate_scores([(clean_d, clean), (dirty_d, dirty)])
    assert agg.level == min(clean.level, dirty.level)
    assert agg.level_name == LEVEL_NAMES[agg.level]
    total = clean.element_count + dirty.element_count
    expected = (
        clean.composite * clean.element_count + dirty.composite * dirty.element_count
    ) / total
    assert _approx(agg.composite, expected)
    assert agg.diagram_count == 2
    assert agg.element_count == total


def test_aggregate_weights_empty_diagrams_at_one_element():
    empty_d = _seq_diagram(0, 0)
    empty = score([], empty_d)  # C4 makes it Level 1; composite alone is clean
    full_d = _seq_diagram(3, 3)
    full = score([], full_d)
    agg = aggregate_scores([(empty_d, empty), (full_d, full)])
    assert agg.level == 1  # the worst diagram defines the set
    expected = (empty.composite * 1 + full.composite * full.element_count) / (
        1 + full.element_count
    )
    assert _approx(agg.composite, expected)
    assert agg.element_count == full.element_count  # the empty one adds none


def test_score_carries_the_suppressed_count_without_moving_the_score():
    d = _seq_diagram(2, 3)
    plain = score([], d)
    disclosed = score([], d, suppressed_count=3)
    assert plain.suppressed_count == 0
    assert disclosed.suppressed_count == 3
    # Disclosure only: level and composite are untouched (golden scores).
    assert disclosed.composite == plain.composite
    assert disclosed.level == plain.level


def test_aggregate_sums_suppressed_counts_across_the_set():
    d1, d2 = _seq_diagram(2, 2), _seq_diagram(2, 2)
    agg = aggregate_scores([
        (d1, score([], d1, suppressed_count=2)),
        (d2, score([], d2, suppressed_count=1)),
    ])
    assert agg.suppressed_count == 3
