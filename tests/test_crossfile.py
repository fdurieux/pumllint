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


def test_conflicting_kind_fires_symmetrically_at_every_site():
    hits = [v for v in _lint(_KIND_CONFLICT) if v.rule_id == "XD001"]
    assert [v.line for v in hits] == [3, 8]  # both declaration sites
    assert all(v.dimension is Dimension.CONSISTENCY for v in hits)
    # The message lists every variant with counts and elects no side.
    for v in hits:
        assert "'participant' ×1" in v.message and "'database' ×1" in v.message


def test_cross_rules_are_inert_for_a_single_diagram():
    single = "@startuml one\nparticipant A\nparticipant B\nA -> B : x()\n@enduml\n"
    assert _xd(_lint(single)) == []


def test_consistent_kinds_are_silent():
    src = _KIND_CONFLICT.replace("database OrderSvc", "participant OrderSvc")
    assert [v.rule_id for v in _xd(_lint(src))] == []


def test_conflicting_stereotype_fires_at_both_sites():
    src = (
        "@startuml one\nparticipant Pay <<service>>\nparticipant C\nC -> Pay : x()\n@enduml\n"
        "@startuml two\nparticipant Pay <<external>>\nparticipant C\nC -> Pay : y()\n@enduml\n"
    )
    hits = [v for v in _lint(src) if v.rule_id == "XD002"]
    assert [v.line for v in hits] == [2, 7]
    assert all("<<service>> ×1" in v.message and "<<external>> ×1" in v.message for v in hits)


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
    # "' pumllint: disable=XD001" suppresses the next line. Findings are
    # per-site, so the suppression silences that site only — the sibling
    # site keeps its finding.
    src = _KIND_CONFLICT.replace(
        "database OrderSvc", "' pumllint: disable=XD001\ndatabase OrderSvc"
    )
    hits = [v for v in _lint(src) if v.rule_id == "XD001"]
    assert [v.line for v in hits] == [3]  # the un-suppressed site
    assert len([v for v in _lint(_KIND_CONFLICT) if v.rule_id == "XD001"]) == 2  # baseline


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
    assert [v.line for v in one_vs if v.rule_id == "XD001"] == [3]
    assert [v.line for v in two_vs if v.rule_id == "XD001"] == [8]  # each site owned locally


def test_unterminated_first_diagram_does_not_swallow_later_findings():
    # Regression: an unterminated first block spans to the next block's start,
    # not to infinity — the conflict site inside 'two' must land in 'two''s group.
    src = (
        "@startuml one\nparticipant Client\nparticipant OrderSvc\n"
        "Client -> OrderSvc : run()\n"          # no @enduml — unterminated
        "@startuml two\nparticipant Client\ndatabase OrderSvc\n"
        "Client -> OrderSvc : query()\n@enduml\n"
    )
    groups = Engine({}).lint_diagrams_grouped(parse_source(src, "t.puml"))
    (one, one_vs), (two, two_vs) = groups
    assert [v.line for v in one_vs if v.rule_id == "XD001"] == [3]
    assert [v.line for v in two_vs if v.rule_id == "XD001"] == [7]


def test_every_site_is_reported_and_no_majority_is_elected():
    # Issue #36: majority-wins indicted the conforming sites once drift had
    # the majority. All sites now carry the same symmetric evidence.
    src = (
        "@startuml a\ndatabase OrderSvc\nparticipant C\nC -> OrderSvc : x()\n@enduml\n"
        "@startuml b\nparticipant OrderSvc\nparticipant C\nC -> OrderSvc : y()\n@enduml\n"
        "@startuml c\nparticipant OrderSvc\nparticipant C\nC -> OrderSvc : z()\n@enduml\n"
    )
    hits = [v for v in _lint(src) if v.rule_id == "XD001"]
    assert [v.line for v in hits] == [2, 7, 12]
    for v in hits:
        assert "'participant' ×2" in v.message and "'database' ×1" in v.message
        assert " but " not in v.message  # no site is told to conform to another


def test_a_tie_reads_the_same_whichever_file_sorts_first():
    # Issue #36: at a 2-vs-2 tie the verdict flipped with filename order.
    # Symmetric reporting makes the message content order-independent.
    drifted = "@startuml {n}\nparticipant Pay <<sink>>\nparticipant C\nC -> Pay : x()\n@enduml\n"
    original = "@startuml {n}\nparticipant Pay <<store>>\nparticipant C\nC -> Pay : y()\n@enduml\n"

    def batch(order):
        return "".join(t.replace("{n}", f"d{i}") for i, t in enumerate(order))

    first = [v.message for v in _lint(batch([drifted, drifted, original, original]))
             if v.rule_id == "XD002"]
    second = [v.message for v in _lint(batch([original, original, drifted, drifted]))
              if v.rule_id == "XD002"]
    assert len(first) == len(second) == 4
    assert sorted(first) == sorted(second)  # same evidence, whatever the order


def test_authoritative_pick_reports_only_nonconforming_sites():
    src = (
        "@startuml a\nparticipant Pay <<sink>>\nparticipant C\nC -> Pay : x()\n@enduml\n"
        "@startuml b\nparticipant Pay <<sink>>\nparticipant C\nC -> Pay : y()\n@enduml\n"
        "@startuml c\nparticipant Pay <<store>>\nparticipant C\nC -> Pay : z()\n@enduml\n"
    )
    cfg = {"rules": {"XD002": {"authoritative": {"Pay": "store"}}}}
    hits = [v for v in _lint(src, cfg) if v.rule_id == "XD002"]
    # The drifted majority is flagged; the configured value is clean.
    assert [v.line for v in hits] == [2, 7]
    assert all("<<store>> is the configured stereotype" in v.message for v in hits)


def test_authoritative_pick_is_a_conflict_pin_not_a_vocabulary_check():
    # All sites agree (with each other, not with the config): no conflict,
    # no finding — the option resolves disagreements, it does not audit.
    src = (
        "@startuml a\nparticipant Pay <<sink>>\nparticipant C\nC -> Pay : x()\n@enduml\n"
        "@startuml b\nparticipant Pay <<sink>>\nparticipant C\nC -> Pay : y()\n@enduml\n"
    )
    cfg = {"rules": {"XD002": {"authoritative": {"Pay": "store"}}}}
    assert not [v for v in _lint(src, cfg) if v.rule_id == "XD002"]


def test_authoritative_kind_pick_works_for_xd001():
    cfg = {"rules": {"XD001": {"authoritative": {"OrderSvc": "database"}}}}
    hits = [v for v in _lint(_KIND_CONFLICT, cfg) if v.rule_id == "XD001"]
    assert [v.line for v in hits] == [3]  # the participant site; database conforms
    assert "'database' is the configured kind" in hits[0].message


def test_unattributable_cross_finding_is_not_dropped():
    # A batch-level finding whose line falls outside every diagram span must
    # still surface (attributed to a fallback diagram), never vanish.
    from pumllint.model import Dimension, Severity, Violation

    class StubBatchRule:
        id = "XT999"
        name = "stub-batch"
        applies_to = ("sequence",)

        def check_all(self, diagrams):
            yield Violation(
                rule_id="XT999", message="batch-level finding",
                file_path="t.puml", line=0,  # outside every span
                severity=Severity.MINOR, dimension=Dimension.CONSISTENCY,
            )

    engine = Engine({})
    engine.cross_rules.append(StubBatchRule())
    diagrams = parse_source(_KIND_CONFLICT, "t.puml")
    flat = engine.lint_diagrams(diagrams)
    assert [v for v in flat if v.rule_id == "XT999"]
    groups = engine.lint_diagrams_grouped(diagrams)
    assert [v for _, vs in groups for v in vs if v.rule_id == "XT999"]


def test_cross_findings_dent_the_owning_diagrams_dim_con_score():
    # Per-site reporting: each diagram owns its site's finding, so the
    # penalty lands on both sides of the conflict, not only the minority.
    engine = Engine({})
    groups = engine.lint_diagrams_grouped(parse_source(_KIND_CONFLICT, "t.puml"))
    results = score_groups(groups)
    (_, r_one), (_, r_two) = results
    assert r_one.dimensions[Dimension.CONSISTENCY].score < 100.0
    assert r_two.dimensions[Dimension.CONSISTENCY].score < 100.0


# --- XD004/XD005: cross-*type* entity identity -------------------------------

_CLS_SEQ = """\
@startuml model
title Model
class OrderService <<service>>
class Customer
Customer "1" -- "1..*" OrderService : uses
@enduml
@startuml flow
title Flow
participant {P} {ST}
participant Client
Client -> {P} : place()
@enduml
"""


def _cls_seq(participant="OrderService", stereotype=""):
    return _CLS_SEQ.replace("{P}", participant).replace("{ST}", stereotype)


def test_cross_type_case_drift_fires_xd004_at_the_later_site():
    hits = [v for v in _lint(_cls_seq("orderService")) if v.rule_id == "XD004"]
    assert len(hits) == 1
    assert hits[0].line == 9
    assert "t.puml:3" in hits[0].message  # cites the class site


def test_consistent_cross_type_spelling_is_clean_for_xd004():
    assert not [v for v in _lint(_cls_seq()) if v.rule_id == "XD004"]


def test_swimlane_vs_participant_drift_fires_xd004():
    src = (
        "@startuml act\ntitle Act\n|billing|\nstart\n:Do thing;\nstop\n@enduml\n"
        "@startuml seq\ntitle Flow\nparticipant Billing\nparticipant C\n"
        "C -> Billing : invoice()\n@enduml\n"
    )
    hits = [v for v in _lint(src) if v.rule_id == "XD004"]
    assert len(hits) == 1 and "swimlane" in hits[0].message


def test_sequence_only_collisions_are_left_to_xd003():
    src = (
        "@startuml one\ntitle A\nparticipant Pay\nparticipant C\nC -> Pay : x()\n@enduml\n"
        "@startuml two\ntitle B\nparticipant pay\nparticipant C\nC -> pay : y()\n@enduml\n"
    )
    ids = {v.rule_id for v in _lint(src)}
    assert "XD003" in ids and "XD004" not in ids


def test_cross_type_stereotype_conflict_fires_xd005():
    hits = [v for v in _lint(_cls_seq(stereotype="<<gateway>>")) if v.rule_id == "XD005"]
    assert [v.line for v in hits] == [3, 9]  # class site and participant site
    for v in hits:
        assert "<<service>> ×1" in v.message and "<<gateway>> ×1" in v.message
    assert hits[0].message.startswith("Class ")
    assert hits[1].message.startswith("Participant ")


def test_authoritative_pick_works_for_xd005():
    cfg = {"rules": {"XD005": {"authoritative": {"OrderService": "service"}}}}
    hits = [
        v for v in _lint(_cls_seq(stereotype="<<gateway>>"), cfg)
        if v.rule_id == "XD005"
    ]
    assert [v.line for v in hits] == [9]  # the drifted participant site only
    assert "<<service>> is the configured stereotype" in hits[0].message


def test_agreeing_cross_type_stereotypes_are_clean_for_xd005():
    assert not [v for v in _lint(_cls_seq(stereotype="<<service>>")) if v.rule_id == "XD005"]


def test_state_names_are_not_entities_for_xd004():
    src = (
        "@startuml sm\ntitle SM\n[*] --> open\nopen --> [*]\n@enduml\n"
        "@startuml seq\ntitle Flow\nparticipant Open\nparticipant C\nC -> Open : go()\n@enduml\n"
    )
    assert not [v for v in _lint(src) if v.rule_id == "XD004"]
