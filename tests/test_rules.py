"""BDD-flavoured tests: each test name reads Given/When/Then-ish."""

from pumllint.engine import Engine
from pumllint.parser import parse_source


def lint(source: str, config: dict | None = None):
    engine = Engine(config or {})
    return engine.lint_diagrams(parse_source(source, "test.puml"))


def rule_ids(source: str, config: dict | None = None) -> set[str]:
    return {v.rule_id for v in lint(source, config)}


CLEAN = """\
@startuml demo
title Demo
actor Customer
participant FrontOffice
Customer -> FrontOffice : Submit application
activate FrontOffice
FrontOffice --> Customer : Acknowledgement
deactivate FrontOffice
@enduml
"""


# --- parser ---------------------------------------------------------------

def test_given_clean_diagram_then_no_violations():
    assert lint(CLEAN) == []


def test_parser_recognizes_declarations_messages_and_activations():
    (d,) = parse_source(CLEAN)
    assert d.name == "demo"
    assert d.diagram_type == "sequence"
    assert set(d.participants) == {"Customer", "FrontOffice"}
    assert len(d.messages) == 2
    assert [a.kind for a in d.activations] == ["activate", "deactivate"]


def test_parser_handles_alias_and_notes():
    src = """\
@startuml x
title T
participant "Front Office" as FrontOffice
actor Customer
note over FrontOffice
  Customer -> Nobody : this must be ignored
end note
Customer -> FrontOffice : Hello
@enduml
"""
    (d,) = parse_source(src)
    assert "FrontOffice" in d.participants
    assert d.participants["FrontOffice"].display_name == "Front Office"
    assert len(d.messages) == 1  # note content ignored


# --- SEQ001 undeclared participant (typo detection) -------------------------

def test_given_typoed_participant_when_linted_then_seq001_fires():
    src = CLEAN.replace("FrontOffice --> Customer", "FrontOffice --> Custmer")
    ids = rule_ids(src)
    assert "SEQ001" in ids


def test_seq001_stays_quiet_when_nothing_is_declared():
    src = "@startuml\ntitle T\nA -> B : hi\nB --> A : ok\n@enduml\n"
    assert "SEQ001" not in rule_ids(src)


# --- SEQ002 unused participant ----------------------------------------------

def test_given_declared_but_unused_participant_then_seq002_fires():
    src = CLEAN.replace("actor Customer", "actor Customer\nparticipant Notary")
    violations = [v for v in lint(src) if v.rule_id == "SEQ002"]
    assert violations and "Notary" in violations[0].message


# --- SEQ003 unbalanced activation ---------------------------------------------

def test_given_activation_never_closed_then_seq003_fires():
    src = CLEAN.replace("deactivate FrontOffice\n", "")
    assert "SEQ003" in rule_ids(src)


def test_return_closes_most_recent_activation():
    src = CLEAN.replace("deactivate FrontOffice", "return done")
    assert "SEQ003" not in rule_ids(src)


def test_deactivate_without_activate_fires_seq003():
    src = "@startuml x\ntitle T\nparticipant A\nparticipant B\nA -> B : go\ndeactivate B\n@enduml\n"
    assert "SEQ003" in rule_ids(src)


def test_plus_plus_shortcut_counts_as_activation():
    src = "@startuml x\ntitle T\nparticipant A\nparticipant B\nA -> B ++ : go\n@enduml\n"
    assert "SEQ003" in rule_ids(src)


# --- SEQ004 unterminated block ---------------------------------------------

def test_given_alt_without_end_then_seq004_fires():
    src = CLEAN.replace("@enduml", "alt happy\nCustomer -> FrontOffice : again\n@enduml")
    assert "SEQ004" in rule_ids(src)


def test_terminated_alt_is_clean():
    src = CLEAN.replace(
        "@enduml", "alt happy\nCustomer -> FrontOffice : again\nend\n@enduml"
    )
    assert "SEQ004" not in rule_ids(src)


# --- SEQ005 unlabelled message ------------------------------------------------

def test_given_message_without_label_then_seq005_fires():
    src = CLEAN.replace("Customer -> FrontOffice : Submit application", "Customer -> FrontOffice")
    assert "SEQ005" in rule_ids(src)


def test_unlabelled_dotted_return_is_tolerated_by_default():
    src = CLEAN.replace("FrontOffice --> Customer : Acknowledgement", "FrontOffice --> Customer")
    assert "SEQ005" not in rule_ids(src)


# --- GEN rules ------------------------------------------------------------

def test_missing_title_and_unnamed_diagram():
    src = "@startuml\nparticipant A\nparticipant B\nA -> B : hi\n@enduml\n"
    ids = rule_ids(src)
    assert {"GEN001", "GEN002"} <= ids


def test_inline_skinparam_flagged_unless_allowed():
    src = CLEAN.replace("title Demo", "title Demo\nskinparam backgroundColor white")
    assert "GEN003" in rule_ids(src)
    cfg = {"rules": {"inline-skinparam": {"allowed": ["backgroundColor"]}}}
    assert "GEN003" not in rule_ids(src, cfg)


def test_naming_convention_configurable():
    src = CLEAN.replace("participant FrontOffice", "participant front_office").replace(
        "FrontOffice", "front_office"
    )
    assert "GEN004" in rule_ids(src)
    cfg = {"rules": {"participant-naming": {"pattern": "^[a-z_]+$", "per_kind": {"actor": "^[A-Z].*$"}}}}
    assert "GEN004" not in rule_ids(src, cfg)


def test_max_participants_threshold():
    body = "\n".join(f"participant P{i}" for i in range(6))
    src = f"@startuml x\ntitle T\n{body}\nP0 -> P1 : hi\n@enduml\n"
    assert "GEN005" not in rule_ids(src)
    assert "GEN005" in rule_ids(src, {"rules": {"max-participants": {"max": 3}}})


def test_rules_can_be_disabled():
    src = "@startuml\nparticipant A\nparticipant B\nA -> B : hi\n@enduml\n"
    cfg = {"rules": {"GEN001": False, "unnamed-diagram": "off"}}
    ids = rule_ids(src, cfg)
    assert "GEN001" not in ids and "GEN002" not in ids


# --- UC001 use case orphans -------------------------------------------------

def test_orphan_actor_in_usecase_diagram():
    src = """\
@startuml uc
title Use cases
:Customer: as Customer
:Auditor: as Auditor
usecase (Submit application) as Submit
Customer --> Submit : initiates
@enduml
"""
    violations = [v for v in lint(src) if v.rule_id == "UC001"]
    assert violations and "Auditor" in violations[0].message


# --- SEQ006 no self message --------------------------------------------------

def test_given_self_message_then_seq006_fires():
    src = CLEAN.replace(
        "Customer -> FrontOffice : Submit application",
        "Customer -> FrontOffice : Submit application\nFrontOffice -> FrontOffice : Validate internally",
    )
    assert "SEQ006" in rule_ids(src)


def test_seq006_respects_allowed_list():
    src = CLEAN.replace(
        "Customer -> FrontOffice : Submit application",
        "Customer -> FrontOffice : Submit application\nFrontOffice -> FrontOffice : Validate internally",
    )
    cfg = {"rules": {"no-self-message": {"allowed": ["FrontOffice"]}}}
    assert "SEQ006" not in rule_ids(src, cfg)


# --- SEQ007 unlabelled block condition ---------------------------------------

def test_given_alt_without_condition_then_seq007_fires():
    src = CLEAN.replace(
        "@enduml", "alt\nCustomer -> FrontOffice : again\nend\n@enduml"
    )
    assert "SEQ007" in rule_ids(src)


def test_labelled_alt_is_clean_for_seq007():
    src = CLEAN.replace(
        "@enduml", "alt happy path\nCustomer -> FrontOffice : again\nend\n@enduml"
    )
    assert "SEQ007" not in rule_ids(src)


# --- inline suppressions -----------------------------------------------------

def test_next_line_suppression_silences_a_single_finding():
    src = CLEAN.replace(
        "FrontOffice --> Customer : Acknowledgement",
        "' pumllint: disable=SEQ006\nFrontOffice -> FrontOffice : internal step",
    )
    assert "SEQ006" not in rule_ids(src)


def test_suppression_works_by_rule_name_too():
    src = CLEAN.replace(
        "FrontOffice --> Customer : Acknowledgement",
        "' pumllint: disable=no-self-message\nFrontOffice -> FrontOffice : internal step",
    )
    assert "SEQ006" not in rule_ids(src)


def test_suppression_only_covers_the_next_line():
    src = CLEAN.replace(
        "FrontOffice --> Customer : Acknowledgement",
        "' pumllint: disable=SEQ006\nFrontOffice -> FrontOffice : one\nFrontOffice -> FrontOffice : two",
    )
    violations = [v for v in lint(src) if v.rule_id == "SEQ006"]
    assert len(violations) == 1 and "two" not in violations[0].message


def test_file_wide_suppression():
    src = "' pumllint: disable-file=GEN001, GEN002\n" + CLEAN.replace("title Demo\n", "")
    ids = rule_ids(src)
    assert "GEN001" not in ids and "GEN002" not in ids


def test_bare_disable_suppresses_all_rules_on_next_line():
    src = CLEAN.replace(
        "FrontOffice --> Customer : Acknowledgement",
        "' pumllint: disable\nFrontOffice -> FrontOffice",
    )
    ids = rule_ids(src)
    assert "SEQ006" not in ids and "SEQ005" not in ids


def test_suppressions_can_be_globally_ignored():
    src = CLEAN.replace(
        "FrontOffice --> Customer : Acknowledgement",
        "' pumllint: disable=SEQ006\nFrontOffice -> FrontOffice : internal step",
    )
    assert "SEQ006" in rule_ids(src, {"suppressions": False})


# --- activity diagrams -------------------------------------------------------

ACTIVITY_CLEAN = """\
@startuml loan-decision
title Loan decision
start
:Receive application;
if (Complete?) then (yes)
  :Score applicant;
else (no)
  :Request documents;
endif
stop
@enduml
"""


def test_activity_diagram_is_detected_and_clean():
    (d,) = parse_source(ACTIVITY_CLEAN)
    assert d.diagram_type == "activity"
    assert [n.kind for n in d.activity_nodes if n.kind in ("start", "stop")] == ["start", "stop"]
    assert lint(ACTIVITY_CLEAN) == []


def test_sequence_rules_do_not_fire_on_activity_diagrams():
    ids = rule_ids(ACTIVITY_CLEAN)
    assert not any(i.startswith("SEQ") for i in ids)


def test_given_no_start_then_act001_fires():
    src = ACTIVITY_CLEAN.replace("start\n", "")
    assert "ACT001" in rule_ids(src)


def test_given_no_stop_then_act002_fires():
    src = ACTIVITY_CLEAN.replace("stop\n", "")
    assert "ACT002" in rule_ids(src)


def test_given_unlabelled_then_branch_then_act003_fires():
    src = ACTIVITY_CLEAN.replace("if (Complete?) then (yes)", "if (Complete?) then")
    assert "ACT003" in rule_ids(src)


def test_given_unlabelled_else_then_act003_fires_unless_configured():
    src = ACTIVITY_CLEAN.replace("else (no)", "else")
    assert "ACT003" in rule_ids(src)
    cfg = {"rules": {"unlabelled-decision-branch": {"require_else_label": False}}}
    assert "ACT003" not in rule_ids(src, cfg)


def test_given_unclosed_while_then_act004_fires():
    src = ACTIVITY_CLEAN.replace("stop\n", "while (More items?) is (yes)\n:Process item;\nstop\n")
    assert "ACT004" in rule_ids(src)
    closed = src.replace("stop\n@enduml", "endwhile (no)\nstop\n@enduml")
    assert "ACT004" not in rule_ids(closed)


def test_activity_fork_and_partition_are_tracked():
    src = """\
@startuml pipeline
title Pipeline
start
partition Intake {
  :Register request;
}
fork
  :Notify sales;
fork again
  :Notify risk;
end fork
stop
@enduml
"""
    (d,) = parse_source(src)
    assert d.diagram_type == "activity"
    assert {b.kind for b in d.blocks} == {"partition", "fork"}
    assert all(b.terminated for b in d.blocks)
    assert lint(src) == []


def test_multiline_action_is_swallowed():
    src = """\
@startuml a
title T
start
:First long action
still the same action;
:Second;
stop
@enduml
"""
    (d,) = parse_source(src)
    actions = [n for n in d.activity_nodes if n.kind == "action"]
    assert len(actions) == 2


# --- backward: the action on a loop's return path ----------------------------

BACKWARD_LOOP = """\
@startuml rework
title Rework
start
:Receive application;
repeat
  :Validate application;
backward :{}
repeat while (Application invalid?) is (Application invalid) not (Application valid)
stop
@enduml
"""


def test_backward_label_is_recorded_under_its_own_kind():
    (d,) = parse_source(BACKWARD_LOOP.format("Request documents;"))
    backward = [n for n in d.activity_nodes if n.kind == "backward"]
    assert [n.label for n in backward] == ["Request documents"]


def test_given_a_backward_action_not_verb_first_then_act006_fires():
    cfg = {"rules": {"ACT006": {"verbs": ["Receive", "Validate", "Request"]}}}
    bad = BACKWARD_LOOP.format("document request;")
    findings = [v for v in lint(bad, cfg) if v.rule_id == "ACT006"]
    assert [v.message for v in findings] == [
        'Activity \'document request\' is not verb-first — name it "verb + object"'
        ' (e.g. "Validate order")'
    ]
    assert "ACT006" not in rule_ids(BACKWARD_LOOP.format("Request documents;"), cfg)


def test_a_backward_action_is_neither_the_start_nor_the_end_of_the_flow():
    """ACT001 and ACT002 report on the first and last *action*. A trailing
    backward line must not become the last one, or an existing ACT002 finding
    silently moves to it."""
    assert rule_ids(BACKWARD_LOOP.format("Request documents;")) == set()
    lines = BACKWARD_LOOP.format("Request documents;").splitlines()
    stopless = "\n".join(l for l in lines if l != "stop") + "\n"
    (violation,) = [v for v in lint(stopless) if v.rule_id == "ACT002"]
    assert violation.line == stopless.splitlines().index("  :Validate application;") + 1


def test_multiline_backward_action_is_swallowed():
    src = BACKWARD_LOOP.format("Request the missing\nsupporting documents;")
    (d,) = parse_source(src)
    backward = [n for n in d.activity_nodes if n.kind == "backward"]
    assert [n.label for n in backward] == ["Request the missing"]


# --- SEQ008 fragment nesting depth -------------------------------------------

def test_given_fragments_nested_beyond_limit_then_seq008_fires():
    body = (
        "alt a\nopt b\nloop c\npar d\n"
        "Customer -> FrontOffice : x\n"
        "end\nend\nend\nend"
    )
    src = CLEAN.replace("@enduml", body + "\n@enduml")
    cfg = {"rules": {"SEQ008": {"max_nesting_depth": 3}}}
    assert "SEQ008" in rule_ids(src, cfg)


def test_shallow_nesting_is_clean_for_seq008():
    body = "alt a\nopt b\nCustomer -> FrontOffice : x\nend\nend"
    src = CLEAN.replace("@enduml", body + "\n@enduml")
    cfg = {"rules": {"SEQ008": {"max_nesting_depth": 3}}}
    assert "SEQ008" not in rule_ids(src, cfg)


def test_seq008_accepts_max_as_an_alias():
    # The cap-family convention (issue #38): both spellings bind.
    body = "alt a\nopt b\nloop c\nCustomer -> FrontOffice : x\nend\nend\nend"
    src = CLEAN.replace("@enduml", body + "\n@enduml")
    assert "SEQ008" in rule_ids(src, {"rules": {"SEQ008": {"max": 2}}})
    assert "SEQ008" in rule_ids(src, {"rules": {"SEQ008": {"max_nesting_depth": 2}}})


def test_seq008_historical_key_wins_over_the_alias():
    body = "alt a\nopt b\nloop c\nCustomer -> FrontOffice : x\nend\nend\nend"
    src = CLEAN.replace("@enduml", body + "\n@enduml")
    cfg = {"rules": {"SEQ008": {"max_nesting_depth": 3, "max": 2}}}
    assert "SEQ008" not in rule_ids(src, cfg)


# --- SEQ009 returns pair with a call -----------------------------------------

def test_given_orphaned_return_then_seq009_fires():
    src = "@startuml x\ntitle T\nparticipant A\nparticipant B\nB --> A : result\n@enduml\n"
    assert "SEQ009" in rule_ids(src)


def test_paired_call_and_return_is_clean_for_seq009():
    src = (
        "@startuml x\ntitle T\nparticipant A\nparticipant B\n"
        "A -> B : query\nB --> A : result\n@enduml\n"
    )
    assert "SEQ009" not in rule_ids(src)


# --- SEQ010 explicit participant ordering ------------------------------------

def test_given_implicit_participant_when_require_order_then_seq010_fires():
    src = "@startuml x\ntitle T\nparticipant A\nA -> B : go\nB --> A : ok\n@enduml\n"
    cfg = {"rules": {"SEQ010": {"require_explicit_order": True}}}
    assert "SEQ010" in rule_ids(src, cfg)


def test_seq010_quiet_when_all_declared_and_disabled_by_default():
    src = (
        "@startuml x\ntitle T\nparticipant A\nparticipant B\n"
        "A -> B : go\nB --> A : ok\n@enduml\n"
    )
    cfg = {"rules": {"SEQ010": {"require_explicit_order": True}}}
    assert "SEQ010" not in rule_ids(src, cfg)  # all declared
    implicit = "@startuml x\ntitle T\nparticipant A\nA -> B : go\n@enduml\n"
    assert "SEQ010" not in rule_ids(implicit)  # off by default


# --- ACT005 swimlane naming --------------------------------------------------

def test_given_lowercase_swimlane_then_act005_fires():
    src = ACTIVITY_CLEAN.replace("start\n", "start\n|billing|\n")
    assert "ACT005" in rule_ids(src)


def test_conforming_swimlane_is_clean_for_act005():
    src = ACTIVITY_CLEAN.replace("start\n", "start\n|Billing|\n")
    assert "ACT005" not in rule_ids(src)


# --- ACT006 verb-first activity names ----------------------------------------

def test_given_noun_phrase_activity_then_act006_fires():
    src = ACTIVITY_CLEAN.replace(":Score applicant;", ":Order validation;")
    cfg = {"rules": {"ACT006": {"verbs": ["Validate", "Receive", "Request"]}}}
    assert "ACT006" in rule_ids(src, cfg)


def test_verb_first_activities_are_clean_for_act006():
    cfg = {"rules": {"ACT006": {"verbs": ["Receive", "Score", "Request"]}}}
    assert "ACT006" not in rule_ids(ACTIVITY_CLEAN, cfg)


_ACT_NOUN = ACTIVITY_CLEAN.replace(":Score applicant;", ":Order validation;")
_VERB_SHAPE = r"^(Receive|Score|Request)\b"


def test_act006_verb_pattern_arms_the_rule_without_a_verbs_list():
    """Issue #47.2: 68 configured verbs, 38 never used. A shape-based
    convention takes a regex instead of a padded list."""
    cfg = {"rules": {"ACT006": {"verb_pattern": _VERB_SHAPE}}}
    findings = [v for v in lint(_ACT_NOUN, cfg) if v.rule_id == "ACT006"]
    assert len(findings) == 1 and "'verb_pattern'" in findings[0].message
    assert "ACT006" not in rule_ids(ACTIVITY_CLEAN, cfg)


def test_act006_listed_verb_passes_beside_a_verb_pattern():
    """An allow-list and an allow-pattern are alternatives: adding a pattern
    never narrows a list, and a label failing both is told about both."""
    cfg = {"rules": {"ACT006": {"verbs": ["Order"], "verb_pattern": _VERB_SHAPE}}}
    assert "ACT006" not in rule_ids(_ACT_NOUN, cfg)
    src = ACTIVITY_CLEAN.replace(":Score applicant;", ":Application review;")
    findings = [v for v in lint(src, cfg) if v.rule_id == "ACT006"]
    assert len(findings) == 1
    assert "first word not in 'verbs' and label does not match 'verb_pattern'" in findings[0].message


def test_act006_message_is_verbatim_when_only_verbs_is_set():
    cfg = {"rules": {"ACT006": {"verbs": ["Receive", "Request"]}}}
    findings = [v for v in lint(_ACT_NOUN, cfg) if v.rule_id == "ACT006"]
    assert findings[0].message == (
        "Activity 'Order validation' is not verb-first — name it "
        '"verb + object" (e.g. "Validate order")'
    )


def test_act006_empty_verb_pattern_does_not_void_the_verbs_list():
    """Compiled, "" matches every label; it must read as "not configured"."""
    cfg = {"rules": {"ACT006": {"verbs": ["Receive", "Request"], "verb_pattern": ""}}}
    assert "ACT006" in rule_ids(_ACT_NOUN, cfg)


# --- UC002 use case / actor naming -------------------------------------------

def test_given_noun_phrase_usecase_then_uc002_fires():
    src = (
        "@startuml uc\ntitle Use cases\nactor Customer\n"
        "usecase (Order placement)\nCustomer --> (Order placement) : does\n@enduml\n"
    )
    cfg = {"rules": {"UC002": {"verbs": ["Place", "Manage"]}}}
    assert "UC002" in rule_ids(src, cfg)


def test_verb_object_usecase_is_clean_for_uc002():
    src = (
        "@startuml uc\ntitle Use cases\nactor Customer\n"
        "usecase (Place order)\nCustomer --> (Place order) : does\n@enduml\n"
    )
    cfg = {"rules": {"UC002": {"verbs": ["Place"]}}}
    assert "UC002" not in rule_ids(src, cfg)


def test_aliased_usecase_is_judged_by_its_label_not_the_alias():
    src = (
        "@startuml uc\ntitle Use cases\nactor Customer\n"
        "usecase (Order placement) as UC1\nCustomer --> UC1 : does\n@enduml\n"
    )
    cfg = {"rules": {"UC002": {"verbs": ["Place", "Manage"]}}}
    findings = [v for v in lint(src, cfg) if v.rule_id == "UC002"]
    assert len(findings) == 1
    assert "'Order placement'" in findings[0].message


_UC_NOUN = (
    "@startuml uc\ntitle Use cases\nactor Customer\n"
    "usecase (Order placement)\nCustomer --> (Order placement) : does\n@enduml\n"
)


def test_uc002_verb_pattern_arms_the_rule_without_a_verbs_list():
    cfg = {"rules": {"UC002": {"verb_pattern": r"^(Place|Manage)\b"}}}
    findings = [v for v in lint(_UC_NOUN, cfg) if v.rule_id == "UC002"]
    assert len(findings) == 1 and "'verb_pattern'" in findings[0].message
    assert "UC002" not in rule_ids(_UC_NOUN.replace("Order placement", "Place order"), cfg)


def test_uc002_listed_verb_passes_beside_a_verb_pattern():
    cfg = {"rules": {"UC002": {"verbs": ["Order"], "verb_pattern": r"^(Place|Manage)\b"}}}
    assert "UC002" not in rule_ids(_UC_NOUN, cfg)


def _usecase(actors: int, cases: int) -> str:
    a = "".join(f"actor A{i}\n" for i in range(actors))
    c = "".join(f"usecase (Case {i})\n" for i in range(cases))
    return f"@startuml uc\ntitle Use cases\n{a}{c}A0 --> (Case 0) : does\n@enduml\n"


def _sequence(n: int) -> str:
    p = "".join(f"participant P{i}\n" for i in range(n))
    return f"@startuml s\ntitle Seq\n{p}P0 -> P1 : hi\n@enduml\n"


def test_gen005_counts_declared_usecase_elements():
    # Counting behaviour, pinned against an explicit budget so it stays a test
    # of *what counts* rather than of the default.
    decls = "".join(f"usecase (Case {i})\n" for i in range(9))
    src = f"@startuml uc\ntitle Use cases\nactor Customer\n{decls}Customer --> (Case 0) : does\n@enduml\n"
    cfg = {"rules": {"GEN005": {"max": 9}}}
    findings = [v for v in lint(src, cfg) if v.rule_id == "GEN005"]
    assert len(findings) == 1
    assert "10 participants" in findings[0].message


def test_gen005_textbook_usecase_diagram_passes_by_default():
    # 3 actors + 7 goals = 10 declared. Under the sequence budget of 9 this
    # reported a minor, which is what a third-party corpus met on first
    # contact: the sequence number counts lifelines, not actors plus goals.
    assert "GEN005" not in rule_ids(_usecase(3, 7))


def test_gen005_oversized_usecase_diagram_is_still_reported():
    findings = [v for v in lint(_usecase(3, 13)) if v.rule_id == "GEN005"]
    assert len(findings) == 1
    assert "16 participants (max 15)" in findings[0].message


def test_gen005_sequence_budget_is_unchanged():
    assert "GEN005" not in rule_ids(_sequence(9))
    findings = [v for v in lint(_sequence(10)) if v.rule_id == "GEN005"]
    assert len(findings) == 1
    assert "10 participants (max 9)" in findings[0].message


def test_gen005_per_type_overrides_the_default_for_that_type_only():
    cfg = {"rules": {"GEN005": {"per_type": {"usecase": 8}}}}
    assert "GEN005" in rule_ids(_usecase(3, 7), cfg)      # 10 > 8
    assert "GEN005" not in rule_ids(_sequence(9), cfg)    # sequence untouched
    cfg = {"rules": {"GEN005": {"per_type": {"sequence": 3}}}}
    assert "GEN005" in rule_ids(_sequence(4), cfg)
    assert "GEN005" not in rule_ids(_usecase(3, 7), cfg)  # usecase untouched


def test_gen005_explicit_max_still_applies_to_every_type():
    # Compatibility pin: a project-wide max keeps its old meaning, so configs
    # written against the shared budget behave exactly as they did.
    cfg = {"rules": {"GEN005": {"max": 9}}}
    assert "GEN005" in rule_ids(_usecase(3, 7), cfg)
    assert "GEN005" in rule_ids(_sequence(10), cfg)


def test_gen005_per_type_beats_an_explicit_max():
    cfg = {"rules": {"GEN005": {"max": 9, "per_type": {"usecase": 20}}}}
    assert "GEN005" not in rule_ids(_usecase(3, 7), cfg)
    assert "GEN005" in rule_ids(_sequence(10), cfg)


def test_gen005_implicit_usecase_endpoints_do_not_count():
    decls = "".join(f"usecase (Case {i})\n" for i in range(8))
    src = f"@startuml uc\ntitle Use cases\nactor Customer\n{decls}Customer --> (Undeclared goal) : asks\n@enduml\n"
    assert "GEN005" not in rule_ids(src)


def test_aliased_usecase_with_verb_first_label_is_clean_for_uc002():
    src = (
        "@startuml uc\ntitle Use cases\nactor Customer\n"
        "usecase (Place order) as UC1\nCustomer --> UC1 : does\n@enduml\n"
    )
    cfg = {"rules": {"UC002": {"verbs": ["Place"]}}}
    assert "UC002" not in rule_ids(src, cfg)


# --- UC003 include/extend direction ------------------------------------------

UC_BASE = "@startuml uc\ntitle Checkout\nusecase (Checkout)\n:Customer: --> (Checkout)\n"


def test_given_reversed_extend_then_uc003_fires():
    src = UC_BASE + "(Checkout) ..> (Apply coupon) : <<extend>>\n@enduml\n"
    hits = [v for v in lint(src) if v.rule_id == "UC003"]
    assert [v.line for v in hits] == [5]


def test_given_reversed_include_then_uc003_fires():
    src = UC_BASE + "(Validate cart) ..> (Checkout) : <<include>>\n@enduml\n"
    assert "UC003" in rule_ids(src)


def test_given_include_from_actor_then_uc003_fires():
    src = (
        "@startuml uc\ntitle Checkout\nusecase (Checkout)\n"
        ":Customer: ..> (Checkout) : <<include>>\n@enduml\n"
    )
    hits = [v for v in lint(src) if v.rule_id == "UC003"]
    assert hits and "actor" in hits[0].message


def test_correct_include_and_extend_directions_are_clean_for_uc003():
    src = (
        UC_BASE
        + "(Checkout) ..> (Validate cart) : <<include>>\n"
        + "(Apply coupon) ..> (Checkout) : <<extend>>\n@enduml\n"
    )
    assert "UC003" not in rule_ids(src)


def test_right_to_left_arrows_are_normalized_for_uc003():
    # (Checkout) <.. (Apply coupon) means Apply coupon → Checkout: correct.
    src = UC_BASE + "(Checkout) <.. (Apply coupon) : <<extend>>\n@enduml\n"
    assert "UC003" not in rule_ids(src)
    (d,) = parse_source(src)
    link = next(l for l in d.usecase_links if l.stereotype == "extend")
    assert (link.source, link.target) == ("Apply coupon", "Checkout")


def test_uc003_stays_silent_without_actor_evidence():
    src = "@startuml uc\ntitle UC\nusecase (A)\n(A) ..> (B) : <<include>>\n@enduml\n"
    assert "UC003" not in rule_ids(src)


def test_usecase_links_still_unpack_as_tuples():
    (d,) = parse_source(UC_BASE + "@enduml\n")
    src, dst, line = d.usecase_links[0]
    assert (src, dst, line) == ("Customer", "Checkout", 4)


# --- CLS class-diagram pack -------------------------------------------------

CLASS_CLEAN = """\
@startuml shop-model
title Shop model
class Customer {
  +name: String
  --
  +placeOrder(item: Item): Order
}
abstract class BaseEntity
interface Payable <<service>>
BaseEntity <|-- Customer
Customer "1" -- "1..*" Order : places
Order ..|> Payable
@enduml
"""


def test_class_diagram_is_detected_and_clean():
    (d,) = parse_source(CLASS_CLEAN)
    assert d.diagram_type == "class"
    assert set(d.classes) == {"Customer", "BaseEntity", "Payable", "Order"}
    assert d.classes["Customer"].kind == "class"
    assert d.classes["BaseEntity"].kind == "abstract"
    assert d.classes["Payable"].stereotype == "service"
    assert [m.name for m in d.classes["Customer"].members] == ["name", "placeOrder"]
    assert d.classes["Customer"].members[1].is_method
    assert [r.kind for r in d.class_relations] == [
        "extension", "association", "realization",
    ]
    assert d.element_count == len(d.classes) + len(d.class_relations)
    assert lint(CLASS_CLEAN) == []


def test_generalization_arrow_types_an_unknown_diagram_as_class():
    (d,) = parse_source("@startuml t\ntitle T\nA <|-- B\n@enduml\n")
    assert d.diagram_type == "class"
    rel = d.class_relations[0]
    assert (rel.child, rel.parent) == ("B", "A")


def test_class_parser_never_retypes_a_sequence_diagram():
    src = CLEAN + "\n@startuml cls\ntitle Cls\nclass Foo\n@enduml\n"
    seq, cls = parse_source(src)
    assert seq.diagram_type == "sequence"
    assert not seq.classes
    assert cls.diagram_type == "class"


def test_sequence_rules_do_not_fire_on_class_diagrams():
    assert not any(i.startswith("SEQ") for i in rule_ids(CLASS_CLEAN))


def test_given_snake_case_class_then_cls001_fires():
    src = "@startuml m\ntitle M\nclass order_service\n@enduml\n"
    assert "CLS001" in rule_ids(src)


def test_given_pascal_case_member_then_cls001_fires_but_enum_is_exempt():
    src = (
        "@startuml m\ntitle M\nclass Order {\n  +PlaceOrder()\n}\n"
        "enum Status {\n  OPEN\n  CLOSED\n}\n@enduml\n"
    )
    hits = [v for v in lint(src) if v.rule_id == "CLS001"]
    assert [v.line for v in hits] == [4]


def test_cls001_patterns_are_configurable():
    src = "@startuml m\ntitle M\nclass order_service\n@enduml\n"
    cfg = {"rules": {"CLS001": {"class_pattern": r"^[a-z_]+$"}}}
    assert "CLS001" not in rule_ids(src, cfg)


def test_given_association_without_multiplicities_then_cls002_fires():
    src = "@startuml m\ntitle M\nclass A\nclass B\nA -- B : owns\n@enduml\n"
    assert "CLS002" in rule_ids(src)
    src_one_end = "@startuml m\ntitle M\nclass A\nclass B\nA \"1\" -- B : owns\n@enduml\n"
    assert "CLS002" in rule_ids(src_one_end)


def test_generalization_needs_no_multiplicities_for_cls002():
    src = "@startuml m\ntitle M\nclass A\nclass B\nA <|-- B\nA <.. B\n@enduml\n"
    assert "CLS002" not in rule_ids(src)


def test_given_unlabelled_association_then_cls003_fires():
    src = '@startuml m\ntitle M\nclass A\nclass B\nA "1" -- "1..*" B\n@enduml\n'
    assert "CLS003" in rule_ids(src)


def test_aggregation_and_composition_are_exempt_from_cls003():
    src = (
        '@startuml m\ntitle M\nclass A\nclass B\n'
        'A "1" o-- "0..*" B\nA "1" *-- "1..*" B\n@enduml\n'
    )
    assert "CLS003" not in rule_ids(src)


def test_given_inheritance_cycle_then_cls004_fires_once_citing_the_cycle():
    src = "@startuml m\ntitle M\nA <|-- B\nB <|-- C\nC <|-- A\n@enduml\n"
    hits = [v for v in lint(src) if v.rule_id == "CLS004"]
    assert len(hits) == 1
    assert "A" in hits[0].message and "->" in hits[0].message


def test_acyclic_hierarchy_is_clean_for_cls004():
    src = "@startuml m\ntitle M\nA <|-- B\nA <|-- C\n@enduml\n"
    assert "CLS004" not in rule_ids(src)


def test_given_too_many_members_then_cls005_fires():
    members = "\n".join(f"  +field{i}: int" for i in range(16))
    src = f"@startuml m\ntitle M\nclass Order {{\n{members}\n}}\n@enduml\n"
    assert "CLS005" in rule_ids(src)
    assert "CLS005" not in rule_ids(src, {"rules": {"CLS005": {"max": 20}}})


def test_member_shorthand_counts_toward_cls005():
    src = (
        "@startuml m\ntitle M\nclass Order\n"
        + "\n".join(f"Order : +field{i}" for i in range(4))
        + "\n@enduml\n"
    )
    cfg = {"rules": {"CLS005": {"max": 3}}}
    assert "CLS005" in rule_ids(src, cfg)


# --- STA state-diagram pack --------------------------------------------------

STATE_CLEAN = """\
@startuml door
title Door lifecycle
state "Wide open" as Open <<external>>
state Operating {
  [*] --> Idle
  Idle --> Busy : work requested
  --
  [*] --> Monitoring
}
[*] --> Open
Open --> Operating : engage [armed]
Operating --> Open : release
Open --> [*]
@enduml
"""


def test_state_diagram_is_detected_and_clean():
    (d,) = parse_source(STATE_CLEAN)
    assert d.diagram_type == "state"
    assert set(d.states) == {"Open", "Operating", "Idle", "Busy", "Monitoring"}
    assert d.states["Open"].display_name == "Wide open"
    assert d.states["Open"].stereotype == "external"
    assert d.states["Operating"].composite
    assert d.states["Idle"].container == "Operating"
    assert d.element_count == len(d.states) + len(d.transitions)
    assert lint(STATE_CLEAN) == []


def test_state_parser_never_retypes_a_sequence_diagram():
    src = CLEAN + "\n@startuml sm\ntitle SM\n[*] --> Idle\nIdle --> [*]\n@enduml\n"
    seq, sm = parse_source(src)
    assert seq.diagram_type == "sequence"
    assert not seq.states
    assert sm.diagram_type == "state"


def test_sequence_rules_do_not_fire_on_state_diagrams():
    assert not any(i.startswith("SEQ") for i in rule_ids(STATE_CLEAN))


def test_given_no_initial_transition_then_sta001_fires():
    src = "@startuml sm\ntitle SM\nstate Open\nstate Closed\nOpen --> Closed : close\n@enduml\n"
    hits = [v for v in lint(src) if v.rule_id == "STA001"]
    assert [v.line for v in hits] == [1]


def test_given_duplicate_initial_transitions_then_sta001_fires_on_the_second():
    src = "@startuml sm\ntitle SM\n[*] --> Open\n[*] --> Closed\nOpen --> Closed : close\n@enduml\n"
    hits = [v for v in lint(src) if v.rule_id == "STA001"]
    assert [v.line for v in hits] == [4]


def test_composite_inner_initial_is_not_top_level_for_sta001():
    assert "STA001" not in rule_ids(STATE_CLEAN)


def test_given_state_without_incoming_transition_then_sta002_fires():
    src = "@startuml sm\ntitle SM\n[*] --> Open\nOpen --> [*]\nstate Suspended\n@enduml\n"
    hits = [v for v in lint(src) if v.rule_id == "STA002"]
    assert [v.line for v in hits] == [5]


def test_self_transition_does_not_make_a_state_reachable_for_sta002():
    src = (
        "@startuml sm\ntitle SM\n[*] --> Open\nOpen --> [*]\n"
        "Suspended --> Suspended : tick\n@enduml\n"
    )
    assert "STA002" in rule_ids(src)


def test_given_unlabelled_transition_then_sta003_fires_but_pseudo_states_are_exempt():
    src = "@startuml sm\ntitle SM\n[*] --> Idle\nIdle --> Active\nActive --> [*]\n@enduml\n"
    hits = [v for v in lint(src) if v.rule_id == "STA003"]
    assert [v.line for v in hits] == [4]


def test_labelled_and_styled_transitions_are_clean_for_sta003():
    src = (
        "@startuml sm\ntitle SM\n[*] --> Idle\n"
        "Idle -[#red]-> Active : powerOn [selfTestOk]\n"
        "Active -down-> Idle : powerOff\nActive --> [*]\n@enduml\n"
    )
    assert "STA003" not in rule_ids(src)


def test_state_description_shorthand_is_consumed_not_mistaken():
    src = (
        "@startuml sm\ntitle SM\n[*] --> Idle\nIdle --> [*]\n"
        "Idle : waiting for input\n@enduml\n"
    )
    (d,) = parse_source(src)
    assert set(d.states) == {"Idle"}
    assert lint(src) == []


# --- GEN006-009 / SEQ011: TRC & RDB thickening -------------------------------

def test_parser_records_header_footer_caption_directives():
    src = (
        "@startuml demo\ntitle Demo\nheader Confidential\n"
        "footer Owner: team-x\ncaption Fig. 1\nparticipant A\nparticipant B\nA -> B : hi\n@enduml\n"
    )
    (d,) = parse_source(src)
    kinds = {dir.kind for dir in d.directives}
    assert {"header", "footer", "caption"} <= kinds


def test_gen006_and_gen007_are_dormant_without_a_pattern():
    ids = rule_ids(CLEAN)
    assert "GEN006" not in ids and "GEN007" not in ids


def test_given_pattern_and_no_owner_tag_then_gen006_fires():
    cfg = {"rules": {"GEN006": {"pattern": r"(?i)owner\s*:"}}}
    assert "GEN006" in rule_ids(CLEAN, cfg)
    tagged = CLEAN.replace("title Demo", "title Demo\nfooter Owner: team-x")
    assert "GEN006" not in rule_ids(tagged, cfg)


def test_given_pattern_and_no_requirement_link_then_gen007_fires():
    cfg = {"rules": {"GEN007": {"pattern": r"REQ-\d+|ADR-\d+"}}}
    assert "GEN007" in rule_ids(CLEAN, cfg)
    named = CLEAN.replace("@startuml demo", "@startuml REQ-142-demo")
    assert "GEN007" not in rule_ids(named, cfg)


def test_given_note_heavy_diagram_then_gen008_fires():
    notes = "note over Customer : blah\n" * 4
    src = CLEAN.replace("@enduml", notes + "@enduml")
    assert "GEN008" in rule_ids(src)


def test_few_notes_are_clean_for_gen008():
    src = CLEAN.replace("@enduml", "note over Customer : blah\n" * 3 + "@enduml")
    assert "GEN008" not in rule_ids(src)


def test_gen008_length_cap_catches_prose_heavy_notes_when_configured():
    prose = "note over Customer : " + "narrated protocol prose " * 8
    src = CLEAN.replace("@enduml", prose + "\n@enduml")
    assert "GEN008" not in rule_ids(src)  # count path alone stays quiet
    cfg = {"rules": {"GEN008": {"max_chars_per_element": 10}}}
    assert "GEN008" in rule_ids(src, cfg)


def test_gen008_length_cap_passes_short_notes():
    src = CLEAN.replace("@enduml", "note over Customer : ok\n@enduml")
    cfg = {"rules": {"GEN008": {"max_chars_per_element": 10}}}
    assert "GEN008" not in rule_ids(src, cfg)


def test_given_oversized_diagram_then_gen009_fires():
    cfg = {"rules": {"GEN009": {"max": 3}}}
    assert "GEN009" in rule_ids(CLEAN, cfg)  # 2 participants + 2 messages = 4
    assert "GEN009" not in rule_ids(CLEAN)  # default max 60


def test_given_too_many_messages_then_seq011_fires_on_first_excess():
    msgs = "".join(f"Customer -> FrontOffice : m{i}\n" for i in range(3))
    src = CLEAN.replace("@enduml", msgs + "@enduml")
    cfg = {"rules": {"SEQ011": {"max": 2}}}
    hits = [v for v in lint(src, cfg) if v.rule_id == "SEQ011"]
    assert len(hits) == 1
    (d,) = parse_source(src)
    assert hits[0].line == d.messages[2].line
    assert "SEQ011" not in rule_ids(src)  # default max 30


# --- Sonar reporter --------------------------------------------------------

def test_sonar_reporter_emits_valid_generic_issue_format():
    import json

    from pumllint.reporters import get_reporter

    src = "@startuml\nparticipant A\nparticipant B\nA -> B : hi\n@enduml\n"
    payload = json.loads(get_reporter("sonar").render(lint(src)))
    assert set(payload) == {"rules", "issues"}
    assert all(i["primaryLocation"]["textRange"]["startLine"] >= 1 for i in payload["issues"])
    rule_ids_used = {i["ruleId"] for i in payload["issues"]}
    assert rule_ids_used <= {r["id"] for r in payload["rules"]}


def test_whitespace_only_usecase_name_does_not_crash_armed_uc002():
    # Regression for the IndexError at p.name.split()[0]: a whitespace-only
    # name passes the `not p.name` truthiness guard, and .split() is empty.
    # The run must complete; the element itself is UC001/GEN004 territory.
    src = (
        "@startuml uc\ntitle Use cases\nactor Customer\n"
        'usecase "   "\nusecase (Place order)\n'
        "Customer --> (Place order) : does\n@enduml\n"
    )
    cfg = {"rules": {"UC002": {"verbs": ["Place"]}}}
    assert "UC002" not in rule_ids(src, cfg)
