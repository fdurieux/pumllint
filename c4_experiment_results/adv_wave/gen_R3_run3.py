"""LoanCheck - Personal Loan Origination System (credit-check scope).

Self-contained implementation derived from the C4 model:

  * containers.puml         - container-level structure
  * components_api.puml     - Origination API internals
  * components_engine.puml  - Decision Engine internals
  * dynamics.puml           - approved / declined / review / invalid /
                              bureau-unavailable / storage-failure flows

Class-per-element mapping
-------------------------
Person            applicant             -> Applicant
Container         origination_api       -> OriginationApi
Component           application_service -> ApplicationService
Component           application_validator -> ApplicationValidator
Container         decision_engine       -> DecisionEngine
Component           scoring_policy      -> ScoringPolicy
Component           bureau_gateway      -> BureauGateway
ContainerDb       application_store     -> ApplicationStore
System_Ext        credit_bureau         -> CreditBureau
System_Ext        notification_service  -> NotificationService

Calls only follow declared Rel edges.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Product limits and scoring bands (the "rules library" of the Decision Engine)
# ---------------------------------------------------------------------------

MIN_LOAN_AMOUNT = 1_000.0
MAX_LOAN_AMOUNT = 50_000.0
MIN_TERM_MONTHS = 6
MAX_TERM_MONTHS = 84

APPROVE_SCORE_THRESHOLD = 700      # score >= 700            -> approve
REVIEW_SCORE_THRESHOLD = 600       # 600 <= score < 700      -> manual review
                                   # score < 600             -> decline

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_DECLINED = "declined"
STATUS_MANUAL_REVIEW = "manual_review"

DECISION_APPROVE = "approve"
DECISION_DECLINE = "decline"
DECISION_REFER = "refer"


# ---------------------------------------------------------------------------
# Errors - failure paths from the dynamic diagrams
# ---------------------------------------------------------------------------


class LoanCheckError(Exception):
    """Base class for all LoanCheck failures."""

    reason = "error"


class ValidationError(LoanCheckError):
    """The submitted application is incomplete or outside product limits."""

    reason = "invalid_application"

    def __init__(self, message: str, field: Optional[str] = None) -> None:
        super().__init__(message)
        self.field = field


class StorageError(LoanCheckError):
    """The Application Store is unavailable or refused the write."""

    reason = "storage_unavailable"


class ApplicationNotFoundError(LoanCheckError):
    """No such application record in the Application Store."""

    reason = "application_not_found"


class BureauUnavailableError(LoanCheckError):
    """The Credit Bureau failed to return a report; no decision can be made."""

    reason = "bureau_unavailable"


class DecisionError(LoanCheckError):
    """The Decision Engine could not produce a decision."""

    reason = "decision_failed"


class NotificationError(LoanCheckError):
    """The Notification Service failed to deliver the decision notification."""

    reason = "notification_failed"


# ---------------------------------------------------------------------------
# System_Ext: Credit Bureau
# ---------------------------------------------------------------------------


class CreditBureau:
    """External credit reference agency providing credit reports and scores.

    Outside the system boundary: simple stand-in returning plausible values.
    """

    DEFAULT_SCORE = 720

    def __init__(self, outcome: Any = "ok", score: Optional[int] = None) -> None:
        # `outcome` may be a status word ("ok", "available", "unavailable",
        # "error", "timeout") or directly a numeric score.
        self.outcome = outcome
        self.score = score
        self.calls: list = []

    def pull_credit_report(self, applicant_id: str, application_id: str) -> Dict[str, Any]:
        """XML/HTTPS - return a credit report for the applicant."""
        self.calls.append((applicant_id, application_id))

        outcome = self.outcome
        score = self.score

        if isinstance(outcome, bool):
            outcome = "ok" if outcome else "unavailable"

        if isinstance(outcome, (int, float)) and not isinstance(outcome, bool):
            score = int(outcome)
            outcome = "ok"

        word = str(outcome).strip().lower() if outcome is not None else "ok"

        if word in ("unavailable", "down", "error", "timeout", "failure",
                    "failed", "offline", "unreachable", "5xx"):
            raise BureauUnavailableError(
                "Credit Bureau did not return a report (%s)" % word
            )

        if score is None:
            if word in ("approved", "approve", "good", "excellent"):
                score = 780
            elif word in ("declined", "decline", "bad", "poor"):
                score = 520
            elif word in ("review", "refer", "borderline", "marginal"):
                score = 640
            else:
                score = self.DEFAULT_SCORE

        score = int(score)
        return {
            "applicant_id": applicant_id,
            "application_id": application_id,
            "score": score,
            "band": self._band(score),
            "report_id": "cb-" + uuid.uuid4().hex[:12],
            "bureau": "credit_bureau",
        }

    @staticmethod
    def _band(score: int) -> str:
        if score >= 740:
            return "excellent"
        if score >= 670:
            return "good"
        if score >= 580:
            return "fair"
        return "poor"


# ---------------------------------------------------------------------------
# System_Ext: Notification Service
# ---------------------------------------------------------------------------


class NotificationService:
    """External messaging provider delivering e-mail and SMS notifications."""

    def __init__(self, outcome: Any = "sent") -> None:
        self.outcome = outcome
        self.sent: list = []

    def send(self, recipient: str, template: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """REST/HTTPS - deliver one decision notification."""
        word = str(self.outcome).strip().lower() if self.outcome is not None else "sent"

        if word in ("error", "failed", "failure", "unavailable", "down",
                    "timeout", "rejected"):
            raise NotificationError("Notification Service delivery failed (%s)" % word)

        message = {
            "notification_id": "ntf-" + uuid.uuid4().hex[:12],
            "recipient": recipient,
            "template": template,
            "channel": "email",
            "payload": dict(payload),
            "status": "sent",
        }
        self.sent.append(message)
        return message


# ---------------------------------------------------------------------------
# ContainerDb: Application Store
# ---------------------------------------------------------------------------


class ApplicationStore:
    """PostgreSQL 16 - stores loan applications and their decision status."""

    def __init__(self, outcome: Any = "stored") -> None:
        self.outcome = outcome
        self.records: Dict[str, Dict[str, Any]] = {}

    # -- internals ---------------------------------------------------------

    def _check_available(self) -> None:
        word = str(self.outcome).strip().lower() if self.outcome is not None else "stored"
        if word in ("error", "unavailable", "down", "failed", "failure",
                    "timeout", "offline", "unreachable"):
            raise StorageError("Application Store unavailable (%s)" % word)

    # -- SQL/TCP operations ------------------------------------------------

    def store_pending(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """Insert the application with status `pending`."""
        self._check_available()
        application_id = application.get("application_id") or (
            "app-" + uuid.uuid4().hex[:12]
        )
        record = dict(application)
        record["application_id"] = application_id
        record["status"] = STATUS_PENDING
        record["decision"] = None
        record["score"] = None
        self.records[application_id] = record
        return dict(record)

    def update_status(
        self,
        application_id: str,
        status: str,
        decision: Optional[str] = None,
        score: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Update the stored application's decision status."""
        self._check_available()
        record = self.records.get(application_id)
        if record is None:
            raise ApplicationNotFoundError(
                "No application record %r in the Application Store" % application_id
            )
        record["status"] = status
        if decision is not None:
            record["decision"] = decision
        if score is not None:
            record["score"] = score
        return dict(record)

    def get(self, application_id: str) -> Dict[str, Any]:
        self._check_available()
        record = self.records.get(application_id)
        if record is None:
            raise ApplicationNotFoundError(
                "No application record %r in the Application Store" % application_id
            )
        return dict(record)


# ---------------------------------------------------------------------------
# Component of Decision Engine: Bureau Gateway
# ---------------------------------------------------------------------------


class BureauGateway:
    """Encapsulates the credit bureau integration and its failure modes.

    Rel: bureau_gateway -> credit_bureau ("Pulls credit report and score from").
    """

    def __init__(self, credit_bureau: CreditBureau) -> None:
        self.credit_bureau = credit_bureau

    def fetch_score(self, applicant_id: str, application_id: str) -> Dict[str, Any]:
        """Pull the report from the bureau and normalise it to a score."""
        try:
            report = self.credit_bureau.pull_credit_report(applicant_id, application_id)
        except BureauUnavailableError:
            raise
        except Exception as exc:  # any integration fault is a bureau failure
            raise BureauUnavailableError(
                "Credit Bureau integration failed: %s" % exc
            ) from exc

        if not report or report.get("score") is None:
            raise BureauUnavailableError("Credit Bureau returned no score")

        try:
            score = int(report["score"])
        except (TypeError, ValueError) as exc:
            raise BureauUnavailableError(
                "Credit Bureau returned a non-numeric score"
            ) from exc

        return {
            "score": score,
            "band": report.get("band"),
            "report_id": report.get("report_id"),
        }


# ---------------------------------------------------------------------------
# Component of Decision Engine: Scoring Policy
# ---------------------------------------------------------------------------


class ScoringPolicy:
    """Maps the applicant's credit score to a credit decision.

    Rel: scoring_policy -> bureau_gateway ("Obtains the applicant's credit
    score via").
    """

    def __init__(self, bureau_gateway: BureauGateway) -> None:
        self.bureau_gateway = bureau_gateway

    def decide(self, application: Dict[str, Any]) -> Dict[str, Any]:
        applicant_id = application.get("applicant_id")
        application_id = application.get("application_id")

        credit = self.bureau_gateway.fetch_score(applicant_id, application_id)
        score = credit["score"]

        if score >= APPROVE_SCORE_THRESHOLD:
            decision = DECISION_APPROVE
            reason = "score sufficient"
        elif score >= REVIEW_SCORE_THRESHOLD:
            decision = DECISION_REFER
            reason = "score borderline"
        else:
            decision = DECISION_DECLINE
            reason = "score too low"

        return {
            "application_id": application_id,
            "decision": decision,
            "score": score,
            "band": credit.get("band"),
            "report_id": credit.get("report_id"),
            "reason": reason,
        }


# ---------------------------------------------------------------------------
# Container: Decision Engine
# ---------------------------------------------------------------------------


class DecisionEngine:
    """Determines the credit decision for a validated application.

    Container-level Rel: decision_engine -> credit_bureau, realised inside the
    container by scoring_policy -> bureau_gateway -> credit_bureau.
    """

    def __init__(self, credit_bureau: CreditBureau) -> None:
        self.bureau_gateway = BureauGateway(credit_bureau)
        self.scoring_policy = ScoringPolicy(self.bureau_gateway)

    def request_decision(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """JSON/HTTPS entry point used by the Origination API."""
        return self.scoring_policy.decide(application)


# ---------------------------------------------------------------------------
# Component of Origination API: Application Validator
# ---------------------------------------------------------------------------


class ApplicationValidator:
    """Checks that a submitted application is complete and within limits."""

    REQUIRED_FIELDS = ("applicant_id", "amount", "term_months")

    def validate(self, application: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(application, dict):
            raise ValidationError("Application payload must be an object")

        for field in self.REQUIRED_FIELDS:
            value = application.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValidationError("Missing required field %r" % field, field=field)

        try:
            amount = float(application["amount"])
        except (TypeError, ValueError):
            raise ValidationError("Amount must be numeric", field="amount")

        if amount <= 0:
            raise ValidationError("Amount must be positive", field="amount")
        if amount < MIN_LOAN_AMOUNT:
            raise ValidationError(
                "Amount %.2f below product minimum %.2f" % (amount, MIN_LOAN_AMOUNT),
                field="amount",
            )
        if amount > MAX_LOAN_AMOUNT:
            raise ValidationError(
                "Amount %.2f above product maximum %.2f" % (amount, MAX_LOAN_AMOUNT),
                field="amount",
            )

        try:
            term_months = int(application["term_months"])
        except (TypeError, ValueError):
            raise ValidationError("Term must be an integer number of months",
                                  field="term_months")

        if not (MIN_TERM_MONTHS <= term_months <= MAX_TERM_MONTHS):
            raise ValidationError(
                "Term %d months outside product range %d-%d"
                % (term_months, MIN_TERM_MONTHS, MAX_TERM_MONTHS),
                field="term_months",
            )

        validated = dict(application)
        validated["amount"] = amount
        validated["term_months"] = term_months
        validated["applicant_id"] = str(application["applicant_id"])
        return validated


# ---------------------------------------------------------------------------
# Component of Origination API: Application Service
# ---------------------------------------------------------------------------


class ApplicationService:
    """Orchestrates the credit-check flow.

    Rels: application_service -> application_validator, -> application_store,
    -> decision_engine, -> notification_service.
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

    # -- flow --------------------------------------------------------------

    def submit_application(self, application: Dict[str, Any]) -> Dict[str, Any]:
        # 1/2: validate. Invalid -> rejected, nothing stored, no report pulled.
        validated = self.application_validator.validate(application)

        # 2: store as pending. Storage failure aborts before any bureau call.
        record = self.application_store.store_pending(validated)
        application_id = record["application_id"]
        validated["application_id"] = application_id

        # 3-6: request the credit decision. Bureau failure leaves the record
        # pending and sends no notification.
        outcome = self.decision_engine.request_decision(validated)
        decision = outcome.get("decision")
        score = outcome.get("score")

        if decision == DECISION_APPROVE:
            status, template, response = (
                STATUS_APPROVED, "loan_approved", "approved")
        elif decision == DECISION_DECLINE:
            status, template, response = (
                STATUS_DECLINED, "loan_declined", "declined")
        elif decision == DECISION_REFER:
            status, template, response = (
                STATUS_MANUAL_REVIEW, "loan_under_review", "under_review")
        else:
            raise DecisionError("Unknown decision %r from Decision Engine" % decision)

        # 7: persist the decision.
        self.application_store.update_status(
            application_id, status, decision=decision, score=score
        )

        # 8: notify the applicant of the outcome.
        notification = self.notification_service.send(
            recipient=validated["applicant_id"],
            template=template,
            payload={
                "application_id": application_id,
                "status": status,
                "amount": validated["amount"],
                "term_months": validated["term_months"],
            },
        )

        # 9: return the response to the applicant.
        return {
            "application_id": application_id,
            "applicant_id": validated["applicant_id"],
            "status": status,
            "decision": decision,
            "response": response,
            "score": score,
            "band": outcome.get("band"),
            "reason": outcome.get("reason"),
            "notification_id": notification.get("notification_id"),
        }


# ---------------------------------------------------------------------------
# Container: Origination API
# ---------------------------------------------------------------------------


class OriginationApi:
    """Receives loan applications and orchestrates the credit decision."""

    def __init__(
        self,
        application_store: ApplicationStore,
        decision_engine: DecisionEngine,
        notification_service: NotificationService,
    ) -> None:
        self.application_validator = ApplicationValidator()
        self.application_service = ApplicationService(
            self.application_validator,
            application_store,
            decision_engine,
            notification_service,
        )

    def submit_application(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """JSON/HTTPS endpoint used by the applicant."""
        return self.application_service.submit_application(application)


# ---------------------------------------------------------------------------
# Person: Loan Applicant
# ---------------------------------------------------------------------------


class Applicant:
    """A retail customer applying for a personal loan.

    Rel: applicant -> origination_api ("Submits loan application to").
    """

    def __init__(self, origination_api: OriginationApi, applicant_id: str = "applicant-1") -> None:
        self.origination_api = origination_api
        self.applicant_id = applicant_id

    def submit_loan_application(self, application: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(application)
        payload.setdefault("applicant_id", self.applicant_id)
        return self.origination_api.submit_application(payload)


# ---------------------------------------------------------------------------
# Wiring + end-to-end entry point
# ---------------------------------------------------------------------------


def _first(request: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in request and request[key] is not None:
            return request[key]
    return None


def _flag(request: Dict[str, Any], *keys: str, default: bool = True) -> bool:
    value = _first(request, *keys)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    word = str(value).strip().lower()
    if word in ("true", "yes", "y", "1", "found", "exists", "present", "ok"):
        return True
    if word in ("false", "no", "n", "0", "missing", "absent", "not_found",
                "none", "unknown"):
        return False
    return default


def build_system(request: Optional[Dict[str, Any]] = None):
    """Wire the whole model from a scenario request dict."""
    request = request or {}

    bureau_outcome = _first(
        request,
        "credit_bureau_result", "credit_bureau_status",
        "bureau_result", "bureau_status",
        "credit_score", "score",
    )
    if bureau_outcome is None:
        bureau_outcome = "ok"
    if not _flag(request, "credit_bureau_exists", "credit_bureau_found",
                 "bureau_exists", "bureau_found"):
        bureau_outcome = "unavailable"

    explicit_score = _first(request, "credit_score", "score")
    score_value: Optional[int] = None
    if explicit_score is not None:
        try:
            score_value = int(explicit_score)
        except (TypeError, ValueError):
            score_value = None

    store_outcome = _first(
        request, "application_store_result", "application_store_status",
        "store_result", "store_status",
    )
    if store_outcome is None:
        store_outcome = "stored"
    if not _flag(request, "application_store_exists", "application_store_found",
                 "store_exists", "store_found"):
        store_outcome = "unavailable"

    notification_outcome = _first(
        request, "notification_service_result", "notification_service_status",
        "notification_result", "notification_status",
    )
    if notification_outcome is None:
        notification_outcome = "sent"

    credit_bureau = CreditBureau(outcome=bureau_outcome, score=score_value)
    application_store = ApplicationStore(outcome=store_outcome)
    notification_service = NotificationService(outcome=notification_outcome)
    decision_engine = DecisionEngine(credit_bureau)
    origination_api = OriginationApi(
        application_store, decision_engine, notification_service
    )
    applicant = Applicant(
        origination_api,
        applicant_id=str(_first(request, "applicant_id", "customer_id") or "applicant-1"),
    )
    return {
        "applicant": applicant,
        "origination_api": origination_api,
        "application_store": application_store,
        "decision_engine": decision_engine,
        "credit_bureau": credit_bureau,
        "notification_service": notification_service,
    }


def handle(request: dict) -> dict:
    """Run one end-to-end credit-check flow.

    Outcome statuses:
      confirmed  - application approved
      declined   - application declined on score
      review     - application referred to manual review
      rejected   - application invalid (nothing stored, no bureau call)
      error: <reason> - storage failure, bureau unavailable, notification
                        failure, or missing applicant
    """
    request = dict(request or {})
    system = build_system(request)
    applicant: Applicant = system["applicant"]
    store: ApplicationStore = system["application_store"]

    # Guard: the applicant must exist before anything is submitted.
    if not _flag(request, "applicant_exists", "applicant_found"):
        return {
            "status": "error: applicant_not_found",
            "reason": "applicant_not_found",
            "application_id": None,
            "decision": None,
            "score": None,
            "notified": False,
            "bureau_calls": 0,
        }

    application = {
        "application_id": _first(request, "application_id"),
        "applicant_id": str(_first(request, "applicant_id", "customer_id") or "applicant-1"),
        "amount": _first(request, "amount", "loan_amount", "requested_amount"),
        "term_months": _first(request, "term_months", "term", "months"),
        "product": _first(request, "product") or "personal_loan",
    }
    if application["amount"] is None:
        application["amount"] = 10_000.0
    if application["term_months"] is None:
        application["term_months"] = 36

    try:
        result = applicant.submit_loan_application(application)
    except ValidationError as exc:
        return {
            "status": "rejected",
            "reason": "invalid_application",
            "detail": str(exc),
            "field": exc.field,
            "application_id": None,
            "decision": None,
            "score": None,
            "notified": False,
            "bureau_calls": len(system["credit_bureau"].calls),
        }
    except StorageError as exc:
        return {
            "status": "error: storage_unavailable",
            "reason": "storage_unavailable",
            "detail": str(exc),
            "application_id": None,
            "decision": None,
            "score": None,
            "notified": False,
            "bureau_calls": len(system["credit_bureau"].calls),
        }
    except BureauUnavailableError as exc:
        pending = next(iter(store.records.values()), None)
        return {
            "status": "error: bureau_unavailable",
            "reason": "bureau_unavailable",
            "detail": str(exc),
            "application_id": pending["application_id"] if pending else None,
            "application_status": pending["status"] if pending else None,
            "decision": None,
            "score": None,
            "notified": False,
            "bureau_calls": len(system["credit_bureau"].calls),
        }
    except ApplicationNotFoundError as exc:
        return {
            "status": "error: application_not_found",
            "reason": "application_not_found",
            "detail": str(exc),
            "application_id": None,
            "decision": None,
            "score": None,
            "notified": False,
            "bureau_calls": len(system["credit_bureau"].calls),
        }
    except NotificationError as exc:
        return {
            "status": "error: notification_failed",
            "reason": "notification_failed",
            "detail": str(exc),
            "application_id": next(iter(store.records), None),
            "decision": None,
            "score": None,
            "notified": False,
            "bureau_calls": len(system["credit_bureau"].calls),
        }
    except LoanCheckError as exc:
        return {
            "status": "error: %s" % exc.reason,
            "reason": exc.reason,
            "detail": str(exc),
            "application_id": None,
            "decision": None,
            "score": None,
            "notified": False,
            "bureau_calls": len(system["credit_bureau"].calls),
        }

    status_map = {
        STATUS_APPROVED: "confirmed",
        STATUS_DECLINED: "declined",
        STATUS_MANUAL_REVIEW: "review",
    }

    return {
        "status": status_map.get(result["status"], result["status"]),
        "application_id": result["application_id"],
        "applicant_id": result["applicant_id"],
        "application_status": result["status"],
        "decision": result["decision"],
        "score": result["score"],
        "band": result["band"],
        "reason": result["reason"],
        "notified": bool(result.get("notification_id")),
        "notification_id": result.get("notification_id"),
        "bureau_calls": len(system["credit_bureau"].calls),
    }


__all__ = [
    "Applicant",
    "OriginationApi",
    "ApplicationService",
    "ApplicationValidator",
    "ApplicationStore",
    "DecisionEngine",
    "ScoringPolicy",
    "BureauGateway",
    "CreditBureau",
    "NotificationService",
    "LoanCheckError",
    "ValidationError",
    "StorageError",
    "ApplicationNotFoundError",
    "BureauUnavailableError",
    "DecisionError",
    "NotificationError",
    "build_system",
    "handle",
]
