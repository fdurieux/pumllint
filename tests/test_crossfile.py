"""Cross-diagram consistency rules (XD pack) and their engine wiring.

Plain assert functions so the zero-dependency runner exercises them too.
"""

from pumllint.engine import Engine
from pumllint.model import Dimension
from pumllint.parser import parse_source
from pumllint.scoring import score_groups

_KIND_CONFLICT = """\
@startuml one
participant Client
participant OrderSvc
Client -> OrderSvc : run()
@enduml
@startuml two
participant Client
database OrderSvc
Client -> OrderSvc : query()
@enduml
"""


def _lint(src: str, config: dict | None = None, path: str = "t.puml"):
    return Engine(config or {}).lint_diagrams(parse_source(src, path))


def _xd(violations):
    return [v for v in violations if v.rule_id.startswith("XD")]


def test_conflicting_kind_fires_at_the_later_site_and_cites_the_first():
    hits = [v for v in _lint(_KIND_CONFLICT) if v.rule_id == "XD001"]
    assert len(hits) == 1
    v = hits[0]
    assert v.line == 8
    assert v.dimension is Dimension.CONSISTENCY
    assert "t.puml:3" in v.message  # references the first declaration site


def test_cross_rules_are_inert_for_a_single_diagram():
    single = "@startuml one\nparticipant A\nparticipant B\nA -> B : x()\n@enduml\n"
    assert _xd(_lint(single)) == []


def test_consistent_kinds_are_silent():
    src = _KIND_CONFLICT.replace("database OrderSvc", "participant OrderSvc")
    assert [v.rule_id for v in _xd(_lint(src))] == []


def test_conflicting_stereotype_fires():
    src = (
        "@startuml one\nparticipant Pay <<service>>\nparticipant C\nC -> Pay : x()\n@enduml\n"
        "@startuml two\nparticipant Pay <<external>>\nparticipant C\nC -> Pay : y()\n@enduml\n"
    )
    hits = [v for v in _lint(src) if v.rule_id == "XD002"]
    assert len(hits) == 1 and hits[0].line == 7


def test_missing_stereotype_is_not_a_conflict():
    src = (
        "@startuml one\nparticipant Pay <<service>>\nparticipant C\nC -> Pay : x()\n@enduml\n"
        "@startuml two\nparticipant Pay\nparticipant C\nC -> Pay : y()\n@enduml\n"
    )
    assert not [v for v in _lint(src) if v.rule_id == "XD002"]


def test_case_collision_fires_including_implicit_participants():
    src = (
        "@startuml one\nparticipant Client\nparticipant OrderSvc\nClient -> OrderSvc : run()\n@enduml\n"
        "@startuml two\nparticipant Client\nClient -> Ordersvc : query()\n@enduml\n"
    )
    hits = [v for v in _lint(src) if v.rule_id == "XD003"]
    assert len(hits) == 1
    assert "OrderSvc" in hits[0].message and "Ordersvc" in hits[0].message


def test_cross_rule_can_be_disabled_via_config():
    assert not [
        v for v in _lint(_KIND_CONFLICT, config={"rules": {"XD001": False}})
        if v.rule_id == "XD001"
    ]


def test_inline_suppression_covers_cross_findings():
    # "' pumllint: disable=XD001" suppresses the next line — the conflicting
    # declaration site the violation is attributed to.
    src = _KIND_CONFLICT.replace(
        "database OrderSvc", "' pumllint: disable=XD001\ndatabase OrderSvc"
    )
    assert not [v for v in _lint(src) if v.rule_id == "XD001"]
    assert [v for v in _lint(_KIND_CONFLICT) if v.rule_id == "XD001"]  # baseline fires


def test_grouped_attribution_and_flat_equivalence():
    engine = Engine({})
    diagrams = parse_source(_KIND_CONFLICT, "t.puml")
    groups = engine.lint_diagrams_grouped(diagrams)
    flat = engine.lint_diagrams(diagrams)

    combined = sorted(
        (v for _, vs in groups for v in vs),
        key=lambda v: (v.file_path, v.line, v.rule_id),
    )
    assert combined == flat

    (one, one_vs), (two, two_vs) = groups
    assert not [v for v in one_vs if v.rule_id == "XD001"]
    assert [v for v in two_vs if v.rule_id == "XD001"]  # owned by the later diagram


def test_cross_findings_dent_the_owning_diagrams_dim_con_score():
    engine = Engine({})
    groups = engine.lint_diagrams_grouped(parse_source(_KIND_CONFLICT, "t.puml"))
    results = score_groups(groups)
    (_, r_one), (_, r_two) = results
    assert r_one.dimensions[Dimension.CONSISTENCY].score == 100.0
    assert r_two.dimensions[Dimension.CONSISTENCY].score < 100.0
