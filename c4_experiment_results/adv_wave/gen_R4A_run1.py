"""
LoanCheck - Personal Loan Origination System (credit-check scope).

Single self-contained module generated from the C4 model:

  * containers.puml        - container-level structure
  * components_api.puml    - Origination API components
  * components_engine.puml - Decision Engine components
  * dynamics.puml          - approved / declined / review / invalid /
                             bureau-unavailable / storage-failure flows
  * spec.md                - decision semantics, validation rules,
                             error policy and API contract

Class per C4 element (alias in CamelCase):

  Applicant             - Person(applicant)
  OriginationApi        - Container(origination_api)
  ApplicationService    - Component(application_service)   [inside OriginationApi]
  ApplicationValidator  - Component(application_validator) [inside OriginationApi]
  DecisionEngine        - Container(decision_engine)
  ScoringPolicy         - Component(scoring_policy)        [inside DecisionEngine]
  BureauGateway         - Component(bureau_gateway)        [inside DecisionEngine]
  ApplicationStore      - ContainerDb(application_store)
  CreditBureau          - System_Ext(credit_bureau)
  NotificationService   - System_Ext(notification_service)

Calls only ever follow a declared Rel.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

__all__ = [
    "LoanCheckError",
    "InvalidApplicationError",
    "StorageUnavailableError",
    "BureauUnavailableError",
    "NotificationError",
    "Application",
    "Decision",
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
# Constants pinned by spec.md
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

DEFAULT_SCORE = 760


# ---------------------------------------------------------------------------
# Errors (failure paths from the dynamic diagrams / error policy)
# ---------------------------------------------------------------------------


class LoanCheckError(Exception):
    """Base class for all LoanCheck failures."""

    status = "error: unknown"


class InvalidApplicationError(LoanCheckError):
    """The submitted application failed validation - nothing else happens."""

    status = STATUS_REJECTED_INVALID

    def __init__(self, reason: str = "invalid_application") -> None:
        super().__init__(reason)
        self.reason = reason


class StorageUnavailableError(LoanCheckError):
    """The Application Store could not store or update the application."""

    status = STATUS_ERROR_STORAGE


class BureauUnavailableError(LoanCheckError):
    """The Credit Bureau did not return a usable credit report/score."""

    status = STATUS_ERROR_BUREAU


class NotificationError(LoanCheckError):
    """The Notification Service could not deliver the decision notification."""

    status = "error: notification_unavailable"


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


class Application:
    """One request for a personal loan (glossary, spec.md)."""

    def __init__(
        self,
        customer_id: Any,
        amount: Any,
        term_months: Any,
        application_id: Optional[str] = None,
        status: str = STATUS_PENDING,
    ) -> None:
        self.application_id = application_id
        self.customer_id = customer_id
        self.amount = amount
        self.term_months = term_months
        self.status = status

    @classmethod
    def from_request(cls, request: Dict[str, Any]) -> "Application":
        request = request or {}
        return cls(
            customer_id=request.get("customer_id"),
            amount=request.get("amount"),
            term_months=request.get("term_months"),
            application_id=request.get("application_id"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "application_id": self.application_id,
            "customer_id": self.customer_id,
            "amount": self.amount,
            "term_months": self.term_months,
            "status": self.status,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "Application({!r})".format(self.to_dict())


class Decision:
    """Outcome of the credit check: approved | declined | review."""

    def __init__(self, outcome: str, score: Optional[int] = None, reason: str = "") -> None:
        if outcome not in (DECISION_APPROVED, DECISION_DECLINED, DECISION_REVIEW):
            raise ValueError("unknown decision outcome: {!r}".format(outcome))
        self.outcome = outcome
        self.score = score
        self.reason = reason

    @property
    def is_approved(self) -> bool:
        return self.outcome == DECISION_APPROVED

    @property
    def is_declined(self) -> bool:
        return self.outcome == DECISION_DECLINED

    @property
    def is_review(self) -> bool:
        return self.outcome == DECISION_REVIEW

    def to_dict(self) -> Dict[str, Any]:
        return {"decision": self.outcome, "score": self.score, "reason": self.reason}

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "Decision({!r}, score={!r})".format(self.outcome, self.score)


# ---------------------------------------------------------------------------
# External systems (System_Ext) - outside the system boundary
# ---------------------------------------------------------------------------


class CreditBureau:
    """System_Ext(credit_bureau).

    External credit reference agency providing consumer credit reports and
    scores. Simulated: the outcome is driven by the scenario options.
    """

    UNAVAILABLE_WORDS = {
        "error",
        "unavailable",
        "down",
        "timeout",
        "failed",
        "failure",
        "fail",
        "outage",
        "not_found",
        "missing",
        "no_report",
    }
    AVAILABLE_WORDS = {"ok", "available", "up", "success", "assessed", "scored", "found"}

    def __init__(self, result: Any = None, score: Optional[int] = None) -> None:
        self._result = result
        self._score = score
        self.calls = 0

    # Rel: bureau_gateway -> credit_bureau, "Pulls credit report and score from"
    def pull_credit_report(self, customer_id: Any) -> Dict[str, Any]:
        self.calls += 1
        score = self._resolve_score()
        if score is None:
            raise BureauUnavailableError("credit bureau did not return a report")
        return {
            "customer_id": customer_id,
            "score": score,
            "status": "ok",
            "report_id": "cb-" + uuid.uuid4().hex[:10],
        }

    # -- internals ----------------------------------------------------------

    def _resolve_score(self) -> Optional[int]:
        value = self._result

        if isinstance(value, bool):
            return int(self._score) if (value and self._score is not None) else (
                DEFAULT_SCORE if value else None
            )

        if isinstance(value, (int, float)):
            return int(value)

        if isinstance(value, dict):
            inner_status = str(value.get("status", "")).strip().lower()
            if inner_status in self.UNAVAILABLE_WORDS:
                return None
            if "score" in value and value["score"] is not None:
                return int(value["score"])
            return int(self._score) if self._score is not None else DEFAULT_SCORE

        if isinstance(value, str):
            word = value.strip().lower()
            if word:
                try:
                    return int(float(word))
                except ValueError:
                    pass
                if word in self.UNAVAILABLE_WORDS:
                    return None
                if word in self.AVAILABLE_WORDS:
                    return int(self._score) if self._score is not None else DEFAULT_SCORE
                # Unrecognised word: treat as available with the given score.
                return int(self._score) if self._score is not None else DEFAULT_SCORE

        if self._score is not None:
            return int(self._score)
        return DEFAULT_SCORE


class NotificationService:
    """System_Ext(notification_service).

    External messaging provider delivering e-mail and SMS notifications.
    Simulated: always accepts unless the scenario says otherwise.
    """

    FAILURE_WORDS = {"error", "unavailable", "failed", "failure", "fail", "down", "timeout"}

    def __init__(self, result: Any = None) -> None:
        self._result = result
        self.sent: list = []

    # Rel: application_service -> notification_service, "Sends decision notifications via"
    def send(self, customer_id: Any, application_id: Optional[str], decision: str) -> Dict[str, Any]:
        if self._is_failure():
            raise NotificationError("notification service unavailable")
        message = {
            "notification_id": "ntf-" + uuid.uuid4().hex[:10],
            "customer_id": customer_id,
            "application_id": application_id,
            "decision": decision,
            "channel": "email",
            "status": "sent",
        }
        self.sent.append(message)
        return message

    def _is_failure(self) -> bool:
        value = self._result
        if value is None:
            return False
        if isinstance(value, bool):
            return not value
        if isinstance(value, dict):
            value = value.get("status")
        return str(value).strip().lower() in self.FAILURE_WORDS


# ---------------------------------------------------------------------------
# ContainerDb(application_store)
# ---------------------------------------------------------------------------


class ApplicationStore:
    """ContainerDb(application_store) - PostgreSQL 16.

    Stores loan applications and their decision status.
    """

    FAILURE_WORDS = {
        "error",
        "unavailable",
        "down",
        "timeout",
        "failed",
        "failure",
        "fail",
        "offline",
        "outage",
    }
    SUCCESS_WORDS = {"ok", "stored", "up", "available", "success", "saved", "written"}

    def __init__(self, result: Any = None) -> None:
        self._result = result
        self._records: Dict[str, Dict[str, Any]] = {}

    # Rel: application_service -> application_store, "Stores ... application records in"
    def store_pending(self, application: Application) -> str:
        self._guard_available()
        application_id = application.application_id or "app-" + uuid.uuid4().hex[:12]
        application.application_id = application_id
        application.status = STATUS_PENDING
        self._records[application_id] = application.to_dict()
        return application_id

    # Rel: application_service -> application_store, "... and updates application records in"
    def update_status(self, application_id: str, status: str) -> Dict[str, Any]:
        self._guard_available()
        record = self._records.get(application_id)
        if record is None:
            raise StorageUnavailableError("unknown application: {!r}".format(application_id))
        record["status"] = status
        return dict(record)

    def get(self, application_id: str) -> Optional[Dict[str, Any]]:
        record = self._records.get(application_id)
        return dict(record) if record is not None else None

    def _guard_available(self) -> None:
        if self._is_unavailable():
            raise StorageUnavailableError("application store unavailable")

    def _is_unavailable(self) -> bool:
        value = self._result
        if value is None:
            return False
        if isinstance(value, bool):
            return not value
        if isinstance(value, dict):
            value = value.get("status")
        word = str(value).strip().lower()
        if not word:
            return False
        if word in self.SUCCESS_WORDS:
            return False
        return word in self.FAILURE_WORDS


# ---------------------------------------------------------------------------
# Decision Engine components
# ---------------------------------------------------------------------------


class BureauGateway:
    """Component(bureau_gateway) of the Decision Engine.

    Encapsulates the credit bureau integration and its failure modes.
    """

    def __init__(self, credit_bureau: CreditBureau) -> None:
        self.credit_bureau = credit_bureau

    def fetch_score(self, customer_id: Any) -> int:
        """Pull the credit report from the bureau and extract the score.

        Any bureau problem surfaces as BureauUnavailableError.
        """
        try:
            report = self.credit_bureau.pull_credit_report(customer_id)
        except BureauUnavailableError:
            raise
        except Exception as exc:  # bureau transport / protocol failure
            raise BureauUnavailableError("credit bureau call failed: {}".format(exc))

        if not isinstance(report, dict):
            raise BureauUnavailableError("credit bureau returned no report")

        score = report.get("score")
        if score is None:
            raise BureauUnavailableError("credit bureau returned no score")
        try:
            return int(score)
        except (TypeError, ValueError):
            raise BureauUnavailableError("credit bureau returned a malformed score")


class ScoringPolicy:
    """Component(scoring_policy) of the Decision Engine.

    Maps the applicant's credit score to a credit decision.

        s >= 713        -> approved
        641 <= s <= 712 -> review
        s < 641         -> declined
    """

    def __init__(self, bureau_gateway: BureauGateway) -> None:
        self.bureau_gateway = bureau_gateway

    def decide(self, application: Application) -> Decision:
        score = self.bureau_gateway.fetch_score(application.customer_id)
        return Decision(self.classify(score), score=score, reason=self._reason(score))

    @staticmethod
    def classify(score: int) -> str:
        if score >= APPROVE_THRESHOLD:
            return DECISION_APPROVED
        if score >= REVIEW_THRESHOLD:
            return DECISION_REVIEW
        return DECISION_DECLINED

    @staticmethod
    def _reason(score: int) -> str:
        if score >= APPROVE_THRESHOLD:
            return "score sufficient"
        if score >= REVIEW_THRESHOLD:
            return "score borderline"
        return "score too low"


class DecisionEngine:
    """Container(decision_engine) - Python 3.12, rules library.

    Determines the credit decision for a validated application.
    """

    def __init__(self, credit_bureau: CreditBureau) -> None:
        self.bureau_gateway = BureauGateway(credit_bureau)
        self.scoring_policy = ScoringPolicy(self.bureau_gateway)

    # Rel: origination_api -> decision_engine, "Requests credit decision from"
    def request_decision(self, application: Application) -> Decision:
        return self.scoring_policy.decide(application)


# ---------------------------------------------------------------------------
# Origination API components
# ---------------------------------------------------------------------------


class ApplicationValidator:
    """Component(application_validator) of the Origination API.

    Checks that a submitted application is complete and within product limits.
    """

    def validate(self, application: Application) -> None:
        """Raise InvalidApplicationError when the application is not valid."""
        customer_id = application.customer_id
        if not isinstance(customer_id, str) or not customer_id.strip():
            raise InvalidApplicationError("customer_id missing or empty")

        amount = self._as_number(application.amount)
        if amount is None:
            raise InvalidApplicationError("amount is not a number")
        if not (MIN_AMOUNT <= amount <= MAX_AMOUNT):
            raise InvalidApplicationError("amount out of product limits")

        term = self._as_number(application.term_months)
        if term is None:
            raise InvalidApplicationError("term_months is not a number")
        if not (MIN_TERM_MONTHS <= term <= MAX_TERM_MONTHS):
            raise InvalidApplicationError("term_months out of product limits")

    def is_valid(self, application: Application) -> bool:
        try:
            self.validate(application)
        except InvalidApplicationError:
            return False
        return True

    @staticmethod
    def _as_number(value: Any) -> Optional[float]:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        return None


class ApplicationService:
    """Component(application_service) of the Origination API.

    Orchestrates the credit-check flow: validation, storage, decision,
    notification - in exactly the order given by spec.md.
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

    # Rel: applicant -> application_service, "Submits loan application to"
    def submit_application(self, request: Dict[str, Any]) -> Dict[str, Any]:
        application = Application.from_request(request)

        # 1. Validate - invalid stops everything (no storage, no bureau, no notification).
        try:
            self.application_validator.validate(application)
        except InvalidApplicationError as exc:
            return {"status": STATUS_REJECTED_INVALID, "reason": exc.reason}

        # 2. Store as pending.
        try:
            application_id = self.application_store.store_pending(application)
        except StorageUnavailableError as exc:
            return {"status": STATUS_ERROR_STORAGE, "reason": str(exc)}

        # 3. Request the credit decision (engine pulls the score from the bureau).
        try:
            decision = self.decision_engine.request_decision(application)
        except BureauUnavailableError as exc:
            # Application stays pending; no notification.
            return {
                "status": STATUS_ERROR_BUREAU,
                "application_id": application_id,
                "application_status": STATUS_PENDING,
                "reason": str(exc),
            }

        # 4. Update the stored application to the decision.
        try:
            self.application_store.update_status(application_id, decision.outcome)
        except StorageUnavailableError as exc:
            return {
                "status": STATUS_ERROR_STORAGE,
                "application_id": application_id,
                "reason": str(exc),
            }

        # 5. Send the decision notification (all three decisions).
        notification_sent = True
        notification_error = None
        try:
            self.notification_service.send(
                application.customer_id, application_id, decision.outcome
            )
        except NotificationError as exc:
            # The decision stands; delivery failure is reported but not fatal.
            notification_sent = False
            notification_error = str(exc)

        # 6. Return the response.
        response: Dict[str, Any] = {
            "status": decision.outcome,
            "application_id": application_id,
            "application_status": decision.outcome,
            "score": decision.score,
            "reason": decision.reason,
            "notification_sent": notification_sent,
        }
        if notification_error is not None:
            response["notification_error"] = notification_error
        return response


class OriginationApi:
    """Container(origination_api) - Python 3.12, FastAPI.

    Receives loan applications, validates them, orchestrates the credit
    decision, and notifies the applicant of the outcome.
    """

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

    # Rel: applicant -> origination_api, "Submits loan application to"
    def submit_application(self, request: Dict[str, Any]) -> Dict[str, Any]:
        return self.application_service.submit_application(request)


# ---------------------------------------------------------------------------
# Person(applicant)
# ---------------------------------------------------------------------------


class Applicant:
    """Person(applicant) - a retail customer applying for a personal loan."""

    def __init__(self, origination_api: OriginationApi, customer_id: Any = None) -> None:
        self.origination_api = origination_api
        self.customer_id = customer_id

    # Rel: applicant -> origination_api, "Submits loan application to"
    def submit_loan_application(self, request: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(request or {})
        if self.customer_id is not None and "customer_id" not in payload:
            payload["customer_id"] = self.customer_id
        return self.origination_api.submit_application(payload)


# ---------------------------------------------------------------------------
# Wiring + end-to-end entry point
# ---------------------------------------------------------------------------


def _first_present(request: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in request and request[key] is not None:
            return request[key]
    return None


def _existence_flag(request: Dict[str, Any], *keys: str) -> Optional[bool]:
    for key in keys:
        if key in request:
            value = request[key]
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                word = value.strip().lower()
                if word in ("true", "yes", "found", "exists", "present"):
                    return True
                if word in ("false", "no", "missing", "not_found", "absent"):
                    return False
    return None


def build_system(options: Optional[Dict[str, Any]] = None):
    """Instantiate the whole container graph for one scenario.

    Returns (applicant, origination_api, application_store, decision_engine,
    credit_bureau, notification_service).
    """
    options = options or {}

    credit_bureau = CreditBureau(
        result=options.get("credit_bureau_result"),
        score=options.get("credit_score"),
    )
    notification_service = NotificationService(result=options.get("notification_result"))
    application_store = ApplicationStore(result=options.get("application_store_result"))
    decision_engine = DecisionEngine(credit_bureau)
    origination_api = OriginationApi(application_store, decision_engine, notification_service)
    applicant = Applicant(origination_api, customer_id=options.get("customer_id"))

    return (
        applicant,
        origination_api,
        application_store,
        decision_engine,
        credit_bureau,
        notification_service,
    )


def handle(request: dict) -> dict:
    """Run one end-to-end credit check.

    Recognised scenario keys (beyond the API contract's customer_id / amount /
    term_months):

      credit_bureau_result / credit_bureau_status  - "ok", "error",
          "unavailable", or a number used directly as the credit score
      credit_score / score                          - explicit score
      application_store_result / application_store_status - "stored", "ok",
          "error", "unavailable"
      notification_service_result / notification_status   - "sent", "ok", "error"
      applicant_exists / customer_found / application_exists - existence flags
    """
    request = dict(request or {})

    # Existence flags: a missing applicant / customer cannot submit anything.
    for keys in (
        ("applicant_exists", "applicant_found"),
        ("customer_exists", "customer_found"),
        ("application_exists", "application_found"),
    ):
        flag = _existence_flag(request, *keys)
        if flag is False:
            return {"status": STATUS_REJECTED_INVALID, "reason": "{} is false".format(keys[0])}

    bureau_result = _first_present(
        request,
        "credit_bureau_result",
        "credit_bureau_status",
        "bureau_result",
        "bureau_status",
        "credit_report_result",
    )
    explicit_score = _first_present(
        request, "credit_score", "score", "credit_bureau_score", "bureau_score"
    )
    store_result = _first_present(
        request,
        "application_store_result",
        "application_store_status",
        "store_result",
        "store_status",
        "storage_result",
        "storage_status",
    )
    notification_result = _first_present(
        request,
        "notification_service_result",
        "notification_service_status",
        "notification_result",
        "notification_status",
    )

    options = {
        "credit_bureau_result": bureau_result,
        "credit_score": explicit_score,
        "application_store_result": store_result,
        "notification_result": notification_result,
        "customer_id": request.get("customer_id"),
    }

    applicant, _api, _store, _engine, _bureau, _notifier = build_system(options)

    payload = {
        "customer_id": request.get("customer_id"),
        "amount": request.get("amount"),
        "term_months": request.get("term_months"),
    }
    if request.get("application_id") is not None:
        payload["application_id"] = request["application_id"]

    try:
        return applicant.submit_loan_application(payload)
    except LoanCheckError as exc:
        return {"status": exc.status, "reason": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error: internal_error", "reason": str(exc)}
