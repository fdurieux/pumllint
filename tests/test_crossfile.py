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


def test_case_collision_fires_at_every_site_including_implicit_participants():
    # Both spellings are reported, each message carrying the whole variant
    # set: no spelling is elected. Until 2026-09-03 only the site differing
    # from the first-seen spelling fired — so which site that was, and hence
    # which diagram's DIM-CON dropped, depended on batch order.
    src = (
        "@startuml one\nparticipant Client\nparticipant OrderSvc\nClient -> OrderSvc : run()\n@enduml\n"
        "@startuml two\nparticipant Client\nClient -> Ordersvc : query()\n@enduml\n"
    )
    hits = [v for v in _lint(src) if v.rule_id == "XD003"]
    assert [v.line for v in hits] == [3, 8]  # declared site and implicit site
    for v in hits:
        assert "'OrderSvc' ×1" in v.message and "'Ordersvc' ×1" in v.message
        assert " but " not in v.message  # no site is told to conform to another


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


def test_cross_type_case_drift_fires_xd004_at_every_site():
    hits = [v for v in _lint(_cls_seq("orderService")) if v.rule_id == "XD004"]
    assert [v.line for v in hits] == [3, 9]  # class site and participant site
    assert hits[0].message.startswith("Class ")
    assert hits[1].message.startswith("Participant ")
    for v in hits:
        assert "'OrderService' ×1" in v.message and "'orderService' ×1" in v.message


def test_consistent_cross_type_spelling_is_clean_for_xd004():
    assert not [v for v in _lint(_cls_seq()) if v.rule_id == "XD004"]


def test_swimlane_vs_participant_drift_fires_xd004():
    src = (
        "@startuml act\ntitle Act\n|billing|\nstart\n:Do thing;\nstop\n@enduml\n"
        "@startuml seq\ntitle Flow\nparticipant Billing\nparticipant C\n"
        "C -> Billing : invoice()\n@enduml\n"
    )
    hits = [v for v in _lint(src) if v.rule_id == "XD004"]
    assert {v.message.split()[0] for v in hits} == {"Swimlane", "Participant"}


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


# -- the `distinct` option: deliberately different entities -------------------

_STEREO_CONFLICT = """\
@startuml one
participant Svc <<x>>
participant Peer
Svc -> Peer : go()
@enduml
@startuml two
queue Svc <<y>>
participant Peer
Svc -> Peer : go()
@enduml
"""

_CROSS_TYPE_STEREO = """\
@startuml sales
class Order <<aggregate>>
@enduml
@startuml checkout
participant Order <<work-order>>
participant Peer
Order -> Peer : place()
@enduml
"""


def test_distinct_silences_xd001_for_the_named_entity_only():
    cfg = {"rules": {"XD001": {"distinct": ["Svc"]}}}
    assert not [v for v in _lint(_STEREO_CONFLICT, cfg) if v.rule_id == "XD001"]
    other = {"rules": {"XD001": {"distinct": ["SomethingElse"]}}}
    assert len([v for v in _lint(_STEREO_CONFLICT, other) if v.rule_id == "XD001"]) == 2


def test_distinct_silences_xd002():
    cfg = {"rules": {"XD002": {"distinct": ["Svc"]}}}
    assert not [v for v in _lint(_STEREO_CONFLICT, cfg) if v.rule_id == "XD002"]


def test_distinct_matches_case_insensitively_for_xd003():
    src = (
        "@startuml one\nparticipant Ledger\nLedger -> Ledger : s()\n@enduml\n"
        "@startuml two\nparticipant ledger\nledger -> ledger : s()\n@enduml\n"
    )
    assert [v.rule_id for v in _xd(_lint(src))] == ["XD003", "XD003"]  # both sites
    cfg = {"rules": {"XD003": {"distinct": ["LEDGER"]}}}
    assert not [v for v in _lint(src, cfg) if v.rule_id == "XD003"]


def test_distinct_matches_case_insensitively_for_xd004():
    src = (
        "@startuml cls\nclass OrderService\n@enduml\n"
        "@startuml seq\nparticipant orderService\nparticipant B\n"
        "orderService -> B : x()\n@enduml\n"
    )
    assert [v.rule_id for v in _xd(_lint(src)) if v.rule_id == "XD004"] == ["XD004", "XD004"]
    cfg = {"rules": {"XD004": {"distinct": ["orderservice"]}}}
    assert not [v for v in _lint(src, cfg) if v.rule_id == "XD004"]


def test_distinct_silences_xd005_bounded_context_homonyms():
    assert len([v for v in _lint(_CROSS_TYPE_STEREO) if v.rule_id == "XD005"]) == 2
    cfg = {"rules": {"XD005": {"distinct": ["Order"]}}}
    assert not [v for v in _lint(_CROSS_TYPE_STEREO, cfg) if v.rule_id == "XD005"]


def test_distinct_and_authoritative_compose():
    # distinct removes one entity from the join; authoritative still pins another
    src = (
        "@startuml one\nparticipant Svc <<x>>\nparticipant Gate <<a>>\n"
        "Svc -> Gate : go()\n@enduml\n"
        "@startuml two\nparticipant Svc <<y>>\nparticipant Gate <<b>>\n"
        "Svc -> Gate : go()\n@enduml\n"
    )
    cfg = {"rules": {"XD002": {"distinct": ["Svc"], "authoritative": {"Gate": "a"}}}}
    hits = [v for v in _lint(src, cfg) if v.rule_id == "XD002"]
    assert len(hits) == 1 and "Gate" in hits[0].message and "<<a>>" in hits[0].message


def test_distinct_tolerates_a_malformed_value():
    cfg = {"rules": {"XD001": {"distinct": "Svc"}}}  # not a list: ignored
    assert len([v for v in _lint(_STEREO_CONFLICT, cfg) if v.rule_id == "XD001"]) == 2


# --- batch order is not an input --------------------------------------------
#
# Found 2026-09-03 re-deriving the pilot census: the same 159 files scored
# {L2:9, L3:35} in one order and {L2:8, L3:36} in another. XD003 and XD004
# kept the first spelling they met as the reference and flagged only the
# sites that differed, so which diagram was blamed — and, through XD004's
# pairwise sequence-internal skip, how many findings existed — followed argv
# order. Directory sweeps sort, so this only surfaced on explicit file
# lists: exactly what pre-commit hands the hooks. The golden snapshot cannot
# see any of it, since it scores corpus units one diagram at a time and the
# XD pack never runs under it. This is that guard.

def _diagrams(*named):
    return [parse_source(src, path)[0] for path, src in named]


def _fingerprint(diagrams):
    """Per-diagram (findings, level, composite), keyed by file — the things a
    batch order must not be able to move."""
    engine = Engine({})
    groups = engine.lint_diagrams_grouped(diagrams)
    scored = score_groups(groups, engine=engine)
    out = {}
    for (d, vs), (_, r) in zip(groups, scored):
        out[d.file_path] = (
            sorted((v.rule_id, v.line) for v in vs),
            r.level,
            round(r.composite, 2),
        )
    return out


def _assert_order_invariant(*named):
    from itertools import permutations

    base = _diagrams(*named)
    reference = _fingerprint(base)
    for perm in permutations(base):
        got = _fingerprint(list(perm))
        assert got == reference, (
            [d.file_path for d in perm], got, reference
        )
    total = sum(len(f) for f, _, _ in reference.values())
    assert total > 0, "the fixture must actually trip a cross rule"
    return reference


def test_xd004_finding_count_does_not_depend_on_batch_order():
    # The count-drop case: a sequence diagram whose own participants collide
    # by case, plus a class of the same name. Pairwise, the sequence-internal
    # pair was skipped when a sequence site was the reference (XD003 would
    # own it — but XD003 needs two sequence diagrams and there is one) and
    # reported when the class site was. 1 finding vs 2, by order.
    ref = _assert_order_invariant(
        ("a_seq.puml", "@startuml a\ntitle A\nparticipant Api\nApi -> api : ping()\n@enduml\n"),
        ("b_class.puml", "@startuml b\ntitle B\nclass API\n@enduml\n"),
    )
    xd = {p: [f for f in fs if f[0] == "XD004"] for p, (fs, _, _) in ref.items()}
    assert len(xd["a_seq.puml"]) == 2 and len(xd["b_class.puml"]) == 1


def test_xd003_owner_does_not_depend_on_batch_order():
    # The owner-flip case: two sequence diagrams, one `Api`, one `api`. The
    # total was stable, so a model-set aggregate hid it, while every
    # per-diagram score moved with whichever file was passed second.
    ref = _assert_order_invariant(
        ("one.puml", "@startuml a\ntitle A\nparticipant Api\nApi -> Db : get()\n@enduml\n"),
        ("two.puml", "@startuml b\ntitle B\nparticipant api\napi -> Db : get()\n@enduml\n"),
    )
    assert all(any(f[0] == "XD003" for f in fs) for fs, _, _ in ref.values())


def test_level_histogram_does_not_depend_on_batch_order():
    # The census shape: a class and two sequence diagrams sharing one entity
    # under two spellings. Pairwise this produced {L3:3} in one order and
    # {L4:2, L3:1} in another.
    ref = _assert_order_invariant(
        ("k.puml", "@startuml k\ntitle K\nclass OrderService\n@enduml\n"),
        ("b.puml", "@startuml b\ntitle B\nparticipant orderservice\nparticipant C\nC -> orderservice : x()\n@enduml\n"),
        ("c.puml", "@startuml c\ntitle C\nparticipant orderservice\nparticipant C\nC -> orderservice : y()\n@enduml\n"),
    )
    assert len({lvl for _, lvl, _ in ref.values()}) >= 1  # shape asserted by invariance above


def test_xd003_and_xd004_honour_the_authoritative_spelling():
    # With a pin, only the non-conforming sites are reported — the same
    # contract XD001/XD002/XD005 already offer. The pin is looked up
    # case-insensitively, since that is how these two rules join.
    cfg = {"rules": {"XD003": {"authoritative": {"ORDERSVC": "OrderSvc"}},
                     "XD004": {"authoritative": {"orderservice": "OrderService"}}}}
    src = (
        "@startuml one\nparticipant Client\nparticipant OrderSvc\nClient -> OrderSvc : run()\n@enduml\n"
        "@startuml two\nparticipant Client\nparticipant Ordersvc\nClient -> Ordersvc : query()\n@enduml\n"
    )
    hits = [v for v in _lint(src, config=cfg) if v.rule_id == "XD003"]
    assert [v.line for v in hits] == [8] and "'OrderSvc' is the configured spelling" in hits[0].message
    hits = [v for v in _lint(_cls_seq("orderService"), config=cfg) if v.rule_id == "XD004"]
    assert [v.line for v in hits] == [9] and "'OrderService' is the configured spelling" in hits[0].message


# --- GEN010 duplicate-diagram-name (2026-09-04) ------------------------------
#
# The governance pack's one cross-diagram rule, and a within-file one: two
# diagrams in one file sharing a name both get the finding. The batch is the
# file, so the engine's two-diagram gate is met by the file itself.

_GEN010_BODY = "title T\nparticipant A\nparticipant B\nA -> B : hi\n"


def _blocks(*names) -> str:
    return "".join(
        (f"@startuml {n}\n" if n else "@startuml\n") + _GEN010_BODY + "@enduml\n"
        for n in names
    )


def _gen010(src: str, path: str = "f.puml"):
    diagrams = parse_source(src, path)
    return sorted(
        (v.line, v.message)
        for v in Engine({}).lint_diagrams(diagrams)
        if v.rule_id == "GEN010"
    )


def test_gen010_reports_every_site_of_a_repeated_name():
    found = _gen010(_blocks("order", "order"))
    assert [line for line, _ in found] == [1, 7], found
    assert all(
        "'order' is used 2 times in this file (lines 1, 7)" in m for _, m in found
    ), found


def test_gen010_joins_neither_an_ordinal_looking_name_nor_the_unnamed():
    assert [line for line, _ in _gen010(_blocks("Dup", "Dup", "Dup#1"))] == [1, 7]
    assert _gen010(_blocks(None, None)) == []  # GEN002's territory
    assert _gen010(_blocks("order", "shipment")) == []


def test_gen010_is_scoped_to_one_file():
    diagrams = parse_source(_blocks("order"), "a.puml") + parse_source(
        _blocks("order"), "b.puml"
    )
    hits = [v for v in Engine({}).lint_diagrams(diagrams) if v.rule_id == "GEN010"]
    assert hits == [], hits


def test_gen010_does_not_depend_on_batch_order():
    from itertools import permutations

    diagrams = parse_source(_blocks("order", "other", "order"), "f.puml")

    def fingerprint(batch):
        engine = Engine({})
        groups = engine.lint_diagrams_grouped(batch)
        scored = score_groups(groups, engine=engine)
        return {
            d.start_line: (
                sorted((v.rule_id, v.line) for v in vs),
                r.level,
                round(r.composite, 2),
            )
            for (d, vs), (_, r) in zip(groups, scored)
        }

    reference = fingerprint(diagrams)
    flagged = [line for line, (fs, _, _) in reference.items() if ("GEN010", line) in fs]
    assert flagged == [1, 13], reference
    for perm in permutations(diagrams):
        assert fingerprint(list(perm)) == reference, [d.start_line for d in perm]

