"""LoanCheck - Personal Loan Origination System (credit-check scope).

Single-module implementation generated from the C4 model:

  * containers.puml         - container-level structure
  * components_api.puml     - Origination API internals
  * components_engine.puml  - Decision Engine internals
  * dynamics.puml           - approved / declined / review / invalid /
                              bureau-unavailable / storage-failure flows
  * spec.md                 - authoritative decision + error semantics

Structural mapping
------------------
Containers / ContainerDb / System_Ext  -> one class each:
    OriginationApi, DecisionEngine, ApplicationStore,
    CreditBureau (ext), NotificationService (ext)
Components -> one class each, implementing part of their container:
    ApplicationService, ApplicationValidator   (Origination API)
    ScoringPolicy, BureauGateway               (Decision Engine)
Person -> Applicant (drives the flow, calls only the Origination API)

Calls exist only where a Rel is declared.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Constants (spec.md: validation rules + decision policy)
# ---------------------------------------------------------------------------

MIN_AMOUNT = 500
MAX_AMOUNT = 84500
MIN_TERM_MONTHS = 9
MAX_TERM_MONTHS = 96

APPROVE_THRESHOLD = 713   # s >= 713            -> approved
REVIEW_THRESHOLD = 641    # 641 <= s <= 712     -> review
                          # s < 641             -> declined

DECISION_APPROVED = "approved"
DECISION_DECLINED = "declined"
DECISION_REVIEW = "review"

STATUS_PENDING = "pending"

STATUS_REJECTED_INVALID = "rejected: invalid_application"
STATUS_ERROR_BUREAU = "error: bureau_unavailable"
STATUS_ERROR_STORAGE = "error: storage_unavailable"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class LoanCheckError(Exception):
    """Base class for all LoanCheck failures."""

    status = "error: unknown"


class InvalidApplicationError(LoanCheckError):
    """The submitted application failed validation. Nothing else happens."""

    status = STATUS_REJECTED_INVALID

    def __init__(self, reason: str = "invalid_application") -> None:
        super().__init__(reason)
        self.reason = reason


class StorageUnavailableError(LoanCheckError):
    """The Application Store could not accept or update a record."""

    status = STATUS_ERROR_STORAGE


class BureauUnavailableError(LoanCheckError):
    """The Credit Bureau failed to return a report/score."""

    status = STATUS_ERROR_BUREAU


class NotificationError(LoanCheckError):
    """The Notification Service failed to deliver a decision notification."""

    status = "error: notification_failed"


# ---------------------------------------------------------------------------
# Person: Loan Applicant
# ---------------------------------------------------------------------------


class Applicant:
    """A retail customer applying for a personal loan.

    Rel(applicant, origination_api, "Submits loan application to")
    Rel(applicant, application_service, "Submits loan application to")
    """

    def __init__(self, origination_api: "OriginationApi", customer_id: str = "") -> None:
        self.origination_api = origination_api
        self.customer_id = customer_id

    def submit_loan_application(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """Step 1 of every dynamic diagram: submit to the Origination API."""
        return self.origination_api.submit_application(application)


# ---------------------------------------------------------------------------
# External systems (outside the system boundary)
# ---------------------------------------------------------------------------


class CreditBureau:
    """System_Ext: external credit reference agency (XML/HTTPS).

    Returns consumer credit reports and scores. Simulated here; the outcome
    is driven by the scenario keys ``credit_bureau_result`` /
    ``credit_bureau_status`` / ``credit_bureau_score``.
    """

    DEFAULT_SCORE = 720

    def __init__(self, outcome: Optional[Any] = None, score: Optional[int] = None) -> None:
        self.outcome = outcome
        self.score = score
        self.calls = 0

    def pull_credit_report(self, customer_id: str) -> Dict[str, Any]:
        """Pull the credit report and score for a consumer.

        Raises:
            BureauUnavailableError: when the bureau is down or errors.
        """
        self.calls += 1
        if not customer_id:
            raise BureauUnavailableError("bureau rejected an empty customer_id")

        score = _coerce_score(self.outcome)
        if score is None:
            score = _coerce_score(self.score)

        if score is None:
            word = _word(self.outcome)
            if word in ("unavailable", "error", "down", "timeout", "failed",
                        "failure", "offline", "not_found", "missing", "false"):
                raise BureauUnavailableError("credit bureau unavailable: %s" % (word or "error"))
            if word in ("approved", "ok", "success", "available", "assessed", "true"):
                score = self.DEFAULT_SCORE
            elif word == "declined":
                score = 540
            elif word == "review":
                score = 660
            else:
                score = self.DEFAULT_SCORE

        return {
            "customer_id": customer_id,
            "score": int(score),
            "report_id": "CB-" + uuid.uuid4().hex[:10],
            "source": "credit_bureau",
        }


class NotificationService:
    """System_Ext: external messaging provider (e-mail / SMS, REST/HTTPS)."""

    def __init__(self, outcome: Optional[Any] = None) -> None:
        self.outcome = outcome
        self.sent: list = []

    def send_notification(
        self,
        customer_id: str,
        decision: str,
        application_id: str,
    ) -> Dict[str, Any]:
        """Deliver a decision notification to the applicant."""
        word = _word(self.outcome)
        if word in ("error", "failed", "failure", "unavailable", "down", "timeout"):
            raise NotificationError("notification service unavailable: %s" % word)

        message = {
            "notification_id": "NT-" + uuid.uuid4().hex[:10],
            "customer_id": customer_id,
            "application_id": application_id,
            "decision": decision,
            "channel": "email",
            "delivered": True,
        }
        self.sent.append(message)
        return message


# ---------------------------------------------------------------------------
# ContainerDb: Application Store (PostgreSQL 16)
# ---------------------------------------------------------------------------


class ApplicationStore:
    """Stores loan applications and their decision status (SQL/TCP)."""

    def __init__(self, outcome: Optional[Any] = None) -> None:
        self.outcome = outcome
        self.records: Dict[str, Dict[str, Any]] = {}

    # -- availability ------------------------------------------------------

    def _guard_available(self) -> None:
        word = _word(self.outcome)
        if word in ("unavailable", "error", "down", "timeout", "failed",
                    "failure", "offline", "false"):
            raise StorageUnavailableError("application store unavailable: %s" % word)

    # -- operations --------------------------------------------------------

    def store_application(self, application: Dict[str, Any]) -> str:
        """Insert the application with status ``pending``; return its id."""
        self._guard_available()
        application_id = str(application.get("application_id") or
                             ("APP-" + uuid.uuid4().hex[:12]))
        self.records[application_id] = {
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
        record = self.records.get(application_id)
        if record is None:
            raise StorageUnavailableError("no such application: %s" % application_id)
        record["status"] = status
        return dict(record)

    def get_application(self, application_id: str) -> Optional[Dict[str, Any]]:
        record = self.records.get(application_id)
        return dict(record) if record is not None else None


# ---------------------------------------------------------------------------
# Components of the Decision Engine
# ---------------------------------------------------------------------------


class BureauGateway:
    """Component: encapsulates the credit bureau integration and failures.

    Rel(bureau_gateway, credit_bureau, "Pulls credit report and score from")
    """

    def __init__(self, credit_bureau: CreditBureau) -> None:
        self.credit_bureau = credit_bureau

    def fetch_score(self, customer_id: str) -> int:
        """Return the applicant's credit score.

        Raises:
            BureauUnavailableError: on any bureau failure or malformed report.
        """
        try:
            report = self.credit_bureau.pull_credit_report(customer_id)
        except BureauUnavailableError:
            raise
        except Exception as exc:  # any transport/parse failure is a bureau failure
            raise BureauUnavailableError("credit bureau call failed: %s" % exc)

        if not isinstance(report, dict) or report.get("score") is None:
            raise BureauUnavailableError("credit bureau returned no score")

        try:
            return int(report["score"])
        except (TypeError, ValueError):
            raise BureauUnavailableError("credit bureau returned a non-numeric score")


class ScoringPolicy:
    """Component: maps the applicant's credit score to a credit decision.

    Rel(origination_api, scoring_policy, "Requests credit decision from")
    Rel(scoring_policy, bureau_gateway, "Obtains the applicant's credit score via")
    """

    def __init__(self, bureau_gateway: BureauGateway) -> None:
        self.bureau_gateway = bureau_gateway

    def decide(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """Obtain the score and apply the decision policy."""
        score = self.bureau_gateway.fetch_score(application.get("customer_id", ""))
        return {"decision": self.classify(score), "score": score}

    @staticmethod
    def classify(score: int) -> str:
        """spec.md decision policy; thresholds inclusive exactly as written."""
        if score >= APPROVE_THRESHOLD:
            return DECISION_APPROVED
        if score >= REVIEW_THRESHOLD:
            return DECISION_REVIEW
        return DECISION_DECLINED


# ---------------------------------------------------------------------------
# Container: Decision Engine
# ---------------------------------------------------------------------------


class DecisionEngine:
    """Determines the credit decision for a validated application.

    Rel(decision_engine, credit_bureau, "Pulls credit report and score from")
    -- realised inside the container by BureauGateway.
    """

    def __init__(self, credit_bureau: CreditBureau) -> None:
        self.credit_bureau = credit_bureau
        self.bureau_gateway = BureauGateway(credit_bureau)
        self.scoring_policy = ScoringPolicy(self.bureau_gateway)

    def request_decision(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """Steps 3-6 of the dynamic diagrams.

        Raises:
            BureauUnavailableError: bureau failure - no decision is made.
        """
        return self.scoring_policy.decide(application)


# ---------------------------------------------------------------------------
# Components of the Origination API
# ---------------------------------------------------------------------------


class ApplicationValidator:
    """Component: completeness + product-limit checks.

    Rel(application_service, application_validator, "Validates the application via")
    """

    def validate(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """Return the normalised application.

        Raises:
            InvalidApplicationError: if any validation rule fails.
        """
        if not isinstance(application, dict):
            raise InvalidApplicationError("application must be an object")

        customer_id = application.get("customer_id")
        if not isinstance(customer_id, str) or not customer_id.strip():
            raise InvalidApplicationError("customer_id missing or empty")

        amount = _as_number(application.get("amount"))
        if amount is None:
            raise InvalidApplicationError("amount missing or not a number")
        if not (MIN_AMOUNT <= amount <= MAX_AMOUNT):
            raise InvalidApplicationError("amount out of product limits")

        term_months = _as_number(application.get("term_months"))
        if term_months is None:
            raise InvalidApplicationError("term_months missing or not a number")
        if not (MIN_TERM_MONTHS <= term_months <= MAX_TERM_MONTHS):
            raise InvalidApplicationError("term_months out of product limits")

        return {
            "customer_id": customer_id.strip(),
            "amount": amount,
            "term_months": term_months,
        }


class ApplicationService:
    """Component: orchestrates validation, storage, decision, notification.

    Rel(application_service, application_validator, ...)
    Rel(application_service, application_store, ...)
    Rel(application_service, decision_engine, ...)
    Rel(application_service, notification_service, ...)
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
        # 1. Validate - invalid stops everything (no storage, no bureau, no notify).
        try:
            validated = self.application_validator.validate(application)
        except InvalidApplicationError as exc:
            return {"status": STATUS_REJECTED_INVALID, "reason": str(exc)}

        # 2. Store as pending.
        try:
            application_id = self.application_store.store_application(validated)
        except StorageUnavailableError as exc:
            return {"status": STATUS_ERROR_STORAGE, "reason": str(exc)}

        # 3. Request the decision (Decision Engine pulls the score).
        try:
            outcome = self.decision_engine.request_decision(validated)
        except BureauUnavailableError as exc:
            # Application stays pending; no notification.
            return {
                "status": STATUS_ERROR_BUREAU,
                "reason": str(exc),
                "application_id": application_id,
                "application_status": STATUS_PENDING,
            }

        decision = outcome["decision"]
        score = outcome.get("score")

        # 4. Update the stored application to the decision.
        try:
            self.application_store.update_application_status(application_id, decision)
        except StorageUnavailableError as exc:
            return {
                "status": STATUS_ERROR_STORAGE,
                "reason": str(exc),
                "application_id": application_id,
            }

        # 5. Notify the applicant (all three decisions).
        notified = True
        try:
            self.notification_service.send_notification(
                validated["customer_id"], decision, application_id
            )
        except NotificationError:
            # The decision stands; delivery is best-effort.
            notified = False

        # 6. Respond.
        return {
            "status": decision,
            "application_id": application_id,
            "score": score,
            "notified": notified,
        }


# ---------------------------------------------------------------------------
# Container: Origination API
# ---------------------------------------------------------------------------


class OriginationApi:
    """Receives applications, validates, orchestrates the decision, notifies."""

    def __init__(
        self,
        application_store: ApplicationStore,
        decision_engine: DecisionEngine,
        notification_service: NotificationService,
    ) -> None:
        self.application_store = application_store
        self.decision_engine = decision_engine
        self.notification_service = notification_service
        self.application_validator = ApplicationValidator()
        self.application_service = ApplicationService(
            self.application_validator,
            application_store,
            decision_engine,
            notification_service,
        )

    def submit_application(self, application: Dict[str, Any]) -> Dict[str, Any]:
        return self.application_service.submit_application(application)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _word(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip().lower()


def _as_number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _coerce_score(value: Any) -> Optional[int]:
    """Return an integer score if ``value`` looks like one, else None."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        try:
            return int(float(text))
        except ValueError:
            return None
    return None


def _first_present(request: Dict[str, Any], *keys: str) -> Optional[Any]:
    for key in keys:
        if key in request and request[key] is not None:
            return request[key]
    return None


def _exists_flag(request: Dict[str, Any], *keys: str) -> Optional[bool]:
    for key in keys:
        if key in request and request[key] is not None:
            value = request[key]
            if isinstance(value, bool):
                return value
            word = _word(value)
            if word in ("true", "yes", "found", "exists", "present", "1"):
                return True
            if word in ("false", "no", "missing", "not_found", "absent", "0"):
                return False
    return None


def _build_system(request: Dict[str, Any]):
    """Wire the containers/components from the scenario input."""
    # --- Application Store outcome ---------------------------------------
    store_outcome = _first_present(
        request,
        "application_store_result",
        "application_store_status",
        "store_result",
        "store_status",
        "storage_result",
        "storage_status",
    )
    store_exists = _exists_flag(
        request, "application_store_exists", "application_store_found",
        "store_exists", "store_found",
    )
    if store_exists is False:
        store_outcome = "unavailable"

    # --- Credit Bureau outcome -------------------------------------------
    bureau_outcome = _first_present(
        request,
        "credit_bureau_result",
        "credit_bureau_status",
        "bureau_result",
        "bureau_status",
        "credit_score",
        "score",
    )
    bureau_score = _coerce_score(
        _first_present(request, "credit_bureau_score", "credit_score", "score")
    )
    bureau_exists = _exists_flag(
        request, "credit_bureau_exists", "credit_bureau_found",
        "bureau_exists", "bureau_found",
    )
    if bureau_exists is False:
        bureau_outcome = "unavailable"
        bureau_score = None

    # --- Notification Service outcome ------------------------------------
    notification_outcome = _first_present(
        request,
        "notification_service_result",
        "notification_service_status",
        "notification_result",
        "notification_status",
    )
    notification_exists = _exists_flag(
        request, "notification_service_exists", "notification_service_found",
        "notification_exists", "notification_found",
    )
    if notification_exists is False:
        notification_outcome = "unavailable"

    credit_bureau = CreditBureau(outcome=bureau_outcome, score=bureau_score)
    notification_service = NotificationService(outcome=notification_outcome)
    application_store = ApplicationStore(outcome=store_outcome)
    decision_engine = DecisionEngine(credit_bureau)
    origination_api = OriginationApi(application_store, decision_engine, notification_service)
    return origination_api, application_store, credit_bureau, notification_service


# ---------------------------------------------------------------------------
# Module-level entry point
# ---------------------------------------------------------------------------


def handle(request: dict) -> dict:
    """Run one end-to-end credit check.

    Recognised scenario keys:
      * ``customer_id``, ``amount``, ``term_months`` - the application.
      * ``credit_bureau_result`` / ``credit_bureau_status`` / ``credit_score``
        - a number (the score) or a word such as ``error`` / ``unavailable``.
      * ``application_store_result`` / ``storage_status`` - ``stored`` or
        ``unavailable`` / ``error``.
      * ``notification_service_result`` - ``sent`` or ``error``.
      * ``<entity>_exists`` / ``<entity>_found`` - False forces that external
        dependency to fail.

    Returns a dict whose ``status`` is one of ``approved``, ``declined``,
    ``review``, ``rejected: invalid_application``, ``error: bureau_unavailable``,
    ``error: storage_unavailable``.
    """
    if not isinstance(request, dict):
        return {"status": STATUS_REJECTED_INVALID, "reason": "request must be an object"}

    origination_api, application_store, credit_bureau, notification_service = _build_system(request)

    application = {
        "customer_id": request.get("customer_id"),
        "amount": _first_present(request, "amount", "loan_amount", "principal"),
        "term_months": _first_present(request, "term_months", "term"),
    }
    if "application_id" in request:
        application["application_id"] = request["application_id"]

    applicant = Applicant(origination_api, customer_id=str(request.get("customer_id") or ""))

    try:
        response = applicant.submit_loan_application(application)
    except LoanCheckError as exc:
        return {"status": exc.status, "reason": str(exc)}
    except Exception as exc:  # defensive: never leak an unexpected traceback
        return {"status": "error: internal", "reason": str(exc)}

    response = dict(response)
    response["bureau_calls"] = credit_bureau.calls
    response["notifications_sent"] = len(notification_service.sent)
    application_id = response.get("application_id")
    if application_id:
        stored = application_store.get_application(application_id)
        if stored is not None:
            response["stored_status"] = stored["status"]
    return response


__all__ = [
    "Applicant",
    "OriginationApi",
    "ApplicationService",
    "ApplicationValidator",
    "DecisionEngine",
    "ScoringPolicy",
    "BureauGateway",
    "ApplicationStore",
    "CreditBureau",
    "NotificationService",
    "LoanCheckError",
    "InvalidApplicationError",
    "StorageUnavailableError",
    "BureauUnavailableError",
    "NotificationError",
    "handle",
]
