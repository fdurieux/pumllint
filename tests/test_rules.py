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
