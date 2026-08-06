"""Acceptance suite for the CargoQuote adversarial-threshold system (W0 kit).

Encodes the INTENDED behavior of CargoQuote instant freight quotation,
hand-derived from the full artifact kit in stack_experiment/cargo_quote/
(normative semantics: contract/decision_table.md — DT-V/DT-S/DT-P).
Degraded or partial artifact conditions describe the same intended
system with less information, so this one suite scores code generated
from every W1 condition.

STATUS: authored in W0 and smoke-calibrated against the hand-written
reference implementation only (stack_experiment/cargo_quote/
reference_impl.py via stack_experiment/smoke_test.py — 11/11, plus
three prior-following mutants each caught). It is NOT yet frozen: the
house calibration protocol (generation-calibration against pristine
generated artifacts, then freeze) runs at W1 pre-registration. Editing
a scenario after any non-calibration result has been computed
invalidates the wave — re-freeze consciously.

Executed by the frozen tools/acceptance/runner_child.py (unchanged).

Overlay mechanism, generalizing the c4_loan_suite precedent: the runner
has only success/failure outcome classes, and CargoQuote has four
non-binary outcomes plus exact-price rules. OVERLAYS maps scenario ->
{"require_re", "forbid_re"} applied by the driver to the serialized
outcome (lowercased detail) AFTER a runner pass: the scenario passes
iff the runner passed AND require_re matches AND forbid_re does not.
Price overlays match the rounded price loosely ("8652\\.4") so float
dust in unrounded implementations does not misclassify.

Scenario map (sensitivity class in brackets — [flow] = pinned by the
behavior artifact, [contract] = pinned only by the decision tables,
[prior-inverting] = adversarial against model priors, pinned by
behavior + contract):

   1 quoted_low_risk      risk 8, w 400, d 900 -> quoted; screen+engine+store+notify called [flow]
   2 accept_boundary_41   risk 41 -> quoted, not review/refused [contract]
   3 review_boundary_42   risk 42 -> review_hold; no price, no notification [contract]
   4 refuse_boundary_67   risk 67 -> refused_screening; refusal IS notified; engine NOT called [contract + prior-inverting]
   5 refuse_high_risk     risk 93 -> refused_screening; engine NOT called [flow]
   6 price_exact_heavy    w 2000, d 1000 -> price 3186.00 (flat surcharge) [contract]
   7 price_exact_both     w 1500, d 5000 -> price 8652.49; 8592.45 (inverted P2/P3 order) forbidden [contract]
   8 invalid_weight_low   w 2 -> rejected; screen and notify MUST NOT be called [contract + flow]
   9 invalid_value_over   declared 90000 -> rejected; screen MUST NOT be called [contract]
  10 screening_down_hold  screening raises -> held_unscreened WITH price, no notification [prior-inverting]
  11 store_down_error     store raises -> error; screen and notify MUST NOT be called [flow]

The suite lexicon extends the shared house lexicon with the success
token "quoted" (CargoQuote's issued-quote status word appears in no
house token). review_hold and held_unscreened deliberately classify as
"unknown" and are asserted via expect "any" + overlays, like the C4
borderline_review precedent.
"""

from .suites import LEXICONS

CARGO_LEXICONS = {
    "success": list(LEXICONS["success"]) + ["quoted"],
    "failure": list(LEXICONS["failure"]),
}


def _num(v):
    return {"_protean": "num", "value": v}


def _obj(fields, truthy=True):
    return {"_protean": "obj", "fields": fields, "truthy": truthy}


_SCREEN_CLS = ["screening", "screen", "sanction", "compliance", "denied"]
_DB_CLS = ["quotestore", "store", "repository", "database"]
_NOTIF_CLS = ["notification", "notifier", "notify"]
_ENGINE_CLS = ["tariff", "engine"]

_SCREEN_METH = ["screen", "check", "risk", "index", "assess", "verify",
                "lookup", "evaluate", "get", "fetch", "request"]
_DB_STORE_METH = ["store", "save", "persist", "insert", "write", "record",
                  "add", "create", "update"]
_NOTIF_METH = ["send", "notify", "dispatch", "deliver", "email", "message"]
_ENGINE_METH = ["price", "compute", "calculate", "quote", "rate", "cost",
                "tariff"]


def _stub_screen(risk=8, action="value"):
    stub = {
        "name": "screen_shipper", "cls_like": _SCREEN_CLS,
        "method_like": _SCREEN_METH, "action": "return", "value": _num(risk),
    }
    if action == "error":
        stub.update({
            "action": "raise",
            # Deliberately NO generic tokens ("unavail", "service"): with two
            # error-stubbed collaborators, a token both exception names contain
            # would raise the wrong type (smoke-test finding, W0).
            "exc_like": ["screen", "sanction"],
            "exc_msg": "screeningUnavailableError: screening service timeout",
            "raise_fallback": "return_failure",
            "failure_value": _obj(
                {"status": "error", "error": "screening_unavailable",
                 "success": False, "risk_index": None}, truthy=False),
        })
    return stub


def _stub_db(action="value"):
    stub = {
        "name": "store_quote", "cls_like": _DB_CLS,
        "method_like": _DB_STORE_METH, "action": "return",
        "value": _obj({"status": "stored", "stored": True, "success": True,
                       "quote_id": "Q-1", "id": "Q-1"}),
    }
    if action == "error":
        stub.update({
            "action": "raise",
            # Same rule as the screening stub: no token that could match the
            # screening exception class ("unavail" is in both names).
            "exc_like": ["stor", "database", "db", "persist"],
            "exc_msg": "storeUnavailableError: quote store unavailable",
            "raise_fallback": "return_failure",
            "failure_value": _obj(
                {"status": "error", "error": "store_unavailable",
                 "success": False, "stored": False}, truthy=False),
        })
    return stub


def _stub_notify():
    return {
        "name": "send_notification", "cls_like": _NOTIF_CLS,
        "method_like": _NOTIF_METH, "action": "return",
        "value": _obj({"status": "sent", "sent": True, "success": True}),
    }


def _request(weight=400, distance=900, value=20000, risk=8,
             screening="ok", db="stored", notify="sent"):
    return {
        "shipper_id": "SHIP-1", "shipper": "SHIP-1", "customer_id": "SHIP-1",
        "client_id": "SHIP-1",
        "weight_kg": weight, "weight": weight, "weight_in_kg": weight,
        "mass_kg": weight,
        "distance_km": distance, "distance": distance, "route_km": distance,
        "declared_value": value, "cargo_value": value, "value_declared": value,
        "risk_index": risk, "risk": risk, "screening_risk": risk,
        "screening_result": screening, "screening_status": screening,
        "db_status": db, "db_result": db, "storage_status": db,
        "store_result": db,
        "notify_status": notify, "notification_result": notify,
    }


SUITE = {
    "entry_cls_like": ["quoteapi", "quoteservice"],
    "entry_cls_fallback": ["api", "service", "quote"],
    "entry_method_like": ["handle", "requestquote", "quote", "submit",
                          "process", "run", "execute"],
    "entry_func_like": ["handle", "requestquote", "process", "main", "run"],
    "args": {
        "shipper_id": "SHIP-1",
        "weight_kg": _num(400), "distance_km": _num(900),
        "declared_value": _num(20000),
        "request": _obj({
            "shipper_id": "SHIP-1", "weight_kg": _num(400),
            "distance_km": _num(900), "declared_value": _num(20000),
        }),
        "quote": _obj({
            "shipper_id": "SHIP-1", "weight_kg": _num(400),
            "distance_km": _num(900), "declared_value": _num(20000),
            "id": "Q-1", "quote_id": "Q-1",
        }),
    },
    "lexicons": CARGO_LEXICONS,
    "scenarios": {
        "quoted_low_risk": {
            "stubs": [_stub_screen(8), _stub_db(), _stub_notify()],
            "expect": "success",
            "must_call": [
                {"cls_like": _SCREEN_CLS, "method_like": _SCREEN_METH},
                {"cls_like": _ENGINE_CLS, "method_like": _ENGINE_METH},
                {"cls_like": _DB_CLS, "method_like": _DB_STORE_METH},
                {"cls_like": _NOTIF_CLS, "method_like": _NOTIF_METH},
            ],
            "request": _request(risk=8),
        },
        "accept_boundary_41": {
            "stubs": [_stub_screen(41), _stub_db(), _stub_notify()],
            "expect": "success",
            "must_call": [
                {"cls_like": _SCREEN_CLS, "method_like": _SCREEN_METH},
            ],
            "request": _request(risk=41),
        },
        "review_boundary_42": {
            "stubs": [_stub_screen(42), _stub_db(), _stub_notify()],
            "expect": "any",
            "must_call": [
                {"cls_like": _SCREEN_CLS, "method_like": _SCREEN_METH},
                {"cls_like": _DB_CLS, "method_like": _DB_STORE_METH},
            ],
            "must_not_call": [
                {"cls_like": _NOTIF_CLS, "method_like": _NOTIF_METH},
            ],
            "request": _request(risk=42),
        },
        "refuse_boundary_67": {
            "stubs": [_stub_screen(67), _stub_db(), _stub_notify()],
            "expect": "failure",
            "failure_like": ["refus", "risk", "screen", "denied", "reject"],
            "must_call": [
                {"cls_like": _SCREEN_CLS, "method_like": _SCREEN_METH},
                {"cls_like": _NOTIF_CLS, "method_like": _NOTIF_METH},
            ],
            "must_not_call": [
                {"cls_like": _ENGINE_CLS, "method_like": _ENGINE_METH},
            ],
            "request": _request(risk=67),
        },
        "refuse_high_risk": {
            "stubs": [_stub_screen(93), _stub_db(), _stub_notify()],
            "expect": "failure",
            "failure_like": ["refus", "risk", "screen", "denied", "reject"],
            "must_call": [
                {"cls_like": _SCREEN_CLS, "method_like": _SCREEN_METH},
            ],
            "must_not_call": [
                {"cls_like": _ENGINE_CLS, "method_like": _ENGINE_METH},
            ],
            "request": _request(risk=93),
        },
        "price_exact_heavy": {
            "stubs": [_stub_screen(8), _stub_db(), _stub_notify()],
            "expect": "success",
            "must_call": [
                {"cls_like": _ENGINE_CLS, "method_like": _ENGINE_METH},
            ],
            "request": _request(weight=2000, distance=1000, risk=8),
        },
        "price_exact_both": {
            "stubs": [_stub_screen(8), _stub_db(), _stub_notify()],
            "expect": "success",
            "must_call": [
                {"cls_like": _ENGINE_CLS, "method_like": _ENGINE_METH},
            ],
            "request": _request(weight=1500, distance=5000, risk=8),
        },
        "invalid_weight_low": {
            "stubs": [_stub_screen(8), _stub_db(), _stub_notify()],
            "expect": "failure",
            "failure_like": ["invalid", "reject", "weight"],
            "must_not_call": [
                {"cls_like": _SCREEN_CLS, "method_like": _SCREEN_METH},
                {"cls_like": _NOTIF_CLS, "method_like": _NOTIF_METH},
            ],
            "request": _request(weight=2),
        },
        "invalid_value_over": {
            "stubs": [_stub_screen(8), _stub_db(), _stub_notify()],
            "expect": "failure",
            "failure_like": ["invalid", "reject", "value", "exceed"],
            "must_not_call": [
                {"cls_like": _SCREEN_CLS, "method_like": _SCREEN_METH},
            ],
            "request": _request(value=90000),
        },
        "screening_down_hold": {
            "stubs": [_stub_screen(action="error"), _stub_db(),
                      _stub_notify()],
            "expect": "any",
            "must_call": [
                {"cls_like": _ENGINE_CLS, "method_like": _ENGINE_METH},
                {"cls_like": _DB_CLS, "method_like": _DB_STORE_METH},
            ],
            "must_not_call": [
                {"cls_like": _NOTIF_CLS, "method_like": _NOTIF_METH},
            ],
            "request": _request(screening="error"),
        },
        "store_down_error": {
            "stubs": [_stub_screen(8), _stub_db(action="error"),
                      _stub_notify()],
            "expect": "failure",
            "failure_like": ["stor", "persist", "database", "unavail",
                             "save"],
            "must_not_call": [
                {"cls_like": _SCREEN_CLS, "method_like": _SCREEN_METH},
                {"cls_like": _NOTIF_CLS, "method_like": _NOTIF_METH},
            ],
            "request": _request(db="error"),
        },
    },
}

# Driver-side overlays (see module docstring): applied to the lowercased
# serialized outcome AFTER a runner pass. Pass iff require_re matches and
# forbid_re (when set) does not.
OVERLAYS = {
    "accept_boundary_41": {
        "require_re": r"quoted",
        "forbid_re": r"review|refus|held",
    },
    "review_boundary_42": {
        "require_re": r"review|hold",
        "forbid_re": r"quoted|refus|approv|declin",
    },
    "price_exact_heavy": {
        "require_re": r"3186",
        "forbid_re": None,
    },
    "price_exact_both": {
        "require_re": r"8652\.4",
        "forbid_re": r"8592\.4",
    },
    "screening_down_hold": {
        "require_re": r"held|hold|unscreened",
        "forbid_re": r"error|fail|reject|refus|unavailable",
    },
}
