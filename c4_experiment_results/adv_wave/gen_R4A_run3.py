"""
LoanCheck - Personal Loan Origination System (credit-check scope).

Self-contained implementation generated from the C4 model:
  - containers.puml         (container view)
  - components_api.puml     (Origination API components)
  - components_engine.puml  (Decision Engine components)
  - dynamics.puml           (approved / declined / review / invalid /
                             bureau-unavailable / storage-failure paths)
  - spec.md                 (companion specification: authoritative semantics)

Structure (one class per C4 element):

    Applicant                 Person
    OriginationApi            Container
    ApplicationService        Component of OriginationApi
    ApplicationValidator      Component of OriginationApi
    DecisionEngine            Container
    ScoringPolicy             Component of DecisionEngine
    BureauGateway             Component of DecisionEngine
    ApplicationStore          ContainerDb
    CreditBureau              System_Ext
    NotificationService       System_Ext

Calls follow declared Rel edges only.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Decision / status constants (spec.md - Glossary, Decision policy, API contract)
# ---------------------------------------------------------------------------

DECISION_APPROVED = "approved"
DECISION_DECLINED = "declined"
DECISION_REVIEW = "review"

STATUS_PENDING = "pending"

STATUS_REJECTED_INVALID = "rejected: invalid_application"
STATUS_ERROR_BUREAU = "error: bureau_unavailable"
STATUS_ERROR_STORAGE = "error: storage_unavailable"

# Decision policy thresholds, inclusive exactly as written in spec.md.
APPROVE_THRESHOLD = 713   # s >= 713            -> approved
REVIEW_THRESHOLD = 641    # 641 <= s <= 712     -> review
                          # s < 641             -> declined

# Validation limits (spec.md - Validation rules).
MIN_AMOUNT = 500
MAX_AMOUNT = 84500
MIN_TERM_MONTHS = 9
MAX_TERM_MONTHS = 96


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


class LoanCheckError(Exception):
    """Base class for LoanCheck failures."""

    status = "error: unknown"


class InvalidApplicationError(LoanCheckError):
    """The submitted application failed validation. Nothing downstream runs."""

    status = STATUS_REJECTED_INVALID

    def __init__(self, reason: str = "invalid_application") -> None:
        super().__init__(reason)
        self.reason = reason


class StorageUnavailableError(LoanCheckError):
    """The Application Store could not be reached / the write failed."""

    status = STATUS_ERROR_STORAGE


class BureauUnavailableError(LoanCheckError):
    """The Credit Bureau could not be reached or returned an error."""

    status = STATUS_ERROR_BUREAU


class NotificationError(LoanCheckError):
    """The Notification Service failed to accept a decision notification."""

    status = "error: notification_unavailable"


# ---------------------------------------------------------------------------
# External systems (System_Ext) - outside the system boundary.
# Simple classes returning plausible values, driven by the scenario input.
# ---------------------------------------------------------------------------


class CreditBureau:
    """System_Ext: external credit reference agency.

    Provides consumer credit reports and scores over XML/HTTPS.
    Only the Decision Engine's Bureau Gateway talks to it.
    """

    def __init__(self, score: Optional[int] = None, status: str = "ok") -> None:
        self._score = score
        self._status = (status or "ok").lower()

    def pull_credit_report(self, customer_id: str) -> Dict[str, Any]:
        """Pull the credit report and score for a customer.

        Raises BureauUnavailableError when the bureau is down or errors.
        """
        if self._status in ("unavailable", "down", "error", "timeout", "failed"):
            raise BureauUnavailableError(
                "credit bureau unavailable for customer %s" % customer_id
            )
        score = self._score if self._score is not None else 700
        return {
            "customer_id": customer_id,
            "score": int(score),
            "report_id": "CB-%s" % uuid.uuid4().hex[:10],
            "bureau_status": "ok",
        }


class NotificationService:
    """System_Ext: external messaging provider (e-mail and SMS)."""

    def __init__(self, status: str = "sent") -> None:
        self._status = (status or "sent").lower()

    def send_notification(
        self, customer_id: str, application_id: str, decision: str
    ) -> Dict[str, Any]:
        """Deliver a decision notification to the applicant."""
        if self._status in ("error", "unavailable", "down", "failed"):
            raise NotificationError(
                "notification service unavailable for application %s" % application_id
            )
        return {
            "delivered": True,
            "channel": "email",
            "message_id": "NS-%s" % uuid.uuid4().hex[:10],
            "customer_id": customer_id,
            "application_id": application_id,
            "decision": decision,
        }


# ---------------------------------------------------------------------------
# ContainerDb: Application Store (PostgreSQL 16)
# ---------------------------------------------------------------------------


class ApplicationStore:
    """ContainerDb: stores loan applications and their decision status."""

    def __init__(self, status: str = "available") -> None:
        self._status = (status or "available").lower()
        self._records: Dict[str, Dict[str, Any]] = {}

    # -- internal ----------------------------------------------------------

    def _guard_available(self) -> None:
        if self._status in ("unavailable", "down", "error", "failed", "offline"):
            raise StorageUnavailableError("application store unavailable")

    # -- API used by the Origination API -----------------------------------

    def store_application(self, application: Dict[str, Any]) -> str:
        """Insert the application with status 'pending'. Returns its id."""
        self._guard_available()
        application_id = application.get("application_id") or "APP-%s" % (
            uuid.uuid4().hex[:12]
        )
        self._records[application_id] = {
            "application_id": application_id,
            "customer_id": application.get("customer_id"),
            "amount": application.get("amount"),
            "term_months": application.get("term_months"),
            "status": STATUS_PENDING,
        }
        return application_id

    def update_application_status(self, application_id: str, status: str) -> Dict[str, Any]:
        """Update a stored application to its decision status."""
        self._guard_available()
        record = self._records.get(application_id)
        if record is None:
            raise StorageUnavailableError(
                "application %s not found in store" % application_id
            )
        record["status"] = status
        return dict(record)

    def get_application(self, application_id: str) -> Optional[Dict[str, Any]]:
        record = self._records.get(application_id)
        return dict(record) if record is not None else None


# ---------------------------------------------------------------------------
# Components of the Decision Engine
# ---------------------------------------------------------------------------


class BureauGateway:
    """Component: encapsulates the credit bureau integration and failure modes.

    Rel: bureau_gateway -> credit_bureau ("Pulls credit report and score from").
    """

    def __init__(self, credit_bureau: CreditBureau) -> None:
        self.credit_bureau = credit_bureau

    def fetch_credit_score(self, customer_id: str) -> int:
        """Return the applicant's credit score.

        Translates any bureau failure into BureauUnavailableError.
        """
        try:
            report = self.credit_bureau.pull_credit_report(customer_id)
        except BureauUnavailableError:
            raise
        except Exception as exc:  # any integration failure is a bureau failure
            raise BureauUnavailableError("credit bureau call failed: %s" % exc)

        score = report.get("score")
        if score is None:
            raise BureauUnavailableError("credit bureau returned no score")
        try:
            return int(score)
        except (TypeError, ValueError):
            raise BureauUnavailableError("credit bureau returned a malformed score")


class ScoringPolicy:
    """Component: maps the applicant's credit score to a credit decision.

    Rel: scoring_policy -> bureau_gateway ("Obtains the applicant's credit
    score via", in-process call).
    """

    def __init__(self, bureau_gateway: BureauGateway) -> None:
        self.bureau_gateway = bureau_gateway

    @staticmethod
    def decide_from_score(score: int) -> str:
        """Apply the decision table from spec.md (inclusive thresholds)."""
        if score >= APPROVE_THRESHOLD:
            return DECISION_APPROVED
        if score >= REVIEW_THRESHOLD:
            return DECISION_REVIEW
        return DECISION_DECLINED

    def evaluate(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """Obtain the score and turn it into a decision."""
        score = self.bureau_gateway.fetch_credit_score(application["customer_id"])
        return {"decision": self.decide_from_score(score), "score": score}


# ---------------------------------------------------------------------------
# Container: Decision Engine
# ---------------------------------------------------------------------------


class DecisionEngine:
    """Container: determines the credit decision for a validated application.

    Entry point used by the Origination API
    (Rel: origination_api -> scoring_policy / decision_engine).
    """

    def __init__(self, scoring_policy: ScoringPolicy) -> None:
        self.scoring_policy = scoring_policy

    def request_decision(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """Return {'decision': ..., 'score': ...}.

        Raises BureauUnavailableError when the bureau failed - no decision
        is made in that case.
        """
        return self.scoring_policy.evaluate(application)


# ---------------------------------------------------------------------------
# Components of the Origination API
# ---------------------------------------------------------------------------


class ApplicationValidator:
    """Component: checks completeness and product limits of an application."""

    @staticmethod
    def _is_number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def validate(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """Return the normalised application or raise InvalidApplicationError."""
        if not isinstance(application, dict):
            raise InvalidApplicationError("invalid_application")

        customer_id = application.get("customer_id")
        if not isinstance(customer_id, str) or customer_id.strip() == "":
            raise InvalidApplicationError("invalid_application")

        amount = application.get("amount")
        if not self._is_number(amount):
            raise InvalidApplicationError("invalid_application")
        if not (MIN_AMOUNT <= amount <= MAX_AMOUNT):
            raise InvalidApplicationError("invalid_application")

        term_months = application.get("term_months")
        if not self._is_number(term_months):
            raise InvalidApplicationError("invalid_application")
        if not (MIN_TERM_MONTHS <= term_months <= MAX_TERM_MONTHS):
            raise InvalidApplicationError("invalid_application")

        return {
            "customer_id": customer_id,
            "amount": amount,
            "term_months": term_months,
        }


class ApplicationService:
    """Component: orchestrates validation, storage, decision and notification.

    Rel: application_service -> application_validator (in-process)
    Rel: application_service -> application_store     (SQL/TCP)
    Rel: application_service -> decision_engine       (JSON/HTTPS)
    Rel: application_service -> notification_service  (REST/HTTPS)
    """

    def __init__(
        self,
        application_validator: ApplicationValidator,
        application_store: ApplicationStore,
        decision_engine: DecisionEngine,
        notification_service: NotificationService,
    ) -> None:
        self.application_validator = application_validator
        self.application_store = application_store
        self.decision_engine = decision_engine
        self.notification_service = notification_service

    def submit_application(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """Run the credit-check flow in the order fixed by spec.md."""
        # Step 1 - validate. Invalid: stop before any store or bureau call.
        try:
            validated = self.application_validator.validate(application)
        except InvalidApplicationError:
            return {"status": STATUS_REJECTED_INVALID}

        # Step 2 - store as pending.
        try:
            application_id = self.application_store.store_application(validated)
        except StorageUnavailableError:
            # No credit report pulled, no notification sent.
            return {"status": STATUS_ERROR_STORAGE}

        # Step 3 - request the decision (engine pulls the score from the bureau).
        try:
            outcome = self.decision_engine.request_decision(validated)
        except BureauUnavailableError:
            # Application stays pending; no notification is sent.
            return {
                "status": STATUS_ERROR_BUREAU,
                "application_id": application_id,
            }

        decision = outcome["decision"]
        score = outcome.get("score")

        # Step 4 - update the stored application to the decision.
        try:
            self.application_store.update_application_status(application_id, decision)
        except StorageUnavailableError:
            return {
                "status": STATUS_ERROR_STORAGE,
                "application_id": application_id,
            }

        # Step 5 - notify the applicant of the decision (all three decisions).
        notified = False
        try:
            self.notification_service.send_notification(
                validated["customer_id"], application_id, decision
            )
            notified = True
        except NotificationError:
            # The decision stands; delivery failure is not a decision failure.
            notified = False

        # Step 6 - return the response.
        return {
            "status": decision,
            "application_id": application_id,
            "decision": decision,
            "score": score,
            "notification_sent": notified,
        }


# ---------------------------------------------------------------------------
# Container: Origination API
# ---------------------------------------------------------------------------


class OriginationApi:
    """Container: receives applications and orchestrates the credit decision."""

    def __init__(self, application_service: ApplicationService) -> None:
        self.application_service = application_service

    def submit_application(self, application: Dict[str, Any]) -> Dict[str, Any]:
        return self.application_service.submit_application(application)


# ---------------------------------------------------------------------------
# Person: Loan Applicant
# ---------------------------------------------------------------------------


class Applicant:
    """Person: a retail customer applying for a personal loan.

    Rel: applicant -> origination_api ("Submits loan application to").
    """

    def __init__(self, origination_api: OriginationApi) -> None:
        self.origination_api = origination_api

    def submit_loan_application(self, application: Dict[str, Any]) -> Dict[str, Any]:
        return self.origination_api.submit_application(application)


# ---------------------------------------------------------------------------
# Scenario wiring helpers
# ---------------------------------------------------------------------------


_TRUE_WORDS = {"true", "yes", "y", "1", "found", "exists", "present", "available", "ok"}
_FALSE_WORDS = {"false", "no", "n", "0", "missing", "absent", "none", "not_found"}

_BUREAU_FAILURE_WORDS = {
    "error",
    "unavailable",
    "down",
    "timeout",
    "failed",
    "failure",
    "offline",
    "missing",
    "not_found",
}

_STORE_FAILURE_WORDS = {
    "error",
    "unavailable",
    "down",
    "failed",
    "failure",
    "offline",
    "missing",
    "not_found",
}

_NOTIFICATION_FAILURE_WORDS = {
    "error",
    "unavailable",
    "down",
    "failed",
    "failure",
    "offline",
    "not_sent",
}


def _flag(request: Dict[str, Any], *keys: str, default: bool = True) -> bool:
    """Read an existence-style flag, tolerating bools, ints and words."""
    for key in keys:
        if key in request and request[key] is not None:
            value = request[key]
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            text = str(value).strip().lower()
            if text in _TRUE_WORDS:
                return True
            if text in _FALSE_WORDS:
                return False
            return True
    return default


def _word(request: Dict[str, Any], *keys: str) -> Optional[str]:
    """Read a '<system>_result' / '<system>_status' style word."""
    for key in keys:
        if key in request and request[key] is not None:
            return str(request[key]).strip().lower()
    return None


def _as_int(value: Any) -> Optional[int]:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _resolve_score(request: Dict[str, Any]) -> Optional[int]:
    """Find the credit score the bureau should return for this scenario."""
    for key in (
        "credit_score",
        "score",
        "credit_bureau_score",
        "bureau_score",
        "credit_bureau_result",
        "credit_bureau_status",
        "bureau_result",
        "bureau_status",
    ):
        if key in request and request[key] is not None:
            score = _as_int(request[key])
            if score is not None:
                return score
    return None


def _resolve_bureau_status(request: Dict[str, Any]) -> str:
    """Decide whether the Credit Bureau answers or fails for this scenario."""
    if not _flag(
        request,
        "credit_bureau_exists",
        "credit_bureau_found",
        "credit_bureau_available",
        "bureau_exists",
        "bureau_found",
        "bureau_available",
        default=True,
    ):
        return "unavailable"

    word = _word(
        request,
        "credit_bureau_result",
        "credit_bureau_status",
        "bureau_result",
        "bureau_status",
    )
    if word is None:
        return "ok"
    if _as_int(word) is not None:
        return "ok"  # a number is a score, not a failure
    if word in _BUREAU_FAILURE_WORDS:
        return "unavailable"
    return "ok"


def _resolve_store_status(request: Dict[str, Any]) -> str:
    """Decide whether the Application Store accepts writes for this scenario."""
    if not _flag(
        request,
        "application_store_exists",
        "application_store_found",
        "application_store_available",
        "store_exists",
        "store_found",
        "store_available",
        default=True,
    ):
        return "unavailable"

    word = _word(
        request,
        "application_store_result",
        "application_store_status",
        "store_result",
        "store_status",
        "storage_result",
        "storage_status",
    )
    if word is None:
        return "available"
    if word in _STORE_FAILURE_WORDS:
        return "unavailable"
    return "available"


def _resolve_notification_status(request: Dict[str, Any]) -> str:
    """Decide whether the Notification Service delivers for this scenario."""
    if not _flag(
        request,
        "notification_service_exists",
        "notification_service_found",
        "notification_service_available",
        default=True,
    ):
        return "error"

    word = _word(
        request,
        "notification_service_result",
        "notification_service_status",
        "notification_result",
        "notification_status",
    )
    if word is None:
        return "sent"
    if word in _NOTIFICATION_FAILURE_WORDS:
        return "error"
    return "sent"


def _score_for_decision_word(word: Optional[str]) -> Optional[int]:
    """Map a decision word given as a scenario input onto a plausible score."""
    if word is None:
        return None
    if word in ("approved", "approve", "accept", "accepted"):
        return 760
    if word in ("review", "refer", "manual_review", "borderline", "referred"):
        return 680
    if word in ("declined", "decline", "reject", "rejected", "refused"):
        return 540
    return None


def build_system(request: Optional[Dict[str, Any]] = None):
    """Wire the whole system for one scenario and return the Applicant."""
    request = request or {}

    score = _resolve_score(request)
    if score is None:
        word = _word(
            request,
            "decision_engine_result",
            "decision_engine_status",
            "decision",
            "decision_result",
            "credit_bureau_result",
            "bureau_result",
        )
        score = _score_for_decision_word(word)
    if score is None:
        score = 700  # plausible default: borderline-but-not-referred

    credit_bureau = CreditBureau(
        score=score, status=_resolve_bureau_status(request)
    )
    notification_service = NotificationService(
        status=_resolve_notification_status(request)
    )
    application_store = ApplicationStore(status=_resolve_store_status(request))

    bureau_gateway = BureauGateway(credit_bureau)
    scoring_policy = ScoringPolicy(bureau_gateway)
    decision_engine = DecisionEngine(scoring_policy)

    application_validator = ApplicationValidator()
    application_service = ApplicationService(
        application_validator=application_validator,
        application_store=application_store,
        decision_engine=decision_engine,
        notification_service=notification_service,
    )
    origination_api = OriginationApi(application_service)
    return Applicant(origination_api)


# ---------------------------------------------------------------------------
# Module-level entry point
# ---------------------------------------------------------------------------


def handle(request: dict) -> dict:
    """Run one end-to-end credit check.

    Request keys: customer_id, amount, term_months, plus scenario controls
    such as credit_score / credit_bureau_result, application_store_result,
    notification_service_result and '<entity>_exists' flags.

    Returns a dict whose 'status' is one of:
        'approved' | 'declined' | 'review'
        'rejected: invalid_application'
        'error: bureau_unavailable'
        'error: storage_unavailable'
    """
    request = request or {}

    application = {
        "customer_id": request.get("customer_id"),
        "amount": request.get("amount"),
        "term_months": request.get("term_months"),
    }

    # An explicitly absent applicant / application cannot be a valid submission.
    if not _flag(
        request,
        "applicant_exists",
        "applicant_found",
        "customer_exists",
        "customer_found",
        "application_exists",
        "application_found",
        default=True,
    ):
        return {"status": STATUS_REJECTED_INVALID}

    applicant = build_system(request)

    try:
        return applicant.submit_loan_application(application)
    except LoanCheckError as exc:
        return {"status": exc.status}
    except Exception as exc:  # defensive: never leak a raw traceback
        return {"status": "error: %s" % type(exc).__name__.lower()}


if __name__ == "__main__":
    _scenarios = [
        {"customer_id": "C1", "amount": 10000, "term_months": 24, "credit_score": 760},
        {"customer_id": "C2", "amount": 10000, "term_months": 24, "credit_score": 705},
        {"customer_id": "C3", "amount": 10000, "term_months": 24, "credit_score": 540},
        {"customer_id": "C4", "amount": 10000, "term_months": 24, "credit_score": 630},
        {"customer_id": "C5", "amount": 0, "term_months": 24, "credit_score": 760},
        {"customer_id": "C6", "amount": 90000, "term_months": 24, "credit_score": 760},
        {
            "customer_id": "C7",
            "amount": 10000,
            "term_months": 24,
            "credit_bureau_result": "error",
        },
        {
            "customer_id": "C8",
            "amount": 10000,
            "term_months": 24,
            "credit_score": 760,
            "application_store_result": "error",
        },
    ]
    for _index, _scenario in enumerate(_scenarios, start=1):
        print(_index, handle(_scenario)["status"])
