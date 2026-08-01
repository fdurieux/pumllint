"""Adversarial-threshold acceptance suite for the C4 detail-ladder
replication (loan_origination, adversarial parameter set).

Encodes the INTENDED behavior of the LoanCheck credit check under the
ADVERSARIAL parameter set — same system, same flow order, same error
policy as the canonical suite (tools/acceptance/c4_loan_suite.py), with
every numeric business rule moved OFF its domain-canonical value:

    approve  s >= 713   (canonical 700)
    review   641..712   (canonical 620..699)
    decline  s <  641   (canonical < 620)
    amount   500..84500 (canonical 1..100000)
    term     9..96      (canonical 6..120)

Hand-derived from the sealed R4A companion spec (c4_experiment/R4A/spec.md
after reveal). The three moved probes sit in the DISAGREEMENT ZONES
between the canonical rule pair and the adversarial rule pair, so an
implementation of the canonical rules and an implementation of the
adversarial rules give different answers at exactly these points:

  review_mid     score 705   canonical: approved | adversarial: review
  declined_band  score 630   canonical: review   | adversarial: declined
  over_cap       amt 90000   canonical: valid    | adversarial: invalid

The five remaining scenarios are byte-identical agreement anchors (both
rule sets agree), keeping the 8-scenario shape of the canonical suite.

Consumed by tools/c4_codegen_experiment.py (--adversarial), executed by
the frozen tools/acceptance/runner_child.py (unchanged). review_mid
carries the same driver-side overlay as the canonical borderline_review
(the runner has no third outcome class): passes iff the runner passed AND
the serialized outcome matches REVIEW_RE and not DECIDED_RE.

FROZEN at pre-registration (sealed-hash commitment in
docs/c4-codegen-detail-experiment.md §Adversarial-threshold replication).
Editing a scenario after any non-calibration result has been computed
invalidates the wave — re-freeze consciously.

Scenario map (R4A spec §Acceptance criteria):
  1 approved_high   score 760  -> approved; bureau+engine+store+notify called
  2 review_mid      score 705  -> review (overlay); bureau+store called
  3 declined_low    score 540  -> declined; bureau+notify called
  4 declined_band   score 630  -> declined; bureau+notify called
  5 invalid_zero    amount 0   -> rejected; bureau MUST NOT be called
  6 over_cap        amount 90000 -> rejected; bureau MUST NOT be called
  7 bureau_error    bureau raises -> error outcome; notifier MUST NOT be called
  8 storage_error   store raises  -> error outcome; notifier MUST NOT be called
"""

from .suites import LEXICONS


def _num(v):
    return {"_protean": "num", "value": v}


def _obj(fields, truthy=True):
    return {"_protean": "obj", "fields": fields, "truthy": truthy}


_BUREAU_CLS = ["bureau"]
_DB_CLS = ["applicationstore", "store", "repository", "database"]
_NOTIF_CLS = ["notification", "notifier", "notify"]
_ENGINE_CLS = ["engine", "decision", "policy", "scoring"]

_BUREAU_METH = ["score", "report", "pull", "fetch", "get", "check", "credit",
                "inquir", "request", "retrieve", "lookup"]
_DB_STORE_METH = ["store", "save", "persist", "insert", "write", "record",
                  "add", "create", "update"]
_NOTIF_METH = ["send", "notify", "dispatch", "deliver", "alert", "email",
               "sms", "message"]
_ENGINE_METH = ["decide", "decision", "evaluate", "assess", "score",
                "process", "determine", "apply", "check", "run"]


def _stub_bureau(score=760, action="value"):
    stub = {
        "name": "bureau_score", "cls_like": _BUREAU_CLS,
        "method_like": _BUREAU_METH, "action": "return", "value": _num(score),
    }
    if action == "error":
        stub.update({
            "action": "raise",
            "exc_like": ["bureau", "credit", "unavail", "timeout", "connect",
                         "service"],
            "exc_msg": "bureauUnavailableError: credit bureau timeout",
            "raise_fallback": "return_failure",
            "failure_value": _obj(
                {"status": "error", "error": "bureau_unavailable",
                 "success": False, "score": None}, truthy=False),
        })
    return stub


def _stub_db(action="value"):
    stub = {
        "name": "store_application", "cls_like": _DB_CLS,
        "method_like": _DB_STORE_METH, "action": "return",
        "value": _obj({"status": "stored", "stored": True, "success": True,
                       "application_id": "APP-1", "id": "APP-1"}),
    }
    if action == "error":
        stub.update({
            "action": "raise",
            "exc_like": ["stor", "database", "db", "persist", "unavail",
                         "write", "save"],
            "exc_msg": "storageError: application store unavailable",
            "raise_fallback": "return_failure",
            "failure_value": _obj(
                {"status": "error", "error": "storage_unavailable",
                 "success": False, "stored": False}, truthy=False),
        })
    return stub


def _stub_notify():
    return {
        "name": "send_notification", "cls_like": _NOTIF_CLS,
        "method_like": _NOTIF_METH, "action": "return",
        "value": _obj({"status": "sent", "sent": True, "success": True}),
    }


def _request(amount=25000, score=760, bureau="ok", db="stored", notify="sent"):
    return {
        "customer_id": "CUST-1", "applicant_id": "CUST-1", "customer": "CUST-1",
        "amount": amount, "loan_amount": amount, "requested_amount": amount,
        "principal": amount,
        "term_months": 60, "term": 60, "duration_months": 60,
        "income": 4200, "monthly_income": 4200, "annual_income": 50400,
        "bureau_score": score, "credit_score": score, "score": score,
        "bureau_result": bureau, "bureau_status": bureau,
        "db_status": db, "db_result": db, "storage_status": db,
        "store_result": db,
        "notify_status": notify, "notification_result": notify,
    }


SUITE = {
    "entry_cls_like": ["originationapi", "applicationservice"],
    "entry_cls_fallback": ["api", "service", "origination", "application"],
    "entry_method_like": ["handle", "submit", "process", "apply", "run",
                          "execute", "checkcredit", "creditcheck",
                          "originate"],
    "entry_func_like": ["handle", "process", "main", "submit", "run"],
    "args": {
        "customer_id": "CUST-1", "amount": _num(25000),
        "term_months": _num(60),
        "application": _obj({
            "customer_id": "CUST-1", "amount": _num(25000),
            "term_months": _num(60), "id": "APP-1",
        }),
    },
    "lexicons": LEXICONS,
    "scenarios": {
        "approved_high": {
            "stubs": [_stub_bureau(760), _stub_db(), _stub_notify()],
            "expect": "success",
            "must_call": [
                {"cls_like": _BUREAU_CLS, "method_like": _BUREAU_METH},
                {"cls_like": _ENGINE_CLS, "method_like": _ENGINE_METH},
                {"cls_like": _DB_CLS, "method_like": _DB_STORE_METH},
                {"cls_like": _NOTIF_CLS, "method_like": _NOTIF_METH},
            ],
            "request": _request(score=760),
        },
        "review_mid": {
            "stubs": [_stub_bureau(705), _stub_db(), _stub_notify()],
            "expect": "any",
            "must_call": [
                {"cls_like": _BUREAU_CLS, "method_like": _BUREAU_METH},
                {"cls_like": _DB_CLS, "method_like": _DB_STORE_METH},
            ],
            "request": _request(score=705),
        },
        "declined_low": {
            "stubs": [_stub_bureau(540), _stub_db(), _stub_notify()],
            "expect": "failure",
            "failure_like": ["declin", "reject", "denied", "low"],
            "must_call": [
                {"cls_like": _BUREAU_CLS, "method_like": _BUREAU_METH},
                {"cls_like": _NOTIF_CLS, "method_like": _NOTIF_METH},
            ],
            "request": _request(score=540),
        },
        "declined_band": {
            "stubs": [_stub_bureau(630), _stub_db(), _stub_notify()],
            "expect": "failure",
            "failure_like": ["declin", "reject", "denied", "low"],
            "must_call": [
                {"cls_like": _BUREAU_CLS, "method_like": _BUREAU_METH},
                {"cls_like": _NOTIF_CLS, "method_like": _NOTIF_METH},
            ],
            "request": _request(score=630),
        },
        "invalid_zero": {
            "stubs": [_stub_bureau(760), _stub_db(), _stub_notify()],
            "expect": "failure",
            "failure_like": ["invalid", "reject", "amount"],
            "must_not_call": [
                {"cls_like": _BUREAU_CLS, "method_like": _BUREAU_METH},
            ],
            "request": _request(amount=0),
        },
        "over_cap": {
            "stubs": [_stub_bureau(760), _stub_db(), _stub_notify()],
            "expect": "failure",
            "failure_like": ["invalid", "reject", "exceed", "cap", "limit",
                             "maximum", "too large", "above"],
            "must_not_call": [
                {"cls_like": _BUREAU_CLS, "method_like": _BUREAU_METH},
            ],
            "request": _request(amount=90000),
        },
        "bureau_error": {
            "stubs": [_stub_bureau(action="error"), _stub_db(),
                      _stub_notify()],
            "expect": "failure",
            "failure_like": ["bureau", "unavail", "credit", "timeout",
                             "pending", "score"],
            "must_not_call": [
                {"cls_like": _NOTIF_CLS, "method_like": _NOTIF_METH},
            ],
            "request": _request(bureau="error"),
        },
        "storage_error": {
            "stubs": [_stub_bureau(760), _stub_db(action="error"),
                      _stub_notify()],
            "expect": "failure",
            "failure_like": ["stor", "persist", "database", "unavail",
                             "save"],
            "must_not_call": [
                {"cls_like": _NOTIF_CLS, "method_like": _NOTIF_METH},
            ],
            "request": _request(db="error"),
        },
    },
}

# Driver-side overlay (pre-registered): review_mid passes iff the runner
# passed AND the serialized outcome matches REVIEW_RE and not DECIDED_RE
# (the runner has no third outcome class; same mechanism, same regexes as
# the canonical suite's borderline_review).
REVIEW_OVERLAY_SCENARIOS = ("review_mid",)
REVIEW_RE = r"review|manual|refer"
DECIDED_RE = r"approv|declin"
