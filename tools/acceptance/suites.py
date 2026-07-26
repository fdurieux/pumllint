"""Acceptance suites for the execution oracle — one per scenario family.

Each suite encodes the INTENDED behavior of its family, hand-derived from
the pristine L5 diagram (degraded variants describe the same intended
system — degradation removes information, it does not change what the
system is supposed to do). The hypothesis these suites test: code
generated from degraded diagrams fails more of the intended behavior when
actually executed.

FROZEN at pre-registration (EVIDENCE.md §Execution oracle). Editing a
scenario after any non-calibration result has been computed invalidates
the wave — re-freeze consciously, the way golden scores are re-frozen.

Design notes (why these scenarios and not more):
- order_payment (examples/order_payment_codegen_good.puml): find order
  (found / notFoundError), guard total > 0, charge (receipt /
  paymentError -> compensate self-call). 4 scenarios.
- insurance_claim (examples/insurance_claim_good.puml): findPolicy
  (active / policyLapsedError), assessRisk (score / riskServiceError),
  guard amount <= coverageLimit, storeClaim (claimRecord / storageError).
  5 scenarios.
- credit_intake (examples/credit_intake_good.puml): the accept/reject
  threshold is unspecified EVEN IN THE PRISTINE DIAGRAM (the family tops
  out at L2 under the codegen profile), so branch direction cannot be
  asserted — its scenarios check flow shape (engine consulted, a decision
  produced, no crash) at three stub scores. 3 scenarios.
- Scenarios whose guard-else the diagram leaves underspecified
  (zero_total, over_limit) assert only the interaction contract
  (charge/store must not happen) with expect="any".
"""

LEXICONS = {
    "success": [
        "success", "succeed", "confirm", "receipt", "complete", "approved",
        "approve", "offer", "proposal", "stored", "claimrecord", "charged",
        "paid", "accepted", "processed", "transaction", "txn", "ok",
    ],
    "failure": [
        "error", "fail", "reject", "declin", "notfound", "not found",
        "missing", "laps", "denied", "cancel", "exceed", "insufficient",
        "invalid", "unable", "exception", "refus", "expired", "inactive",
        "unavailable", "no such", "unknown order", "unknown policy",
    ],
}


def _num(v):
    return {"_protean": "num", "value": v}


def _obj(fields, truthy=True):
    return {"_protean": "obj", "fields": fields, "truthy": truthy}


# ------------------------------------------------------------ order_payment

_OP_DB = ["orderdb", "database", "db", "repository", "repo", "store"]
_OP_GW = ["paymentgateway", "gateway", "payment"]
_OP_FIND = ["find", "get", "lookup", "load", "fetch", "retrieve"]
_OP_CHARGE = ["charge", "pay", "authorize", "debit", "capture", "transact", "process"]

def _op_order(total):
    return _obj({
        "total": total, "amount": total, "order_id": "ORD-1", "id": "ORD-1",
        "status": "found", "order": "ORD-1",
    })

_OP_RECEIPT = _obj({
    "success": True, "status": "approved", "receipt": "receipt",
    "transaction_id": "txn-1", "amount": 100,
})

def _op_stub_find(action="value", total=100):
    stub = {
        "name": "db_find", "cls_like": _OP_DB, "method_like": _OP_FIND,
        "action": "return", "value": _op_order(total),
    }
    if action == "notfound":
        stub.update({
            "action": "raise",
            "exc_like": ["notfound", "not_found", "missing", "noorder", "lookup"],
            "exc_msg": "notFoundError: order ORD-1 not found",
            "raise_fallback": "return_none",
        })
    return stub

def _op_stub_charge(action="value"):
    stub = {
        "name": "gateway_charge", "cls_like": _OP_GW, "method_like": _OP_CHARGE,
        "action": "return", "value": _OP_RECEIPT,
    }
    if action == "error":
        stub.update({
            "action": "raise",
            "exc_like": ["payment", "charge", "declin", "gateway"],
            "exc_msg": "paymentError: charge declined by gateway",
            "raise_fallback": "return_failure",
            "failure_value": _obj(
                {"success": False, "status": "declined", "error": "paymentError"},
                truthy=False,
            ),
        })
    return stub

_ORDER_PAYMENT = {
    "entry_cls_like": ["orderservice"],
    "entry_cls_fallback": ["service", "order"],
    "entry_method_like": [
        "processpayment", "process", "pay", "charge", "handle", "execute",
        "run", "place", "settle",
    ],
    "entry_func_like": ["process", "handle", "main", "run", "pay"],
    "args": {
        "order_id": "ORD-1", "orderid": "ORD-1", "id": "ORD-1",
        "customer_id": "CUST-1", "customer": "CUST-1",
        "amount": _num(100), "total": _num(100),
        "order": _op_order(100),
    },
    "scenarios": {
        "happy_path": {
            "stubs": [_op_stub_find(), _op_stub_charge()],
            "expect": "success",
            "must_call": [{"cls_like": _OP_GW, "method_like": _OP_CHARGE}],
            "request": {
                "order_id": "ORD-1", "order_exists": True, "order_found": True,
                "order_total": 100, "amount": 100,
                "payment_result": "approved", "payment_status": "approved",
                "gateway_result": "approved", "charge_result": "approved",
            },
        },
        "order_not_found": {
            "stubs": [_op_stub_find("notfound"), _op_stub_charge()],
            "expect": "failure",
            "failure_like": ["notfound", "not found", "missing", "no order",
                             "unknown", "no such"],
            "must_not_call": [{"cls_like": _OP_GW, "method_like": _OP_CHARGE}],
            "request": {
                "order_id": "ORD-404", "order_exists": False,
                "order_found": False, "order_total": 100, "amount": 100,
                "payment_result": "approved", "payment_status": "approved",
                "gateway_result": "approved", "charge_result": "approved",
            },
        },
        "payment_error": {
            "stubs": [_op_stub_find(), _op_stub_charge("error")],
            "expect": "failure",
            "failure_like": ["payment", "declin", "charge", "gateway"],
            "must_call": [{
                "cls_like": ["*"],
                "method_like": ["compensat", "refund", "rollback", "revert",
                                "reverse", "undo"],
            }],
            "request": {
                "order_id": "ORD-1", "order_exists": True, "order_found": True,
                "order_total": 100, "amount": 100,
                "payment_result": "declined", "payment_status": "declined",
                "gateway_result": "declined", "charge_result": "declined",
            },
        },
        "zero_total": {
            "stubs": [_op_stub_find(total=0), _op_stub_charge()],
            "expect": "any",
            "must_not_call": [{"cls_like": _OP_GW, "method_like": _OP_CHARGE}],
            "request": {
                "order_id": "ORD-1", "order_exists": True, "order_found": True,
                "order_total": 0, "amount": 0,
                "payment_result": "approved", "payment_status": "approved",
                "gateway_result": "approved", "charge_result": "approved",
            },
        },
    },
}


# ---------------------------------------------------------- insurance_claim

_IC_REG = ["policyregistry", "registry", "policy"]
_IC_FRAUD = ["fraudchecker", "fraud", "risk"]
_IC_DB = ["claimdb", "database", "db", "repo", "storage", "store"]
_IC_FINDPOL = ["findpolicy", "find", "get", "lookup", "load", "fetch", "retrieve"]
_IC_ASSESS = ["assess", "check", "evaluate", "score", "analyz", "rate"]
_IC_STORE = ["store", "save", "persist", "insert", "write", "record"]

def _ic_policy(limit):
    return _obj({
        "status": "active", "active": True, "coverage_limit": limit,
        "coverageLimit": limit, "limit": limit, "policy_id": "POL-1",
        "id": "POL-1",
    })

def _ic_stub_policy(action="value", limit=10000):
    stub = {
        "name": "registry_find_policy", "cls_like": _IC_REG,
        "method_like": _IC_FINDPOL, "action": "return",
        "value": _ic_policy(limit),
    }
    if action == "lapsed":
        stub.update({
            "action": "raise",
            "exc_like": ["laps", "policy", "inactive", "expired"],
            "exc_msg": "policyLapsedError: policy POL-1 lapsed",
            "raise_fallback": "return_failure",
            "failure_value": _obj(
                {"status": "lapsed", "active": False, "error": "policyLapsedError"},
                truthy=False,
            ),
        })
    return stub

def _ic_stub_risk(action="value"):
    stub = {
        "name": "fraud_assess_risk", "cls_like": _IC_FRAUD,
        "method_like": _IC_ASSESS, "action": "return", "value": _num(12),
    }
    if action == "error":
        stub.update({
            "action": "raise",
            "exc_like": ["risk", "fraud", "service", "unavailable"],
            "exc_msg": "riskServiceError: risk service unavailable",
            "raise_fallback": "return_failure",
            "failure_value": _obj(
                {"status": "error", "error": "riskServiceError"}, truthy=False,
            ),
        })
    return stub

def _ic_stub_store(action="value"):
    stub = {
        "name": "db_store_claim", "cls_like": _IC_DB, "method_like": _IC_STORE,
        "action": "return",
        "value": _obj({"status": "stored", "claim_record": "claimRecord",
                       "id": "CLM-1"}),
    }
    if action == "error":
        stub.update({
            "action": "raise",
            "exc_like": ["storage", "store", "database", "db", "persist"],
            "exc_msg": "storageError: could not store claim CLM-1",
            "raise_fallback": "return_failure",
            "failure_value": _obj(
                {"status": "error", "error": "storageError"}, truthy=False,
            ),
        })
    return stub

def _ic_claim(amount):
    return _obj({
        "amount": amount, "claim_id": "CLM-1", "id": "CLM-1",
        "policy_id": "POL-1", "claim_amount": amount,
    })

def _ic_scenario(policy="value", risk="value", store="value",
                 amount=500, limit=10000):
    return {
        "stubs": [_ic_stub_policy(policy, limit), _ic_stub_risk(risk),
                  _ic_stub_store(store)],
        # every amount carrier must agree — artifacts read claim.amount,
        # claim_amount or a bare amount param interchangeably
        "args_override": {"amount": amount, "claim_amount": amount,
                          "claim": _ic_claim(amount)},
    }

_INSURANCE_CLAIM = {
    "entry_cls_like": ["claimservice"],
    "entry_cls_fallback": ["service", "claim"],
    "entry_method_like": [
        "processclaim", "process", "submit", "file", "handle", "intake",
        "register", "execute", "run",
    ],
    "entry_func_like": ["process", "handle", "main", "run", "submit", "file"],
    "args": {
        "claim": _ic_claim(500), "claim_id": "CLM-1", "claimid": "CLM-1",
        "id": "CLM-1", "policy_id": "POL-1", "policyid": "POL-1",
        "amount": _num(500), "claim_amount": _num(500),
    },
    "scenarios": {
        "happy_path": {
            **_ic_scenario(),
            "expect": "success",
            "must_call": [{"cls_like": _IC_DB, "method_like": _IC_STORE}],
            "request": {"claim_id": "CLM-1", "policy_id": "POL-1",
                        "claim_amount": 500, "amount": 500,
                        "policy_status": "active", "policy_result": "active",
                        "coverage_limit": 10000, "risk_result": "assessed",
                        "risk_status": "assessed", "fraud_result": "assessed",
                        "risk_score": 12, "storage_result": "stored",
                        "storage_status": "stored", "db_result": "stored"},
        },
        "policy_lapsed": {
            **_ic_scenario(policy="lapsed"),
            "expect": "failure",
            "failure_like": ["laps", "polic", "inactive", "expired"],
            "must_not_call": [{"cls_like": _IC_DB, "method_like": _IC_STORE}],
            "request": {"claim_id": "CLM-1", "policy_id": "POL-1",
                        "claim_amount": 500, "amount": 500,
                        "policy_status": "lapsed", "policy_result": "lapsed",
                        "coverage_limit": 10000, "risk_result": "assessed",
                        "risk_status": "assessed", "fraud_result": "assessed",
                        "risk_score": 12, "storage_result": "stored",
                        "storage_status": "stored", "db_result": "stored"},
        },
        "risk_service_error": {
            **_ic_scenario(risk="error"),
            "expect": "failure",
            "failure_like": ["risk", "fraud", "service"],
            "must_not_call": [{"cls_like": _IC_DB, "method_like": _IC_STORE}],
            "request": {"claim_id": "CLM-1", "policy_id": "POL-1",
                        "claim_amount": 500, "amount": 500,
                        "policy_status": "active", "policy_result": "active",
                        "coverage_limit": 10000, "risk_result": "error",
                        "risk_status": "error", "fraud_result": "error",
                        "storage_result": "stored",
                        "storage_status": "stored", "db_result": "stored"},
        },
        "over_coverage_limit": {
            **_ic_scenario(amount=50000, limit=10000),
            "expect": "any",
            "must_not_call": [{"cls_like": _IC_DB, "method_like": _IC_STORE}],
            "request": {"claim_id": "CLM-1", "policy_id": "POL-1",
                        "claim_amount": 50000, "amount": 50000,
                        "policy_status": "active", "policy_result": "active",
                        "coverage_limit": 10000, "risk_result": "assessed",
                        "risk_status": "assessed", "fraud_result": "assessed",
                        "risk_score": 12, "storage_result": "stored",
                        "storage_status": "stored", "db_result": "stored"},
        },
        "storage_error": {
            **_ic_scenario(store="error"),
            "expect": "failure",
            "failure_like": ["stor", "persist", "database", "db"],
            "must_call": [{"cls_like": _IC_DB, "method_like": _IC_STORE}],
            "request": {"claim_id": "CLM-1", "policy_id": "POL-1",
                        "claim_amount": 500, "amount": 500,
                        "policy_status": "active", "policy_result": "active",
                        "coverage_limit": 10000, "risk_result": "assessed",
                        "risk_status": "assessed", "fraud_result": "assessed",
                        "risk_score": 12, "storage_result": "error",
                        "storage_status": "error", "db_result": "error"},
        },
    },
}


# ------------------------------------------------------------ credit_intake

_CI_ENGINE = ["creditengine", "engine", "credit", "scoring"]
_CI_SCORE = ["score", "assess", "evaluate", "rate", "calculate", "check"]

def _ci_scenario(score):
    return {
        "stubs": [{
            "name": "engine_score", "cls_like": _CI_ENGINE,
            "method_like": _CI_SCORE, "action": "return", "value": _num(score),
        }],
        "expect": "decision",
        "must_call": [{"cls_like": _CI_ENGINE, "method_like": _CI_SCORE}],
    }

_CREDIT_INTAKE = {
    "entry_cls_like": ["frontoffice", "front"],
    "entry_cls_fallback": ["office", "service", "intake"],
    "entry_method_like": [
        "submit", "process", "handle", "apply", "application", "intake",
        "receive", "run", "execute",
    ],
    "entry_func_like": ["process", "handle", "main", "run", "submit", "apply"],
    "args": {
        "application": _obj({"applicant": "Jane Doe", "name": "Jane Doe",
                             "amount": 10000, "customer": "Jane Doe"}),
        # customer/applicant may receive callbacks (receive_offer, notify)
        # — must be protean objects, not strings
        "applicant": _obj({"name": "Jane Doe", "amount": 10000}),
        "customer": _obj({"name": "Jane Doe", "amount": 10000}),
        "name": "Jane Doe",
        "amount": _num(10000),
    },
    "scenarios": {
        "scores_applicant": {
            **_ci_scenario(700),
            "request": {"applicant": "Jane Doe", "customer": "Jane Doe",
                        "amount": 10000, "risk_score": 700, "score": 700,
                        "credit_score": 700, "engine_result": 700},
        },
        "decision_at_low_score": {
            **_ci_scenario(5),
            "request": {"applicant": "Jane Doe", "customer": "Jane Doe",
                        "amount": 10000, "risk_score": 5, "score": 5,
                        "credit_score": 5, "engine_result": 5},
        },
        "decision_at_high_score": {
            **_ci_scenario(850),
            "request": {"applicant": "Jane Doe", "customer": "Jane Doe",
                        "amount": 10000, "risk_score": 850, "score": 850,
                        "credit_score": 850, "engine_result": 850},
        },
    },
}


FAMILIES = {
    "order_payment": _ORDER_PAYMENT,
    "credit_intake": _CREDIT_INTAKE,
    "insurance_claim": _INSURANCE_CLAIM,
}


def family_of(path_or_label: str):
    """Map an artifact label or diagram path to its suite, else None."""
    s = path_or_label.lower()
    for fam in FAMILIES:
        if fam in s:
            return fam
    return None


def build_spec(family: str, scenario: str, entry_mode: str = "auto") -> dict:
    """Assemble the standalone child payload for one (family, scenario)."""
    fam = FAMILIES[family]
    sc = fam["scenarios"][scenario]
    args = dict(fam["args"])
    for k, v in sc.get("args_override", {}).items():
        args[k] = {"_protean": "num", "value": v} if isinstance(v, (int, float)) else v
    return {
        "family": family,
        "scenario": scenario,
        "lexicons": LEXICONS,
        "entry_cls_like": fam["entry_cls_like"],
        "entry_cls_fallback": fam.get("entry_cls_fallback", []),
        "entry_method_like": fam["entry_method_like"],
        "entry_func_like": fam.get("entry_func_like", []),
        "args": args,
        "stubs": sc.get("stubs", []),
        "expect": sc["expect"],
        "failure_like": sc.get("failure_like", []),
        "must_call": sc.get("must_call", []),
        "must_not_call": sc.get("must_not_call", []),
        "request": sc.get("request", {}),
        # Interaction checks are meaningful only when the artifact exposes
        # the class-per-participant shape; the parent disables them for
        # handle()-entry artifacts that don't (pre-registered rule).
        "check_calls": entry_mode != "handle_only",
    }
