"""
LoanCheck - Personal Loan Origination System (credit-check scope).

Self-contained implementation derived from the C4 model:

  * containers.puml           - Origination API, Decision Engine, Application Store,
                                Credit Bureau (ext), Notification Service (ext)
  * components_api.puml       - Application Service, Application Validator
  * components_engine.puml    - Scoring Policy, Bureau Gateway
  * dynamics.puml             - approved / declined / manual-review / invalid /
                                bureau-unavailable / storage-failure paths

Class-per-element mapping (alias -> class):

    applicant            -> Applicant                 (Person, drives the flow)
    origination_api      -> OriginationApi            (Container)
    application_service  -> ApplicationService        (Component of origination_api)
    application_validator-> ApplicationValidator      (Component of origination_api)
    decision_engine      -> DecisionEngine            (Container)
    scoring_policy       -> ScoringPolicy             (Component of decision_engine)
    bureau_gateway       -> BureauGateway             (Component of decision_engine)
    application_store    -> ApplicationStore          (ContainerDb)
    credit_bureau        -> CreditBureau              (System_Ext)
    notification_service -> NotificationService       (System_Ext)

Calls only ever follow a declared Rel.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Product limits and scoring bands
# ---------------------------------------------------------------------------

MIN_LOAN_AMOUNT = 500.0
MAX_LOAN_AMOUNT = 50000.0
MIN_TERM_MONTHS = 6
MAX_TERM_MONTHS = 84

APPROVE_SCORE_THRESHOLD = 700
REVIEW_SCORE_THRESHOLD = 600

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_DECLINED = "declined"
STATUS_UNDER_REVIEW = "under_review"

DECISION_APPROVE = "approve"
DECISION_DECLINE = "decline"
DECISION_REFER = "refer"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class LoanCheckError(Exception):
    """Base class for every failure raised inside the LoanCheck system."""

    reason = "loan_check_error"


class ValidationError(LoanCheckError):
    """The submitted application is incomplete or outside product limits."""

    reason = "invalid_application"

    def __init__(self, message: str, errors: Optional[list] = None) -> None:
        super().__init__(message)
        self.errors = list(errors or [message])


class StorageError(LoanCheckError):
    """The Application Store could not be reached or refused the write."""

    reason = "storage_unavailable"


class ApplicationNotFoundError(LoanCheckError):
    """No application record exists for the requested id."""

    reason = "application_not_found"


class BureauUnavailableError(LoanCheckError):
    """The Credit Bureau failed to return a report; no decision can be made."""

    reason = "bureau_unavailable"


class DecisionError(LoanCheckError):
    """The Decision Engine could not produce a decision."""

    reason = "decision_failed"


class NotificationError(LoanCheckError):
    """The Notification Service could not deliver the decision notification."""

    reason = "notification_failed"


# ---------------------------------------------------------------------------
# System_Ext: Credit Bureau
# ---------------------------------------------------------------------------


class CreditBureau:
    """External credit reference agency (System_Ext).

    Outside the system boundary: returns plausible canned values. The scenario
    can steer it with ``credit_bureau_result`` / ``credit_bureau_status``
    ("available", "error"/"unavailable"/"timeout") and ``credit_score``.
    """

    def __init__(self, outcome: str = "available", score: int = 720) -> None:
        self.outcome = (outcome or "available").lower()
        self.score = score

    def pull_credit_report(self, applicant_id: str, application_id: str) -> Dict[str, Any]:
        """Rel: bureau_gateway -> credit_bureau, "Pulls credit report and score"."""
        if self.outcome in ("error", "unavailable", "down", "timeout", "failure", "failed"):
            raise BureauUnavailableError(
                "Credit Bureau is unavailable for applicant %s" % applicant_id
            )
        if self.outcome in ("no_file", "not_found", "thin_file"):
            return {
                "applicant_id": applicant_id,
                "application_id": application_id,
                "reference": "CB-%s" % uuid.uuid4().hex[:10],
                "score": None,
                "file_found": False,
            }
        return {
            "applicant_id": applicant_id,
            "application_id": application_id,
            "reference": "CB-%s" % uuid.uuid4().hex[:10],
            "score": int(self.score),
            "file_found": True,
        }


# ---------------------------------------------------------------------------
# System_Ext: Notification Service
# ---------------------------------------------------------------------------


class NotificationService:
    """External messaging provider delivering e-mail and SMS (System_Ext)."""

    def __init__(self, outcome: str = "sent") -> None:
        self.outcome = (outcome or "sent").lower()
        self.sent: list = []

    def send_notification(
        self, applicant_id: str, application_id: str, template: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Rel: application_service -> notification_service, "Sends decision notifications"."""
        if self.outcome in ("error", "failed", "failure", "unavailable", "down"):
            raise NotificationError(
                "Notification Service rejected message for application %s" % application_id
            )
        receipt = {
            "message_id": "MSG-%s" % uuid.uuid4().hex[:10],
            "applicant_id": applicant_id,
            "application_id": application_id,
            "template": template,
            "channel": "email",
            "status": "sent",
            "payload": dict(payload),
        }
        self.sent.append(receipt)
        return receipt


# ---------------------------------------------------------------------------
# ContainerDb: Application Store
# ---------------------------------------------------------------------------


class ApplicationStore:
    """PostgreSQL 16 store of loan applications and their decision status."""

    def __init__(self, outcome: str = "stored") -> None:
        self.outcome = (outcome or "stored").lower()
        self._records: Dict[str, Dict[str, Any]] = {}

    # -- internals ---------------------------------------------------------

    def _guard_available(self) -> None:
        if self.outcome in ("error", "unavailable", "down", "failed", "failure", "timeout"):
            raise StorageError("Application Store is unavailable")

    # -- operations --------------------------------------------------------

    def store_application(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """Rel step 2: store a validated application as pending."""
        self._guard_available()
        record = dict(application)
        record["status"] = STATUS_PENDING
        record["decision"] = None
        record["credit_score"] = None
        self._records[record["application_id"]] = record
        return dict(record)

    def update_status(
        self,
        application_id: str,
        status: str,
        decision: Optional[str] = None,
        credit_score: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Rel step 7: update the stored application with its decision status."""
        self._guard_available()
        record = self._records.get(application_id)
        if record is None:
            raise ApplicationNotFoundError(
                "No application record for id %s" % application_id
            )
        record["status"] = status
        if decision is not None:
            record["decision"] = decision
        if credit_score is not None:
            record["credit_score"] = credit_score
        return dict(record)

    def get_application(self, application_id: str) -> Dict[str, Any]:
        self._guard_available()
        record = self._records.get(application_id)
        if record is None:
            raise ApplicationNotFoundError(
                "No application record for id %s" % application_id
            )
        return dict(record)


# ---------------------------------------------------------------------------
# Component of decision_engine: Bureau Gateway
# ---------------------------------------------------------------------------


class BureauGateway:
    """Encapsulates the credit bureau integration and its failure modes."""

    def __init__(self, credit_bureau: CreditBureau) -> None:
        self.credit_bureau = credit_bureau

    def fetch_credit_score(self, applicant_id: str, application_id: str) -> int:
        """Calls credit_bureau; translates any failure into BureauUnavailableError."""
        try:
            report = self.credit_bureau.pull_credit_report(applicant_id, application_id)
        except BureauUnavailableError:
            raise
        except Exception as exc:  # pragma: no cover - defensive translation
            raise BureauUnavailableError(
                "Credit Bureau call failed: %s" % exc
            ) from exc

        score = report.get("score")
        if score is None or not report.get("file_found", True):
            raise BureauUnavailableError(
                "Credit Bureau returned no usable score for applicant %s" % applicant_id
            )
        return int(score)


# ---------------------------------------------------------------------------
# Component of decision_engine: Scoring Policy
# ---------------------------------------------------------------------------


class ScoringPolicy:
    """Maps the applicant's credit score to a credit decision."""

    def __init__(self, bureau_gateway: BureauGateway) -> None:
        self.bureau_gateway = bureau_gateway

    def decide(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """Rel: origination_api -> scoring_policy, "Requests credit decision"."""
        score = self.bureau_gateway.fetch_credit_score(
            application["applicant_id"], application["application_id"]
        )

        if score >= APPROVE_SCORE_THRESHOLD:
            decision = DECISION_APPROVE
            reason = "score_sufficient"
        elif score >= REVIEW_SCORE_THRESHOLD:
            decision = DECISION_REFER
            reason = "score_borderline"
        else:
            decision = DECISION_DECLINE
            reason = "score_too_low"

        return {
            "application_id": application["application_id"],
            "decision": decision,
            "credit_score": score,
            "reason": reason,
        }


# ---------------------------------------------------------------------------
# Container: Decision Engine
# ---------------------------------------------------------------------------


class DecisionEngine:
    """Determines the credit decision for a validated application."""

    def __init__(self, scoring_policy: ScoringPolicy) -> None:
        self.scoring_policy = scoring_policy

    def request_decision(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """Rel: origination_api -> decision_engine, "Requests credit decision"."""
        return self.scoring_policy.decide(application)


# ---------------------------------------------------------------------------
# Component of origination_api: Application Validator
# ---------------------------------------------------------------------------


class ApplicationValidator:
    """Checks that a submitted application is complete and within product limits."""

    REQUIRED_FIELDS = ("applicant_id", "amount", "term_months")

    def validate(self, application: Dict[str, Any]) -> Dict[str, Any]:
        errors: list = []

        for field in self.REQUIRED_FIELDS:
            value = application.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append("missing_%s" % field)

        amount = application.get("amount")
        if amount is not None:
            try:
                amount = float(amount)
            except (TypeError, ValueError):
                errors.append("amount_not_numeric")
                amount = None
        if amount is not None:
            if amount <= 0:
                errors.append("amount_not_positive")
            elif amount < MIN_LOAN_AMOUNT:
                errors.append("amount_below_product_minimum")
            elif amount > MAX_LOAN_AMOUNT:
                errors.append("amount_above_product_maximum")

        term = application.get("term_months")
        if term is not None:
            try:
                term = int(term)
            except (TypeError, ValueError):
                errors.append("term_not_numeric")
                term = None
        if term is not None and (term < MIN_TERM_MONTHS or term > MAX_TERM_MONTHS):
            errors.append("term_outside_product_limits")

        if application.get("applicant_exists") is False or (
            application.get("applicant_found") is False
        ):
            errors.append("applicant_not_found")

        if errors:
            raise ValidationError("Application is not valid: %s" % ", ".join(errors), errors)

        return {"valid": True, "normalised": {"amount": amount, "term_months": term}}


# ---------------------------------------------------------------------------
# Component of origination_api: Application Service
# ---------------------------------------------------------------------------


class ApplicationService:
    """Orchestrates the credit-check flow: validation, storage, decision, notification."""

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

    def submit_application(self, submission: Dict[str, Any]) -> Dict[str, Any]:
        """Runs steps 1..9 of the dynamic diagrams for one submission."""
        application_id = submission.get("application_id") or "APP-%s" % uuid.uuid4().hex[:10]
        applicant_id = submission.get("applicant_id")

        application = {
            "application_id": application_id,
            "applicant_id": applicant_id,
            "amount": submission.get("amount"),
            "term_months": submission.get("term_months"),
            "applicant_exists": submission.get("applicant_exists"),
            "applicant_found": submission.get("applicant_found"),
        }

        # Step 2 (invalid path): validate before anything else - no credit report
        # is pulled and nothing is stored when validation fails.
        validation = self.application_validator.validate(application)
        application["amount"] = validation["normalised"]["amount"]
        application["term_months"] = validation["normalised"]["term_months"]

        # Step 2: store the application as pending. Storage failure aborts the
        # flow before any bureau pull or notification.
        self.application_store.store_application(application)

        # Step 3-6: ask the Decision Engine. A bureau failure leaves the
        # application pending and sends no decision notification.
        try:
            decision_result = self.decision_engine.request_decision(application)
        except BureauUnavailableError:
            raise

        decision = decision_result["decision"]
        credit_score = decision_result["credit_score"]

        if decision == DECISION_APPROVE:
            new_status = STATUS_APPROVED
            template = "loan_approved"
        elif decision == DECISION_DECLINE:
            new_status = STATUS_DECLINED
            template = "loan_declined"
        elif decision == DECISION_REFER:
            new_status = STATUS_UNDER_REVIEW
            template = "loan_under_review"
        else:  # pragma: no cover - defensive
            raise DecisionError("Unknown decision %r" % decision)

        # Step 7: persist the decision.
        record = self.application_store.update_status(
            application_id, new_status, decision=decision, credit_score=credit_score
        )

        # Step 8: notify the applicant of the outcome.
        notification: Optional[Dict[str, Any]] = None
        notification_status = "sent"
        try:
            notification = self.notification_service.send_notification(
                applicant_id,
                application_id,
                template,
                {
                    "decision": decision,
                    "status": new_status,
                    "amount": application["amount"],
                    "term_months": application["term_months"],
                },
            )
        except NotificationError:
            # The decision is already durably stored; a messaging failure must
            # not lose it, so the outcome is still returned to the applicant.
            notification_status = "failed"

        # Step 9: return the outcome.
        return {
            "application_id": application_id,
            "applicant_id": applicant_id,
            "application_status": record["status"],
            "decision": decision,
            "credit_score": credit_score,
            "reason": decision_result["reason"],
            "notification": notification,
            "notification_status": notification_status,
        }


# ---------------------------------------------------------------------------
# Container: Origination API
# ---------------------------------------------------------------------------


class OriginationApi:
    """Receives applications, validates, orchestrates the decision, notifies."""

    def __init__(self, application_service: ApplicationService) -> None:
        self.application_service = application_service

    def submit_loan_application(self, submission: Dict[str, Any]) -> Dict[str, Any]:
        """Rel: applicant -> origination_api, "Submits loan application to"."""
        try:
            outcome = self.application_service.submit_application(submission)
        except ValidationError as exc:
            return {
                "status": "rejected",
                "reason": "invalid_application",
                "errors": exc.errors,
                "application_stored": False,
                "credit_report_pulled": False,
                "notification_sent": False,
            }
        except StorageError as exc:
            return {
                "status": "error: storage_unavailable",
                "reason": "storage_unavailable",
                "detail": str(exc),
                "application_stored": False,
                "credit_report_pulled": False,
                "notification_sent": False,
            }
        except BureauUnavailableError as exc:
            return {
                "status": "error: bureau_unavailable",
                "reason": "bureau_unavailable",
                "detail": str(exc),
                "application_status": STATUS_PENDING,
                "application_stored": True,
                "credit_report_pulled": False,
                "notification_sent": False,
            }
        except ApplicationNotFoundError as exc:
            return {
                "status": "error: application_not_found",
                "reason": "application_not_found",
                "detail": str(exc),
                "notification_sent": False,
            }
        except LoanCheckError as exc:
            return {
                "status": "error: %s" % exc.reason,
                "reason": exc.reason,
                "detail": str(exc),
                "notification_sent": False,
            }

        decision = outcome["decision"]
        if decision == DECISION_APPROVE:
            status = "confirmed"
        elif decision == DECISION_DECLINE:
            status = "declined"
        else:
            status = "under_review"

        return {
            "status": status,
            "decision": decision,
            "application_id": outcome["application_id"],
            "applicant_id": outcome["applicant_id"],
            "application_status": outcome["application_status"],
            "credit_score": outcome["credit_score"],
            "reason": outcome["reason"],
            "application_stored": True,
            "credit_report_pulled": True,
            "notification_sent": outcome["notification_status"] == "sent",
        }


# ---------------------------------------------------------------------------
# Person: Loan Applicant
# ---------------------------------------------------------------------------


class Applicant:
    """A retail customer applying for a personal loan."""

    def __init__(self, origination_api: OriginationApi, applicant_id: str = "APPLICANT-1") -> None:
        self.origination_api = origination_api
        self.applicant_id = applicant_id

    def submit_loan_application(self, submission: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(submission)
        payload.setdefault("applicant_id", self.applicant_id)
        return self.origination_api.submit_loan_application(payload)


# ---------------------------------------------------------------------------
# Wiring helpers
# ---------------------------------------------------------------------------


def _first(request: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in request and request[key] is not None:
            return request[key]
    return default


def _external_outcome(request: Dict[str, Any], name: str, default: str) -> str:
    value = _first(
        request,
        "%s_result" % name,
        "%s_status" % name,
        "%s_outcome" % name,
        default=default,
    )
    return str(value).lower()


def build_system(request: Optional[Dict[str, Any]] = None):
    """Instantiate the whole container/component graph for one scenario."""
    request = dict(request or {})

    bureau_outcome = _external_outcome(request, "credit_bureau", "available")
    if bureau_outcome in ("bureau_unavailable", "unavailable", "down"):
        bureau_outcome = "error"

    score = _first(
        request,
        "credit_score",
        "score",
        "credit_bureau_score",
        default=None,
    )
    if score is None:
        # The bureau outcome may itself carry the score or a decision hint.
        raw = _external_outcome(request, "credit_bureau", "")
        if raw.isdigit():
            score = int(raw)
        elif raw in ("approved", "approve"):
            score = 780
        elif raw in ("declined", "decline", "rejected"):
            score = 540
        elif raw in ("review", "refer", "borderline", "manual_review"):
            score = 650
        else:
            score = 720
    try:
        score = int(score)
    except (TypeError, ValueError):
        score = 720
    if bureau_outcome.isdigit():
        bureau_outcome = "available"
    if bureau_outcome in ("approved", "approve", "declined", "decline", "rejected",
                          "review", "refer", "borderline", "manual_review", "assessed",
                          "ok", "success"):
        bureau_outcome = "available"

    store_outcome = _external_outcome(request, "application_store", "stored")
    if store_outcome in ("stored", "ok", "available", "success", "up"):
        store_outcome = "stored"

    notification_outcome = _external_outcome(request, "notification_service", "sent")
    if notification_outcome in ("sent", "ok", "delivered", "success", "active"):
        notification_outcome = "sent"

    credit_bureau = CreditBureau(outcome=bureau_outcome, score=score)
    notification_service = NotificationService(outcome=notification_outcome)
    application_store = ApplicationStore(outcome=store_outcome)

    bureau_gateway = BureauGateway(credit_bureau)
    scoring_policy = ScoringPolicy(bureau_gateway)
    decision_engine = DecisionEngine(scoring_policy)

    application_validator = ApplicationValidator()
    application_service = ApplicationService(
        application_validator, application_store, decision_engine, notification_service
    )
    origination_api = OriginationApi(application_service)
    applicant = Applicant(
        origination_api, str(_first(request, "applicant_id", default="APPLICANT-1"))
    )

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
# Module-level entry point
# ---------------------------------------------------------------------------


def handle(request: dict) -> dict:
    """Run one end-to-end credit-check flow.

    Recognised request keys:
        applicant_id, application_id, amount, term_months
        applicant_exists / applicant_found        -> False forces a rejection
        application_store_result / _status        -> "stored" | "error"
        credit_bureau_result / _status            -> "available" | "error" | a score
        credit_score                              -> numeric bureau score
        notification_service_result / _status     -> "sent" | "error"

    Returns a dict whose "status" is one of:
        "confirmed", "declined", "under_review", "rejected",
        "error: storage_unavailable", "error: bureau_unavailable", "error: <reason>"
    """
    request = dict(request or {})
    system = build_system(request)
    applicant: Applicant = system["applicant"]

    amount = _first(request, "amount", "loan_amount", default=10000.0)
    term = _first(request, "term_months", "term", default=36)

    submission = {
        "application_id": _first(request, "application_id"),
        "applicant_id": _first(request, "applicant_id", default=applicant.applicant_id),
        "amount": amount,
        "term_months": term,
        "applicant_exists": request.get("applicant_exists"),
        "applicant_found": request.get("applicant_found"),
    }

    try:
        return applicant.submit_loan_application(submission)
    except LoanCheckError as exc:  # pragma: no cover - OriginationApi maps these
        return {"status": "error: %s" % exc.reason, "reason": exc.reason, "detail": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error: unexpected", "reason": "unexpected", "detail": str(exc)}


if __name__ == "__main__":
    for scenario in (
        {"applicant_id": "A-1", "amount": 10000, "term_months": 36, "credit_score": 780},
        {"applicant_id": "A-2", "amount": 10000, "term_months": 36, "credit_score": 540},
        {"applicant_id": "A-3", "amount": 10000, "term_months": 36, "credit_score": 650},
        {"applicant_id": "A-4", "amount": 1000000, "term_months": 36},
        {"applicant_id": "A-5", "amount": 10000, "term_months": 36,
         "credit_bureau_result": "error"},
        {"applicant_id": "A-6", "amount": 10000, "term_months": 36,
         "application_store_result": "error"},
    ):
        print(scenario, "->", handle(scenario)["status"])
