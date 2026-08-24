"""BDD-flavoured tests for the codegen-readiness profile (SEQ101–SEQ109).

Each rule gets its violation + passing scenario straight from the spec's
Gherkin, plus tests for the profile mechanism itself (disabled by default,
`profile:` selection, `enable:` lists, `escalate:` severity overrides).
"""

from pumllint.engine import Engine
from pumllint.model import Severity
from pumllint.parser import parse_source

CODEGEN = {"profile": "codegen"}


def lint(source: str, config: dict | None = None):
    engine = Engine({**CODEGEN, **(config or {})})
    return engine.lint_diagrams(parse_source(source, "test.puml"))


def rule_ids(source: str, config: dict | None = None) -> set[str]:
    return {v.rule_id for v in lint(source, config)}


def violations_for(source: str, rule_id: str, config: dict | None = None):
    return [v for v in lint(source, config) if v.rule_id == rule_id]


def puml(body: str) -> str:
    return f"@startuml\n{body}\n@enduml\n"


# --- profile mechanism -------------------------------------------------------

def test_codegen_rules_are_disabled_without_the_profile():
    src = puml("participant OrderService\nOrderService -> PaymentGateway : charge(orderId)")
    ids = {v.rule_id for v in Engine({}).lint_diagrams(parse_source(src, "test.puml"))}
    assert not any(i.startswith("SEQ1") for i in ids)


def test_cli_style_profile_activates_codegen_rules():
    src = puml("participant OrderService\nOrderService -> PaymentGateway : charge(orderId)")
    assert "SEQ101" in rule_ids(src)


def test_profile_enable_list_activates_a_gated_rule_without_matching_profile():
    src = puml("participant OrderService\nOrderService -> PaymentGateway : charge(orderId)")
    cfg = {"profile": "strict", "profiles": {"strict": {"enable": ["SEQ101"]}}}
    ids = {v.rule_id for v in Engine(cfg).lint_diagrams(parse_source(src, "test.puml"))}
    assert "SEQ101" in ids
    assert "SEQ102" not in ids  # not enabled, profile name doesn't match


def test_profile_escalate_overrides_severity_of_existing_rule():
    src = puml("participant A\nparticipant B\nA -> B : go()")  # no title -> GEN001
    cfg = {
        "profile": "codegen",
        "profiles": {"codegen": {"escalate": {"GEN001": "blocker"}}},
    }
    v = [x for x in Engine(cfg).lint_diagrams(parse_source(src, "t.puml")) if x.rule_id == "GEN001"]
    assert v and v[0].severity == Severity.BLOCKER


def test_escalation_wins_over_explicit_rule_severity():
    # A profile is an opt-in quality gate: its escalations override even
    # rule-level severity settings from the base config.
    src = puml("participant A\nparticipant B\nA -> B : go()")
    cfg = {
        "profile": "codegen",
        "profiles": {"codegen": {"escalate": {"GEN001": "blocker"}}},
        "rules": {"GEN001": {"severity": "info"}},
    }
    v = [x for x in Engine(cfg).lint_diagrams(parse_source(src, "t.puml")) if x.rule_id == "GEN001"]
    assert v and v[0].severity == Severity.BLOCKER


def test_codegen_rules_do_not_fire_on_activity_diagrams():
    src = "@startuml\ntitle T\nstart\n:Do a thing somehow;\nstop\n@enduml\n"
    assert not any(i.startswith("SEQ1") for i in rule_ids(src))


# --- SEQ101 participants must be explicitly declared -------------------------

def test_seq101_implicit_participant_is_reported_as_blocker():
    src = puml("participant OrderService\nOrderService -> PaymentGateway : charge(orderId)")
    v = violations_for(src, "SEQ101")
    assert v and "PaymentGateway" in v[0].message
    assert v[0].severity == Severity.BLOCKER


def test_seq101_fully_declared_participants_pass():
    src = puml(
        "participant OrderService\nparticipant PaymentGateway\n"
        "OrderService -> PaymentGateway : charge(orderId)"
    )
    assert "SEQ101" not in rule_ids(src)


# --- SEQ102 declarations must carry a role type or stereotype ----------------

def test_seq102_untyped_generic_participant_is_reported_as_major():
    src = puml(
        "participant Billing\nactor Customer\nCustomer -> Billing : requestInvoice(orderId)"
    )
    v = violations_for(src, "SEQ102")
    assert v and "Billing" in v[0].message
    assert v[0].severity == Severity.MAJOR
    assert all("Customer" not in x.message for x in v)  # actor is typed


def test_seq102_typed_and_stereotyped_participants_pass():
    src = puml(
        "actor Customer\nparticipant Billing <<service>>\ndatabase InvoiceDB\n"
        "Customer -> Billing : requestInvoice(orderId)"
    )
    assert "SEQ102" not in rule_ids(src)


# --- SEQ103 messages must be operation signatures ----------------------------

def test_seq103_prose_message_is_reported_as_blocker():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : fetch the order details"
    )
    v = violations_for(src, "SEQ103")
    assert v and "fetch the order details" in v[0].message
    assert v[0].severity == Severity.BLOCKER


def test_seq103_signature_form_message_passes():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : findOrderById(orderId)"
    )
    assert "SEQ103" not in rule_ids(src)


def test_seq103_reply_arrows_are_exempt_from_the_parenthesis_requirement():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : findOrderById(orderId)\n"
        "OrderDB --> OrderService : order"
    )
    assert "SEQ103" not in rule_ids(src)


def test_seq103_prose_hidden_inside_parentheses_is_reported():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : handle(the payment stuff)"
    )
    v = violations_for(src, "SEQ103")
    assert v and "prose" in v[0].message
    assert v[0].severity == Severity.BLOCKER


def test_seq103_function_word_argument_is_reported():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : load_config(explicit path or auto-detect)"
    )
    v = violations_for(src, "SEQ103")
    assert v and "prose" in v[0].message


def test_seq103_typed_dotted_and_two_word_parameters_pass():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : charge(orderId, order.total)\n"
        "OrderService -> OrderDB : find(id: OrderId)\n"
        "OrderService -> OrderDB : store(Order order)\n"
        "OrderService -> OrderDB : poll()"
    )
    assert "SEQ103" not in rule_ids(src)


def test_seq103_quoted_literal_argument_passes():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        'OrderService -> OrderDB : log("user not found")'
    )
    assert "SEQ103" not in rule_ids(src)


def test_seq103_argument_lexicon_and_width_are_configurable():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : handle(the payment stuff)"
    )
    lenient = {"rules": {"SEQ103": {"arg_stop_words": ["foo"], "max_arg_words": 5}}}
    assert "SEQ103" not in rule_ids(src, lenient)
    strict = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : handle(foo)"
    )
    assert violations_for(strict, "SEQ103", lenient)


# --- SEQ104 synchronous calls must have an explicit return -------------------

def test_seq104_missing_return_message_is_reported_as_major():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : findOrderById(orderId)"
    )
    v = violations_for(src, "SEQ104")
    assert v and "findOrderById(orderId)" in v[0].message
    assert v[0].severity == Severity.MAJOR


def test_seq104_call_with_named_return_value_passes():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : findOrderById(orderId)\n"
        "OrderDB --> OrderService : order"
    )
    assert "SEQ104" not in rule_ids(src)


def test_seq104_async_messages_are_exempt():
    src = puml(
        "participant OrderService <<service>>\nqueue Events\n"
        "OrderService ->> Events : orderPlaced(orderId)"
    )
    assert "SEQ104" not in rule_ids(src)


def test_seq104_return_keyword_counts_as_a_reply():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : findOrderById(orderId)\n"
        "activate OrderDB\nreturn order"
    )
    assert "SEQ104" not in rule_ids(src)


# --- SEQ105 fragment guards must be machine-evaluable ------------------------

def test_seq105_vague_guard_is_reported_as_blocker():
    src = puml(
        "participant OrderService <<service>>\nparticipant PaymentGateway <<external>>\n"
        "alt sometimes\nOrderService -> PaymentGateway : charge(orderId, amount)\nend"
    )
    v = violations_for(src, "SEQ105")
    assert v and "sometimes" in v[0].message
    assert v[0].severity == Severity.BLOCKER


def test_seq105_empty_guard_is_reported():
    src = puml(
        "participant A <<service>>\nparticipant B <<service>>\n"
        "opt\nA -> B : ping()\nend"
    )
    assert violations_for(src, "SEQ105")


def test_seq105_boolean_expression_guard_passes():
    src = puml(
        "participant OrderService <<service>>\nparticipant PaymentGateway <<external>>\n"
        "alt order.total > 0\n"
        "OrderService -> PaymentGateway : charge(orderId, order.total)\n"
        "else [else]\n"
        "OrderService -> OrderService : markFree(orderId)\n"
        "end"
    )
    assert "SEQ105" not in rule_ids(src)


def test_seq105_unguarded_else_is_reported():
    src = puml(
        "participant A <<service>>\nparticipant B <<service>>\n"
        "alt x > 0\nA -> B : f(x)\nelse\nA -> B : g(x)\nend"
    )
    assert violations_for(src, "SEQ105")


def test_seq105_vagueness_lexicon_is_configurable():
    src = puml(
        "participant A <<service>>\nparticipant B <<service>>\n"
        "alt when the stars align\nA -> B : f(x)\nend"
    )
    assert "SEQ105" not in rule_ids(src)
    cfg = {"rules": {"SEQ105": {"vague_terms": ["when the stars align"]}}}
    assert "SEQ105" in rule_ids(src, cfg)


# --- SEQ106 no placeholder or elision markers --------------------------------

def test_seq106_elision_marker_in_message_is_reported_as_blocker():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : validateOrder(order) ... etc"
    )
    v = violations_for(src, "SEQ106")
    assert v
    assert v[0].severity == Severity.BLOCKER


def test_seq106_complete_labels_pass():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : validateOrder(order)\n"
        "OrderDB --> OrderService : validationResult"
    )
    assert "SEQ106" not in rule_ids(src)


def test_seq106_tbd_in_note_is_reported():
    src = puml(
        "participant A <<service>>\nparticipant B <<service>>\n"
        "A -> B : process(order)\n"
        "note right : retry policy TBD"
    )
    assert violations_for(src, "SEQ106")


def test_seq106_word_tokens_do_not_match_inside_identifiers():
    # "etc" must not fire inside "fetchOrder"
    src = puml(
        "participant A <<service>>\nparticipant B <<service>>\n"
        "A -> B : fetchOrder(orderId)\nB --> A : order"
    )
    assert "SEQ106" not in rule_ids(src)


# --- SEQ107 external/persistent calls must model a failure path --------------

def test_seq107_unguarded_external_call_is_reported_as_major():
    src = puml(
        "participant OrderService <<service>>\nparticipant PaymentGateway <<external>>\n"
        "OrderService -> PaymentGateway : charge(orderId, amount)\n"
        "PaymentGateway --> OrderService : receipt"
    )
    v = violations_for(src, "SEQ107")
    assert v and "charge(orderId, amount)" in v[0].message
    assert v[0].severity == Severity.MAJOR


def test_seq107_external_call_with_failure_branch_passes():
    src = puml(
        "participant OrderService <<service>>\nparticipant PaymentGateway <<external>>\n"
        "alt charge accepted\n"
        "OrderService -> PaymentGateway : charge(orderId, amount)\n"
        "PaymentGateway --> OrderService : receipt\n"
        "else charge error\n"
        "PaymentGateway --> OrderService : paymentError\n"
        "OrderService -> OrderService : compensate(orderId)\n"
        "end"
    )
    assert "SEQ107" not in rule_ids(src)


def test_seq107_database_calls_need_a_failure_path_too():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : findOrderById(orderId)\n"
        "OrderDB --> OrderService : order"
    )
    assert violations_for(src, "SEQ107")


def test_seq107_calls_to_internal_services_are_not_flagged():
    src = puml(
        "participant A <<service>>\nparticipant B <<service>>\n"
        "A -> B : process(order)\nB --> A : outcome"
    )
    assert "SEQ107" not in rule_ids(src)


def test_seq107_error_group_elsewhere_does_not_exempt_a_call_outside_it():
    # The group must CONTAIN the call — a later error fragment used to
    # exempt every call above it (issue #29).
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : findOrderById(orderId)\n"
        "OrderDB --> OrderService : order\n"
        "group storage error handling\n"
        "OrderService -> OrderService : rollback()\n"
        "end"
    )
    assert violations_for(src, "SEQ107")


def test_seq107_error_group_containing_the_call_exempts_it():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "group storage error handling\n"
        "OrderService -> OrderDB : findOrderById(orderId)\n"
        "OrderDB --> OrderService : order\n"
        "end"
    )
    assert "SEQ107" not in rule_ids(src)


def test_seq107_empty_failure_branch_does_not_count():
    # 'else charge error' with nothing inside declares a failure path
    # without modelling it (issue #29).
    src = puml(
        "participant OrderService <<service>>\nparticipant PaymentGateway <<external>>\n"
        "alt charge accepted\n"
        "OrderService -> PaymentGateway : charge(orderId, amount)\n"
        "PaymentGateway --> OrderService : receipt\n"
        "else charge error\n"
        "end"
    )
    assert violations_for(src, "SEQ107")


def test_seq107_failure_branch_with_only_a_return_still_counts():
    src = puml(
        "participant OrderService <<service>>\nparticipant PaymentGateway <<external>>\n"
        "alt charge accepted\n"
        "OrderService -> PaymentGateway : charge(orderId, amount)\n"
        "PaymentGateway --> OrderService : receipt\n"
        "else charge error\n"
        "return chargeFailed\n"
        "end"
    )
    assert "SEQ107" not in rule_ids(src)


# --- SEQ108 activation lifecycle ---------------------------------------------

def test_seq108_dangling_activation_is_reported_as_major():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : findOrderById(orderId)\n"
        "activate OrderDB\n"
        "OrderDB --> OrderService : order"
    )
    v = violations_for(src, "SEQ108")
    assert v and "OrderDB" in v[0].message
    assert v[0].severity == Severity.MAJOR


def test_seq108_balanced_activations_pass():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : findOrderById(orderId)\n"
        "activate OrderDB\n"
        "OrderDB --> OrderService : order\n"
        "deactivate OrderDB"
    )
    assert "SEQ108" not in rule_ids(src)


def test_seq108_orphan_deactivate_is_reported():
    src = puml(
        "participant A <<service>>\nparticipant B <<service>>\n"
        "A -> B : go(x)\nB --> A : y\ndeactivate B"
    )
    assert violations_for(src, "SEQ108")


# --- SEQ109 replies must use reply arrows and name the value -----------------

def test_seq109_non_informative_reply_label_is_reported_as_minor():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : findOrderById(orderId)\n"
        "OrderDB --> OrderService : ok"
    )
    v = violations_for(src, "SEQ109")
    assert v and "'ok'" in v[0].message
    assert v[0].severity == Severity.MINOR


def test_seq109_named_return_value_on_reply_arrow_passes():
    src = puml(
        "participant OrderService <<service>>\ndatabase OrderDB\n"
        "OrderService -> OrderDB : findOrderById(orderId)\n"
        "OrderDB --> OrderService : order"
    )
    assert "SEQ109" not in rule_ids(src)


def test_seq109_solid_arrow_return_is_reported():
    src = puml(
        "participant A <<service>>\nparticipant B <<service>>\n"
        "A -> B : findUser(userId)\n"
        "B -> A : user"
    )
    assert violations_for(src, "SEQ109")


def test_seq109_qualified_result_name_passes():
    src = puml(
        "participant A <<service>>\nparticipant B <<service>>\n"
        "A -> B : validate(order)\nB --> A : validationResult"
    )
    assert "SEQ109" not in rule_ids(src)


# --- spec's yaml wiring, end to end ------------------------------------------

def test_full_profile_config_shape_from_the_spec():
    cfg = {
        "profile": "codegen",
        "profiles": {
            "codegen": {
                "enable": [f"SEQ10{i}" for i in range(1, 10)],
                "escalate": {"SEQ001": "blocker"},
            }
        },
    }
    src = puml("participant OrderService\nOrderService -> PaymentGateway : do the thing")
    engine = Engine(cfg)
    found = engine.lint_diagrams(parse_source(src, "t.puml"))
    ids = {v.rule_id for v in found}
    assert {"SEQ101", "SEQ102", "SEQ103"} <= ids
