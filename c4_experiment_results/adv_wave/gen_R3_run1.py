"""LoanCheck - Personal Loan Origination System (credit-check scope).

Self-contained implementation derived from the C4 model:

  Containers
    - OriginationApi      (Container)    "Origination API"
    - DecisionEngine      (Container)    "Decision Engine"
    - ApplicationStore    (ContainerDb)  "Application Store"

  Components
    - ApplicationService   / ApplicationValidator  (of Origination API)
    - ScoringPolicy        / BureauGateway         (of Decision Engine)

  External systems
    - CreditBureau        (System_Ext)
    - NotificationService (System_Ext)

  Person
    - Applicant

Calls follow the declared Rel edges only.
"""

from __future__ import annotations

import random
import uuid
from typing import Any, Dict, Optional

__all__ = [
    "LoanCheckError",
    "ValidationError",
    "StorageError",
    "BureauUnavailableError",
    "DecisionError",
    "NotificationError",
    "Applicant",
    "ApplicationValidator",
    "ApplicationService",
    "OriginationApi",
    "ScoringPolicy",
    "BureauGateway",
    "DecisionEngine",
    "ApplicationStore",
    "CreditBureau",
    "NotificationService",
    "build_system",
    "handle",
]


# ---------------------------------------------------------------------------
# Product limits / policy thresholds
# ---------------------------------------------------------------------------

MIN_LOAN_AMOUNT = 500.0
MAX_LOAN_AMOUNT = 50000.0
MIN_TERM_MONTHS = 6
MAX_TERM_MONTHS = 84
MIN_APPLICANT_AGE = 18
MAX_APPLICANT_AGE = 75

APPROVE_SCORE = 700
REFER_SCORE = 600

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_DECLINED = "declined"
STATUS_UNDER_REVIEW = "under_manual_review"

DECISION_APPROVE = "approve"
DECISION_DECLINE = "decline"
DECISION_REFER = "refer"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class LoanCheckError(Exception):
    """Base class for all failures raised inside the origination system."""

    reason = "loan_check_error"

    def __init__(self, message: str = "", reason: Optional[str] = None) -> None:
        super().__init__(message or self.reason)
        self.message = message or self.reason
        if reason:
            self.reason = reason


class ValidationError(LoanCheckError):
    """The submitted application is incomplete or outside product limits."""

    reason = "invalid_application"

    def __init__(self, message: str = "", errors: Optional[list] = None) -> None:
        super().__init__(message)
        self.errors = list(errors or ([message] if message else []))


class StorageError(LoanCheckError):
    """The Application Store could not be reached or refused the write."""

    reason = "storage_unavailable"


class BureauUnavailableError(LoanCheckError):
    """The Credit Bureau failed to return a report."""

    reason = "bureau_unavailable"


class DecisionError(LoanCheckError):
    """The Decision Engine could not produce a decision."""

    reason = "decision_unavailable"


class NotificationError(LoanCheckError):
    """The Notification Service refused or failed to deliver a message."""

    reason = "notification_failed"


# ---------------------------------------------------------------------------
# External systems (outside the system boundary) - simple stubs
# ---------------------------------------------------------------------------


class CreditBureau:
    """System_Ext: external credit reference agency.

    Provides consumer credit reports and scores. Its outcome is driven by
    ``credit_bureau_result`` / ``credit_bureau_status`` in the scenario input
    (a short word such as "available"/"unavailable"/"error", or a number that
    is taken as the credit score itself).
    """

    UNAVAILABLE_WORDS = {
        "unavailable",
        "down",
        "error",
        "timeout",
        "failed",
        "failure",
        "offline",
        "outage",
    }

    def __init__(self, outcome: Any = None, score: Optional[int] = None) -> None:
        self._outcome = outcome
        self._score = score

    def pull_credit_report(self, applicant_id: str, application: Optional[dict] = None) -> dict:
        """Pull a credit report and score for the applicant (XML/HTTPS)."""
        outcome = self._outcome

        if isinstance(outcome, bool):
            if not outcome:
                raise BureauUnavailableError("credit bureau did not return a report")
            outcome = None

        if isinstance(outcome, (int, float)) and not isinstance(outcome, bool):
            return self._report(applicant_id, int(outcome))

        if isinstance(outcome, str):
            token = outcome.strip().lower()
            try:
                return self._report(applicant_id, int(float(token)))
            except (TypeError, ValueError):
                pass
            if token in self.UNAVAILABLE_WORDS:
                raise BureauUnavailableError("credit bureau is unavailable")
            if token in {"approved", "approve", "excellent", "good", "high"}:
                return self._report(applicant_id, 780)
            if token in {"declined", "decline", "bad", "poor", "low"}:
                return self._report(applicant_id, 520)
            if token in {"review", "refer", "borderline", "marginal", "fair"}:
                return self._report(applicant_id, 650)
            # "ok", "available", "active", "assessed", ... -> a normal report
            return self._report(applicant_id, self._default_score())

        if self._score is not None:
            return self._report(applicant_id, int(self._score))

        return self._report(applicant_id, self._default_score())

    def _default_score(self) -> int:
        if self._score is not None:
            return int(self._score)
        return random.randint(560, 820)

    @staticmethod
    def _report(applicant_id: str, score: int) -> dict:
        score = max(300, min(850, int(score)))
        return {
            "applicant_id": applicant_id,
            "score": score,
            "bureau_reference": "BR-" + uuid.uuid4().hex[:10].upper(),
            "report_status": "complete",
        }


class NotificationService:
    """System_Ext: external messaging provider (e-mail and SMS)."""

    FAILURE_WORDS = {"error", "failed", "failure", "unavailable", "rejected", "bounced"}

    def __init__(self, outcome: Any = None) -> None:
        self._outcome = outcome

    def send(self, recipient: str, template: str, payload: Optional[dict] = None) -> dict:
        """Deliver a decision notification (REST/HTTPS)."""
        outcome = self._outcome
        if isinstance(outcome, bool) and not outcome:
            raise NotificationError("notification service rejected the message")
        if isinstance(outcome, str) and outcome.strip().lower() in self.FAILURE_WORDS:
            raise NotificationError("notification service rejected the message")
        return {
            "message_id": "MSG-" + uuid.uuid4().hex[:12].upper(),
            "recipient": recipient,
            "template": template,
            "channel": "email",
            "delivery_status": "sent",
            "payload": dict(payload or {}),
        }


# ---------------------------------------------------------------------------
# ContainerDb: Application Store
# ---------------------------------------------------------------------------


class ApplicationStore:
    """ContainerDb: PostgreSQL 16 store of loan applications and decisions."""

    FAILURE_WORDS = {
        "unavailable",
        "down",
        "error",
        "failed",
        "failure",
        "offline",
        "timeout",
    }

    def __init__(self, outcome: Any = None) -> None:
        self._outcome = outcome
        self._records: Dict[str, dict] = {}

    # -- availability -------------------------------------------------------

    def _guard_available(self) -> None:
        outcome = self._outcome
        if isinstance(outcome, bool) and not outcome:
            raise StorageError("application store is unavailable")
        if isinstance(outcome, str) and outcome.strip().lower() in self.FAILURE_WORDS:
            raise StorageError("application store is unavailable")

    # -- writes -------------------------------------------------------------

    def store_pending(self, application: dict) -> dict:
        """Insert the application with status 'pending' (SQL/TCP)."""
        self._guard_available()
        application_id = application.get("application_id") or (
            "APP-" + uuid.uuid4().hex[:10].upper()
        )
        record = {
            "application_id": application_id,
            "applicant_id": application.get("applicant_id"),
            "amount": application.get("amount"),
            "term_months": application.get("term_months"),
            "status": STATUS_PENDING,
            "decision": None,
            "score": None,
        }
        self._records[application_id] = record
        return dict(record)

    def update_status(
        self,
        application_id: str,
        status: str,
        decision: Optional[str] = None,
        score: Optional[int] = None,
    ) -> dict:
        """Update the stored application with its decision status (SQL/TCP)."""
        self._guard_available()
        record = self._records.get(application_id)
        if record is None:
            raise StorageError("application %s not found in store" % application_id)
        record["status"] = status
        if decision is not None:
            record["decision"] = decision
        if score is not None:
            record["score"] = score
        return dict(record)

    # -- reads --------------------------------------------------------------

    def get(self, application_id: str) -> Optional[dict]:
        record = self._records.get(application_id)
        return dict(record) if record else None


# ---------------------------------------------------------------------------
# Components of the Decision Engine
# ---------------------------------------------------------------------------


class BureauGateway:
    """Component: encapsulates the credit bureau integration and failure modes."""

    def __init__(self, credit_bureau: CreditBureau) -> None:
        self.credit_bureau = credit_bureau

    def fetch_score(self, applicant_id: str, application: Optional[dict] = None) -> int:
        """Pull the credit report and extract the score (Rel -> credit_bureau)."""
        try:
            report = self.credit_bureau.pull_credit_report(applicant_id, application)
        except BureauUnavailableError:
            raise
        except Exception as exc:  # any transport-level failure of the bureau
            raise BureauUnavailableError("credit bureau call failed: %s" % exc) from exc

        if not isinstance(report, dict):
            raise BureauUnavailableError("credit bureau returned no report")
        if report.get("report_status") not in (None, "complete"):
            raise BureauUnavailableError("credit bureau returned an incomplete report")

        score = report.get("score")
        if score is None:
            raise BureauUnavailableError("credit bureau returned no score")
        try:
            return int(score)
        except (TypeError, ValueError) as exc:
            raise BureauUnavailableError("credit bureau returned a malformed score") from exc


class ScoringPolicy:
    """Component: maps the applicant's credit score to a credit decision."""

    def __init__(
        self,
        bureau_gateway: BureauGateway,
        approve_threshold: int = APPROVE_SCORE,
        refer_threshold: int = REFER_SCORE,
    ) -> None:
        self.bureau_gateway = bureau_gateway
        self.approve_threshold = approve_threshold
        self.refer_threshold = refer_threshold

    def decide(self, application: dict) -> dict:
        """Obtain the score (Rel -> bureau_gateway) and apply the scoring rules."""
        applicant_id = application.get("applicant_id")
        score = self.bureau_gateway.fetch_score(applicant_id, application)

        if score >= self.approve_threshold:
            decision = DECISION_APPROVE
        elif score >= self.refer_threshold:
            decision = DECISION_REFER
        else:
            decision = DECISION_DECLINE

        return {
            "decision": decision,
            "score": score,
            "approve_threshold": self.approve_threshold,
            "refer_threshold": self.refer_threshold,
        }


class DecisionEngine:
    """Container: determines the credit decision for a validated application."""

    def __init__(self, scoring_policy: ScoringPolicy) -> None:
        self.scoring_policy = scoring_policy

    def request_decision(self, application: dict) -> dict:
        """Entry point called by the Origination API (JSON/HTTPS).

        Raises BureauUnavailableError when the bureau fails: no decision is made.
        """
        if not isinstance(application, dict):
            raise DecisionError("malformed decision request")
        if not application.get("applicant_id"):
            raise DecisionError("decision request is missing the applicant id")
        return self.scoring_policy.decide(application)


# ---------------------------------------------------------------------------
# Components of the Origination API
# ---------------------------------------------------------------------------


class ApplicationValidator:
    """Component: checks completeness and product limits of an application."""

    REQUIRED_FIELDS = ("applicant_id", "amount", "term_months")

    def validate(self, application: dict) -> dict:
        """Return the normalised application or raise ValidationError."""
        errors = []

        if not isinstance(application, dict):
            raise ValidationError("application payload must be an object")

        for field in self.REQUIRED_FIELDS:
            value = application.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append("missing field: %s" % field)

        if application.get("applicant_exists") is False or application.get(
            "applicant_found"
        ) is False:
            errors.append("unknown applicant")

        amount = None
        if application.get("amount") is not None:
            try:
                amount = float(application["amount"])
            except (TypeError, ValueError):
                errors.append("amount is not a number")
            else:
                if amount <= 0:
                    errors.append("amount must be positive")
                elif amount < MIN_LOAN_AMOUNT:
                    errors.append("amount below product minimum of %s" % MIN_LOAN_AMOUNT)
                elif amount > MAX_LOAN_AMOUNT:
                    errors.append("amount above product maximum of %s" % MAX_LOAN_AMOUNT)

        term = None
        if application.get("term_months") is not None:
            try:
                term = int(application["term_months"])
            except (TypeError, ValueError):
                errors.append("term_months is not an integer")
            else:
                if term < MIN_TERM_MONTHS or term > MAX_TERM_MONTHS:
                    errors.append(
                        "term_months outside product limits (%s-%s)"
                        % (MIN_TERM_MONTHS, MAX_TERM_MONTHS)
                    )

        age = application.get("age")
        if age is not None:
            try:
                age_value = int(age)
            except (TypeError, ValueError):
                errors.append("age is not an integer")
            else:
                if age_value < MIN_APPLICANT_AGE or age_value > MAX_APPLICANT_AGE:
                    errors.append(
                        "applicant age outside product limits (%s-%s)"
                        % (MIN_APPLICANT_AGE, MAX_APPLICANT_AGE)
                    )

        income = application.get("annual_income")
        if income is not None:
            try:
                income_value = float(income)
            except (TypeError, ValueError):
                errors.append("annual_income is not a number")
            else:
                if income_value <= 0:
                    errors.append("annual_income must be positive")

        if errors:
            raise ValidationError("; ".join(errors), errors=errors)

        normalised = dict(application)
        if amount is not None:
            normalised["amount"] = amount
        if term is not None:
            normalised["term_months"] = term
        normalised["applicant_id"] = str(application["applicant_id"])
        return normalised


class ApplicationService:
    """Component: orchestrates validation, storage, decision and notification."""

    NOTIFICATION_TEMPLATES = {
        DECISION_APPROVE: "loan_application_approved",
        DECISION_DECLINE: "loan_application_declined",
        DECISION_REFER: "loan_application_under_review",
    }

    STATUS_BY_DECISION = {
        DECISION_APPROVE: STATUS_APPROVED,
        DECISION_DECLINE: STATUS_DECLINED,
        DECISION_REFER: STATUS_UNDER_REVIEW,
    }

    RESPONSE_BY_DECISION = {
        DECISION_APPROVE: "approved",
        DECISION_DECLINE: "declined",
        DECISION_REFER: "under_review",
    }

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

    def submit_application(self, application: dict) -> dict:
        """Run the whole credit-check flow for one submitted application."""
        # 1 / 2: validate. Invalid -> rejected, no store write, no bureau pull.
        validated = self.application_validator.validate(application)

        # 2: store as pending. Store unavailable -> storage error, nothing else.
        record = self.application_store.store_pending(validated)
        application_id = record["application_id"]

        # 3-6: request the credit decision.
        try:
            decision_result = self.decision_engine.request_decision(
                {
                    "application_id": application_id,
                    "applicant_id": validated["applicant_id"],
                    "amount": validated.get("amount"),
                    "term_months": validated.get("term_months"),
                }
            )
        except BureauUnavailableError as exc:
            # Application stays pending; no decision notification is sent.
            raise BureauUnavailableError(str(exc)) from exc

        decision = decision_result["decision"]
        score = decision_result.get("score")
        status = self.STATUS_BY_DECISION.get(decision)
        if status is None:
            raise DecisionError("decision engine returned an unknown decision: %r" % decision)

        # 7: persist the decision.
        self.application_store.update_status(
            application_id, status, decision=decision, score=score
        )

        # 8: notify the applicant of the outcome.
        notification = None
        notification_error = None
        try:
            notification = self.notification_service.send(
                recipient=validated.get("email") or validated["applicant_id"],
                template=self.NOTIFICATION_TEMPLATES[decision],
                payload={
                    "application_id": application_id,
                    "decision": decision,
                    "amount": validated.get("amount"),
                },
            )
        except NotificationError as exc:
            # The decision itself stands; the delivery failure is reported.
            notification_error = str(exc)

        # 9: return the response to the applicant.
        return {
            "status": self.RESPONSE_BY_DECISION[decision],
            "application_id": application_id,
            "applicant_id": validated["applicant_id"],
            "amount": validated.get("amount"),
            "term_months": validated.get("term_months"),
            "decision": decision,
            "score": score,
            "application_status": status,
            "notified": notification is not None,
            "notification_id": (notification or {}).get("message_id"),
            "notification_error": notification_error,
        }


class OriginationApi:
    """Container: receives applications and orchestrates the credit decision."""

    def __init__(self, application_service: ApplicationService) -> None:
        self.application_service = application_service

    def submit_loan_application(self, application: dict) -> dict:
        """HTTP entry point used by the applicant (JSON/HTTPS)."""
        return self.application_service.submit_application(application)


# ---------------------------------------------------------------------------
# Person
# ---------------------------------------------------------------------------


class Applicant:
    """Person: a retail customer applying for a personal loan."""

    def __init__(self, origination_api: OriginationApi, applicant_id: str = "applicant-1") -> None:
        self.origination_api = origination_api
        self.applicant_id = applicant_id

    def submit_loan_application(self, application: dict) -> dict:
        """Submit the application to the Origination API (JSON/HTTPS)."""
        payload = dict(application or {})
        payload.setdefault("applicant_id", self.applicant_id)
        return self.origination_api.submit_loan_application(payload)


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------


def build_system(
    bureau_outcome: Any = None,
    bureau_score: Optional[int] = None,
    store_outcome: Any = None,
    notification_outcome: Any = None,
    approve_threshold: int = APPROVE_SCORE,
    refer_threshold: int = REFER_SCORE,
) -> Dict[str, Any]:
    """Instantiate every element of the C4 model and wire the declared Rels."""
    credit_bureau = CreditBureau(outcome=bureau_outcome, score=bureau_score)
    notification_service = NotificationService(outcome=notification_outcome)

    application_store = ApplicationStore(outcome=store_outcome)

    bureau_gateway = BureauGateway(credit_bureau)
    scoring_policy = ScoringPolicy(bureau_gateway, approve_threshold, refer_threshold)
    decision_engine = DecisionEngine(scoring_policy)

    application_validator = ApplicationValidator()
    application_service = ApplicationService(
        application_validator, application_store, decision_engine, notification_service
    )
    origination_api = OriginationApi(application_service)
    applicant = Applicant(origination_api)

    return {
        "applicant": applicant,
        "origination_api": origination_api,
        "application_service": application_service,
        "application_validator": application_validator,
        "application_store": application_store,
        "decision_engine": decision_engine,
        "scoring_policy": scoring_policy,
        "bureau_gateway": bureau_gateway,
        "credit_bureau": credit_bureau,
        "notification_service": notification_service,
    }


# ---------------------------------------------------------------------------
# Scenario input helpers
# ---------------------------------------------------------------------------

_MISSING = object()


def _lookup(request: dict, *keys: str) -> Any:
    for key in keys:
        if key in request and request[key] is not None:
            return request[key]
    return _MISSING


def _score_from(value: Any) -> Optional[int]:
    if isinstance(value, bool) or value is _MISSING or value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip()))
        except (TypeError, ValueError):
            return None
    return None


def _bureau_outcome(request: dict) -> Any:
    raw = _lookup(
        request,
        "credit_bureau_result",
        "credit_bureau_status",
        "bureau_result",
        "bureau_status",
        "credit_bureau",
        "bureau",
    )
    if raw is _MISSING:
        raw = None

    score = _lookup(request, "credit_score", "score", "bureau_score")
    if raw is None and score is not _MISSING:
        raw = score

    exists = _lookup(
        request,
        "credit_bureau_exists",
        "credit_bureau_found",
        "bureau_exists",
        "bureau_found",
        "credit_report_found",
        "credit_report_exists",
    )
    if exists is not _MISSING and exists is False:
        return "unavailable"

    return raw


def _store_outcome(request: dict) -> Any:
    raw = _lookup(
        request,
        "application_store_result",
        "application_store_status",
        "store_result",
        "store_status",
        "application_store",
    )
    if raw is _MISSING:
        raw = None
    exists = _lookup(
        request,
        "application_store_exists",
        "application_store_found",
        "store_exists",
        "store_found",
    )
    if exists is not _MISSING and exists is False:
        return "unavailable"
    return raw


def _notification_outcome(request: dict) -> Any:
    raw = _lookup(
        request,
        "notification_service_result",
        "notification_service_status",
        "notification_result",
        "notification_status",
        "notification_service",
    )
    if raw is _MISSING:
        return None
    return raw


def _decision_override(request: dict) -> Optional[str]:
    """Map a decision-engine outcome word onto a synthetic bureau score."""
    raw = _lookup(
        request,
        "decision_engine_result",
        "decision_engine_status",
        "decision_result",
        "decision_status",
        "decision",
    )
    if raw is _MISSING or not isinstance(raw, str):
        return None
    return raw.strip().lower()


_DECISION_WORD_SCORES = {
    "approved": 780,
    "approve": 780,
    "accepted": 780,
    "declined": 520,
    "decline": 520,
    "rejected": 520,
    "refer": 650,
    "review": 650,
    "manual_review": 650,
    "borderline": 650,
    "referred": 650,
}


# ---------------------------------------------------------------------------
# End-to-end entry point
# ---------------------------------------------------------------------------


def handle(request: dict) -> dict:
    """Run one end-to-end credit-check flow.

    Outcome statuses:
      "approved"                    - score sufficient, stored + notified
      "declined"                    - score too low, stored + notified
      "under_review"                - score borderline, stored + notified
      "rejected"                    - application invalid, nothing else happened
      "error: storage_unavailable"  - application store refused the write
      "error: bureau_unavailable"   - no decision; application stays pending
      "error: <reason>"             - any other failure
    """
    request = dict(request or {})

    bureau_outcome = _bureau_outcome(request)
    decision_word = _decision_override(request)
    if decision_word and bureau_outcome in (None, _MISSING):
        mapped = _DECISION_WORD_SCORES.get(decision_word)
        if mapped is not None:
            bureau_outcome = mapped
        elif decision_word in CreditBureau.UNAVAILABLE_WORDS:
            bureau_outcome = decision_word

    bureau_score = _score_from(_lookup(request, "credit_score", "score", "bureau_score"))

    system = build_system(
        bureau_outcome=bureau_outcome,
        bureau_score=bureau_score,
        store_outcome=_store_outcome(request),
        notification_outcome=_notification_outcome(request),
        approve_threshold=int(request.get("approve_threshold", APPROVE_SCORE)),
        refer_threshold=int(request.get("refer_threshold", REFER_SCORE)),
    )

    applicant_id = request.get("applicant_id") or request.get("customer_id") or "applicant-1"
    applicant_exists = _lookup(request, "applicant_exists", "applicant_found", "customer_exists")

    application = {
        "application_id": request.get("application_id"),
        "applicant_id": applicant_id,
        "amount": request.get("amount", request.get("loan_amount")),
        "term_months": request.get("term_months", request.get("term")),
        "email": request.get("email"),
        "age": request.get("age"),
        "annual_income": request.get("annual_income"),
    }
    if applicant_exists is not _MISSING:
        application["applicant_exists"] = bool(applicant_exists)
    application = {k: v for k, v in application.items() if v is not None}

    person: Applicant = system["applicant"]
    person.applicant_id = applicant_id

    try:
        result = person.submit_loan_application(application)
    except ValidationError as exc:
        return {
            "status": "rejected",
            "reason": exc.reason,
            "errors": exc.errors,
            "message": exc.message,
            "applicant_id": applicant_id,
            "application_id": request.get("application_id"),
            "stored": False,
            "credit_report_pulled": False,
            "notified": False,
        }
    except StorageError as exc:
        return {
            "status": "error: %s" % exc.reason,
            "reason": exc.reason,
            "message": exc.message,
            "applicant_id": applicant_id,
            "application_id": request.get("application_id"),
            "stored": False,
            "credit_report_pulled": False,
            "notified": False,
        }
    except BureauUnavailableError as exc:
        return {
            "status": "error: %s" % exc.reason,
            "reason": exc.reason,
            "message": exc.message,
            "applicant_id": applicant_id,
            "application_id": request.get("application_id"),
            "stored": True,
            "application_status": STATUS_PENDING,
            "decision": None,
            "credit_report_pulled": False,
            "notified": False,
        }
    except LoanCheckError as exc:
        return {
            "status": "error: %s" % exc.reason,
            "reason": exc.reason,
            "message": exc.message,
            "applicant_id": applicant_id,
            "application_id": request.get("application_id"),
            "notified": False,
        }

    result["stored"] = True
    result["credit_report_pulled"] = True
    return result
