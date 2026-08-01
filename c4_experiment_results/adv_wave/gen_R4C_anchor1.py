"""LoanCheck - Personal Loan Origination System (credit-check scope).

Self-contained implementation derived from the C4 model:

  * containers.puml          -- OriginationApi, DecisionEngine, ApplicationStore,
                                CreditBureau (ext), NotificationService (ext)
  * components_api.puml      -- ApplicationService, ApplicationValidator
  * components_engine.puml   -- ScoringPolicy, BureauGateway
  * dynamics.puml            -- approved / declined / review / invalid /
                                bureau-unavailable / storage-unavailable paths
  * spec.md                  -- validation rules, decision policy, error policy

Class-to-class calls follow the declared Rel edges only.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Constants (spec.md: validation rules and decision policy)
# ---------------------------------------------------------------------------

MIN_AMOUNT = 1
MAX_AMOUNT = 100000
MIN_TERM_MONTHS = 6
MAX_TERM_MONTHS = 120

APPROVE_THRESHOLD = 700
REVIEW_THRESHOLD = 620

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
    """The submitted application failed validation. No bureau call is made."""

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
    """The Notification Service failed to deliver a decision notification."""

    status = "error: notification_unavailable"


# ---------------------------------------------------------------------------
# System_Ext: Credit Bureau
# ---------------------------------------------------------------------------


class CreditBureau:
    """External credit reference agency (System_Ext).

    Outside the system boundary: returns plausible values. The scenario key
    ``credit_bureau_result`` (or ``credit_bureau_status``) drives the outcome;
    a numeric value is taken as the credit score itself.
    """

    DEFAULT_SCORE = 720

    def __init__(self, outcome: Any = None, score: Optional[int] = None) -> None:
        self._outcome = outcome
        self._score = score

    def pull_credit_report(self, customer_id: str) -> Dict[str, Any]:
        """Pull a credit report and score for the applicant (XML/HTTPS)."""
        if not customer_id:
            raise BureauUnavailableError("no customer_id supplied to bureau")

        outcome = self._outcome

        # A number anywhere in the outcome is the credit score.
        numeric = _as_number(outcome)
        if numeric is not None:
            return {
                "customer_id": customer_id,
                "status": "ok",
                "score": int(numeric),
                "report_id": "CB-" + uuid.uuid4().hex[:10].upper(),
            }

        if isinstance(outcome, str):
            token = outcome.strip().lower()
            if token in {
                "error",
                "unavailable",
                "down",
                "timeout",
                "failed",
                "failure",
                "lapsed",
                "offline",
                "not_found",
                "missing",
            }:
                raise BureauUnavailableError("credit bureau unavailable: %s" % token)
            if token in {"approved", "active", "ok", "available", "assessed", "success"}:
                score = self._score if self._score is not None else self.DEFAULT_SCORE
                return {
                    "customer_id": customer_id,
                    "status": "ok",
                    "score": int(score),
                    "report_id": "CB-" + uuid.uuid4().hex[:10].upper(),
                }
            if token in {"declined", "rejected", "bad"}:
                return {
                    "customer_id": customer_id,
                    "status": "ok",
                    "score": 540,
                    "report_id": "CB-" + uuid.uuid4().hex[:10].upper(),
                }
            if token in {"review", "borderline", "refer"}:
                return {
                    "customer_id": customer_id,
                    "status": "ok",
                    "score": 660,
                    "report_id": "CB-" + uuid.uuid4().hex[:10].upper(),
                }

        if outcome is False:
            raise BureauUnavailableError("credit bureau unavailable")

        score = self._score if self._score is not None else self.DEFAULT_SCORE
        return {
            "customer_id": customer_id,
            "status": "ok",
            "score": int(score),
            "report_id": "CB-" + uuid.uuid4().hex[:10].upper(),
        }


# ---------------------------------------------------------------------------
# System_Ext: Notification Service
# ---------------------------------------------------------------------------


class NotificationService:
    """External messaging provider delivering e-mail and SMS (System_Ext)."""

    def __init__(self, outcome: Any = None) -> None:
        self._outcome = outcome
        self.sent: list = []

    def send(self, customer_id: str, decision: str, application_id: str) -> Dict[str, Any]:
        """Deliver a decision notification. Returns a plausible receipt."""
        outcome = self._outcome
        if isinstance(outcome, str) and outcome.strip().lower() in {
            "error",
            "failed",
            "failure",
            "unavailable",
            "down",
            "lapsed",
        }:
            raise NotificationError("notification service unavailable")
        if outcome is False:
            raise NotificationError("notification service unavailable")

        message_id = "NTF-" + uuid.uuid4().hex[:10].upper()
        receipt = {
            "message_id": message_id,
            "customer_id": customer_id,
            "application_id": application_id,
            "decision": decision,
            "channel": "email",
            "status": "sent",
        }
        self.sent.append(receipt)
        return receipt


# ---------------------------------------------------------------------------
# ContainerDb: Application Store
# ---------------------------------------------------------------------------


class ApplicationStore:
    """PostgreSQL 16 store for loan applications and their decision status."""

    def __init__(self, outcome: Any = None) -> None:
        self._outcome = outcome
        self.records: Dict[str, Dict[str, Any]] = {}

    # -- internal ----------------------------------------------------------
    def _check_available(self) -> None:
        outcome = self._outcome
        if outcome is False:
            raise StorageUnavailableError("application store unavailable")
        if isinstance(outcome, str) and outcome.strip().lower() in {
            "error",
            "unavailable",
            "down",
            "failed",
            "failure",
            "timeout",
            "lapsed",
            "offline",
        }:
            raise StorageUnavailableError("application store unavailable")

    # -- API ---------------------------------------------------------------
    def store_pending(self, application: Dict[str, Any]) -> str:
        """Insert the application with status ``pending``; return its id."""
        self._check_available()
        application_id = application.get("application_id") or (
            "APP-" + uuid.uuid4().hex[:12].upper()
        )
        self.records[application_id] = {
            "application_id": application_id,
            "customer_id": application.get("customer_id"),
            "amount": application.get("amount"),
            "term_months": application.get("term_months"),
            "status": STATUS_PENDING,
        }
        return application_id

    def update_status(self, application_id: str, status: str) -> Dict[str, Any]:
        """Update the stored application to the given decision status."""
        self._check_available()
        record = self.records.get(application_id)
        if record is None:
            raise StorageUnavailableError(
                "application %s not found in store" % application_id
            )
        record["status"] = status
        return dict(record)

    def get(self, application_id: str) -> Optional[Dict[str, Any]]:
        record = self.records.get(application_id)
        return dict(record) if record is not None else None


# ---------------------------------------------------------------------------
# Component of Decision Engine: Bureau Gateway
# ---------------------------------------------------------------------------


class BureauGateway:
    """Encapsulates the credit bureau integration and its failure modes."""

    def __init__(self, credit_bureau: CreditBureau) -> None:
        self.credit_bureau = credit_bureau

    def fetch_score(self, customer_id: str) -> int:
        """Return the applicant's credit score, or raise BureauUnavailableError."""
        try:
            report = self.credit_bureau.pull_credit_report(customer_id)
        except BureauUnavailableError:
            raise
        except Exception as exc:  # any bureau failure mode maps to unavailable
            raise BureauUnavailableError("credit bureau error: %s" % exc) from exc

        if not isinstance(report, dict):
            raise BureauUnavailableError("malformed credit report")
        if report.get("status") != "ok":
            raise BureauUnavailableError("credit bureau returned no report")

        score = report.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise BureauUnavailableError("credit bureau returned no score")
        return int(score)


# ---------------------------------------------------------------------------
# Component of Decision Engine: Scoring Policy
# ---------------------------------------------------------------------------


class ScoringPolicy:
    """Maps the applicant's credit score to a credit decision."""

    def __init__(self, bureau_gateway: BureauGateway) -> None:
        self.bureau_gateway = bureau_gateway

    @staticmethod
    def classify(score: int) -> str:
        """s >= 700 approved; 620 <= s <= 699 review; s < 620 declined."""
        if score >= APPROVE_THRESHOLD:
            return DECISION_APPROVED
        if score >= REVIEW_THRESHOLD:
            return DECISION_REVIEW
        return DECISION_DECLINED

    def decide(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """Obtain the score via the gateway, then apply the decision policy."""
        customer_id = application.get("customer_id")
        score = self.bureau_gateway.fetch_score(customer_id)
        return {"decision": self.classify(score), "score": score}


# ---------------------------------------------------------------------------
# Container: Decision Engine
# ---------------------------------------------------------------------------


class DecisionEngine:
    """Determines the credit decision for a validated application."""

    def __init__(self, credit_bureau: Optional[CreditBureau] = None) -> None:
        self.bureau_gateway = BureauGateway(credit_bureau or CreditBureau())
        self.scoring_policy = ScoringPolicy(self.bureau_gateway)

    def request_decision(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """Entry point called by the Origination API (JSON/HTTPS)."""
        return self.scoring_policy.decide(application)


# ---------------------------------------------------------------------------
# Component of Origination API: Application Validator
# ---------------------------------------------------------------------------


class ApplicationValidator:
    """Checks that a submitted application is complete and within limits."""

    @staticmethod
    def _is_number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def validate(self, application: Any) -> Dict[str, Any]:
        """Raise InvalidApplicationError unless every rule in spec.md holds."""
        if not isinstance(application, dict):
            raise InvalidApplicationError("application must be an object")

        customer_id = application.get("customer_id")
        if not isinstance(customer_id, str) or not customer_id.strip():
            raise InvalidApplicationError("customer_id missing or empty")

        amount = application.get("amount")
        if not self._is_number(amount):
            raise InvalidApplicationError("amount missing or not a number")
        if not (MIN_AMOUNT <= amount <= MAX_AMOUNT):
            raise InvalidApplicationError("amount out of product limits")

        term_months = application.get("term_months")
        if not self._is_number(term_months):
            raise InvalidApplicationError("term_months missing or not a number")
        if not (MIN_TERM_MONTHS <= term_months <= MAX_TERM_MONTHS):
            raise InvalidApplicationError("term_months out of product limits")

        return {
            "customer_id": customer_id.strip(),
            "amount": amount,
            "term_months": term_months,
        }


# ---------------------------------------------------------------------------
# Component of Origination API: Application Service
# ---------------------------------------------------------------------------


class ApplicationService:
    """Orchestrates the credit-check flow: validate, store, decide, notify."""

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
        # 1. Validate. Invalid -> reject, stop. No storage, bureau or notify.
        try:
            validated = self.application_validator.validate(application)
        except InvalidApplicationError as exc:
            return {"status": STATUS_REJECTED_INVALID, "reason": exc.reason}

        # 2. Store as pending. Storage failure -> stop, nothing else happens.
        try:
            application_id = self.application_store.store_pending(validated)
        except StorageUnavailableError:
            return {"status": STATUS_ERROR_STORAGE}

        # 3. Request the decision (engine pulls the bureau score).
        try:
            outcome = self.decision_engine.request_decision(validated)
        except BureauUnavailableError:
            # Application stays pending; no notification is sent.
            return {"status": STATUS_ERROR_BUREAU, "application_id": application_id}

        decision = outcome["decision"]
        score = outcome.get("score")

        # 4. Update the stored application to the decision.
        try:
            self.application_store.update_status(application_id, decision)
        except StorageUnavailableError:
            return {"status": STATUS_ERROR_STORAGE, "application_id": application_id}

        # 5. Send the decision notification (all three decisions).
        notification_sent = False
        try:
            self.notification_service.send(
                validated["customer_id"], decision, application_id
            )
            notification_sent = True
        except NotificationError:
            # Delivery is best-effort: the decision itself still stands.
            notification_sent = False

        # 6. Return the response to the applicant.
        return {
            "status": decision,
            "application_id": application_id,
            "score": score,
            "notification_sent": notification_sent,
        }


# ---------------------------------------------------------------------------
# Container: Origination API
# ---------------------------------------------------------------------------


class OriginationApi:
    """Receives applications, validates, orchestrates the decision, notifies."""

    def __init__(
        self,
        application_store: Optional[ApplicationStore] = None,
        decision_engine: Optional[DecisionEngine] = None,
        notification_service: Optional[NotificationService] = None,
    ) -> None:
        self.application_store = application_store or ApplicationStore()
        self.decision_engine = decision_engine or DecisionEngine()
        self.notification_service = notification_service or NotificationService()
        self.application_validator = ApplicationValidator()
        self.application_service = ApplicationService(
            self.application_validator,
            self.application_store,
            self.decision_engine,
            self.notification_service,
        )

    def submit_application(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """HTTP entry point used by the applicant (JSON/HTTPS)."""
        return self.application_service.submit_application(application)


# ---------------------------------------------------------------------------
# Person: Loan Applicant
# ---------------------------------------------------------------------------


class Applicant:
    """A retail customer applying for a personal loan."""

    def __init__(self, origination_api: OriginationApi, customer_id: str = "") -> None:
        self.origination_api = origination_api
        self.customer_id = customer_id

    def submit_loan_application(self, application: Dict[str, Any]) -> Dict[str, Any]:
        return self.origination_api.submit_application(application)


# ---------------------------------------------------------------------------
# Scenario helpers
# ---------------------------------------------------------------------------


def _as_number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        token = value.strip()
        try:
            return float(token)
        except (TypeError, ValueError):
            return None
    return None


_FALSEY_WORDS = {
    "false",
    "no",
    "0",
    "missing",
    "absent",
    "none",
    "not_found",
    "unavailable",
    "down",
    "error",
    "lapsed",
}


def _flag(request: Dict[str, Any], *keys: str) -> Optional[bool]:
    """Read an existence flag such as ``<entity>_exists`` / ``<entity>_found``."""
    for key in keys:
        if key not in request:
            continue
        value = request[key]
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            token = value.strip().lower()
            if token in _FALSEY_WORDS:
                return False
            return True
        if value is None:
            return False
        return bool(value)
    return None


def _outcome(request: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in request and request[key] is not None:
            return request[key]
    return None


def _build_system(request: Dict[str, Any]):
    """Wire the containers/components from the scenario knobs in ``request``."""
    # Application Store availability.
    store_outcome = _outcome(
        request,
        "application_store_result",
        "application_store_status",
        "store_result",
        "store_status",
        "storage_result",
        "storage_status",
    )
    store_exists = _flag(
        request,
        "application_store_exists",
        "application_store_found",
        "store_exists",
        "store_found",
    )
    if store_exists is False:
        store_outcome = "unavailable"
    application_store = ApplicationStore(store_outcome)

    # Credit Bureau outcome / score.
    bureau_outcome = _outcome(
        request,
        "credit_bureau_result",
        "credit_bureau_status",
        "bureau_result",
        "bureau_status",
        "decision_engine_result",
        "decision_engine_status",
        "score",
        "credit_score",
    )
    bureau_exists = _flag(
        request,
        "credit_bureau_exists",
        "credit_bureau_found",
        "bureau_exists",
        "bureau_found",
    )
    if bureau_exists is False:
        bureau_outcome = "unavailable"
    explicit_score = _as_number(
        _outcome(request, "score", "credit_score", "bureau_score")
    )
    credit_bureau = CreditBureau(
        bureau_outcome,
        int(explicit_score) if explicit_score is not None else None,
    )

    # Notification Service outcome.
    notification_outcome = _outcome(
        request,
        "notification_service_result",
        "notification_service_status",
        "notification_result",
        "notification_status",
    )
    notification_exists = _flag(
        request,
        "notification_service_exists",
        "notification_service_found",
        "notification_exists",
        "notification_found",
    )
    if notification_exists is False:
        notification_outcome = "unavailable"
    notification_service = NotificationService(notification_outcome)

    decision_engine = DecisionEngine(credit_bureau)
    origination_api = OriginationApi(
        application_store, decision_engine, notification_service
    )
    return origination_api, application_store, notification_service


# ---------------------------------------------------------------------------
# Module-level entry point
# ---------------------------------------------------------------------------


def handle(request: dict) -> dict:
    """Run one end-to-end credit-check flow.

    Recognised scenario keys:
      ``customer_id``, ``amount``, ``term_months`` (the application itself);
      ``customer_exists`` / ``customer_found`` (a missing customer makes the
      application invalid); ``credit_bureau_result`` / ``credit_bureau_status``
      (a number is the credit score, ``error``/``unavailable`` fails the pull);
      ``application_store_result`` / ``application_store_status``;
      ``notification_service_result`` / ``notification_service_status``.

    Returns a dict whose ``status`` is one of ``approved``, ``declined``,
    ``review``, ``rejected: invalid_application``, ``error: bureau_unavailable``
    or ``error: storage_unavailable``; ``application_id`` is present whenever
    the application was stored.
    """
    if not isinstance(request, dict):
        return {"status": STATUS_REJECTED_INVALID, "reason": "request must be an object"}

    application = {
        "customer_id": request.get("customer_id"),
        "amount": request.get("amount"),
        "term_months": request.get("term_months"),
    }

    # A declared-missing customer cannot yield a valid application.
    customer_exists = _flag(
        request, "customer_exists", "customer_found", "applicant_exists", "applicant_found"
    )
    if customer_exists is False:
        return {"status": STATUS_REJECTED_INVALID, "reason": "customer not found"}

    origination_api, application_store, notification_service = _build_system(request)
    applicant = Applicant(origination_api, str(application.get("customer_id") or ""))

    try:
        response = applicant.submit_loan_application(application)
    except LoanCheckError as exc:
        return {"status": exc.status, "reason": str(exc)}

    result: Dict[str, Any] = {"status": response["status"]}
    if response.get("application_id"):
        result["application_id"] = response["application_id"]
    if response.get("reason"):
        result["reason"] = response["reason"]
    if response.get("score") is not None:
        result["score"] = response["score"]
    result["notification_sent"] = bool(notification_service.sent)
    if response.get("application_id"):
        record = application_store.get(response["application_id"])
        if record is not None:
            result["stored_status"] = record["status"]
    return result


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
