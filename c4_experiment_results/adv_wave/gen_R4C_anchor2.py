"""LoanCheck -- Personal Loan Origination System (credit-check scope).

Single self-contained module generated from the C4 model:

  * containers.puml         -- container-level structure
  * components_api.puml     -- Origination API internals
  * components_engine.puml  -- Decision Engine internals
  * dynamics.puml           -- approved / declined / review / invalid /
                               bureau-unavailable / storage-failure flows
  * spec.md                 -- decision semantics, validation, error policy

Class-per-element mapping
-------------------------
Containers / ContainerDb:
    OriginationApi      (Container origination_api)
    DecisionEngine      (Container decision_engine)
    ApplicationStore    (ContainerDb application_store)
System_Ext:
    CreditBureau        (System_Ext credit_bureau)
    NotificationService (System_Ext notification_service)
Components (each implements part of its container's responsibility):
    ApplicationService   + ApplicationValidator   -> OriginationApi
    ScoringPolicy        + BureauGateway          -> DecisionEngine
Person:
    Applicant           (drives the flow; calls OriginationApi)

Declared relationships (and only these) become method calls:
    applicant            -> application_service / origination_api
    application_service  -> application_validator
    application_service  -> application_store
    application_service  -> decision_engine (scoring_policy)
    application_service  -> notification_service
    scoring_policy       -> bureau_gateway
    bureau_gateway       -> credit_bureau
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

__all__ = [
    "LoanCheckError",
    "InvalidApplicationError",
    "StorageUnavailableError",
    "BureauUnavailableError",
    "Application",
    "Applicant",
    "ApplicationValidator",
    "ApplicationService",
    "OriginationApi",
    "ApplicationStore",
    "ScoringPolicy",
    "BureauGateway",
    "DecisionEngine",
    "CreditBureau",
    "NotificationService",
    "LoanCheckSystem",
    "handle",
]


# ---------------------------------------------------------------------------
# Decision / status vocabulary
# ---------------------------------------------------------------------------

DECISION_APPROVED = "approved"
DECISION_DECLINED = "declined"
DECISION_REVIEW = "review"

STATUS_PENDING = "pending"

STATUS_REJECTED_INVALID = "rejected: invalid_application"
STATUS_ERROR_BUREAU = "error: bureau_unavailable"
STATUS_ERROR_STORAGE = "error: storage_unavailable"

APPROVE_THRESHOLD = 700          # s >= 700            -> approved
REVIEW_THRESHOLD = 620           # 620 <= s <= 699     -> review
                                 # s < 620             -> declined

MIN_AMOUNT = 1
MAX_AMOUNT = 100000
MIN_TERM_MONTHS = 6
MAX_TERM_MONTHS = 120

_OK_WORDS = {
    "ok",
    "success",
    "successful",
    "up",
    "available",
    "active",
    "stored",
    "assessed",
    "scored",
    "sent",
    "delivered",
    "approved",
    "declined",
    "review",
}
_FAIL_WORDS = {
    "error",
    "fail",
    "failed",
    "failure",
    "unavailable",
    "down",
    "timeout",
    "offline",
    "lapsed",
    "inactive",
    "rejected",
}


def _is_failure(word: Any) -> bool:
    """Interpret a scenario '<system>_result' / '<system>_status' word."""
    if word is None:
        return False
    if isinstance(word, bool):
        return not word
    text = str(word).strip().lower()
    if text == "":
        return False
    if text in _FAIL_WORDS:
        return True
    if text in _OK_WORDS:
        return False
    # Unknown words are treated as non-failures (best-effort, be permissive).
    return False


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# ---------------------------------------------------------------------------
# Errors -- failure paths from the dynamic diagrams
# ---------------------------------------------------------------------------


class LoanCheckError(Exception):
    """Base class for all LoanCheck failures."""

    status = "error: unknown"


class InvalidApplicationError(LoanCheckError):
    """Application failed the validation rules; nothing downstream happens."""

    status = STATUS_REJECTED_INVALID

    def __init__(self, reason: str = "invalid_application") -> None:
        super().__init__(reason)
        self.reason = reason


class StorageUnavailableError(LoanCheckError):
    """Application Store could not persist / update the application."""

    status = STATUS_ERROR_STORAGE


class BureauUnavailableError(LoanCheckError):
    """Credit Bureau could not return a report / score."""

    status = STATUS_ERROR_BUREAU


# ---------------------------------------------------------------------------
# Application record
# ---------------------------------------------------------------------------


class Application:
    """One request for a personal loan (see spec.md glossary)."""

    def __init__(
        self,
        customer_id: Any,
        amount: Any,
        term_months: Any,
        application_id: Optional[str] = None,
    ) -> None:
        self.application_id = application_id
        self.customer_id = customer_id
        self.amount = amount
        self.term_months = term_months
        self.status = STATUS_PENDING
        self.credit_score: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "application_id": self.application_id,
            "customer_id": self.customer_id,
            "amount": self.amount,
            "term_months": self.term_months,
            "status": self.status,
            "credit_score": self.credit_score,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return "Application(%r, status=%r)" % (self.application_id, self.status)


# ---------------------------------------------------------------------------
# System_Ext: Credit Bureau
# ---------------------------------------------------------------------------


class CreditBureau:
    """External credit reference agency (outside the system boundary).

    Provides consumer credit reports and scores over XML/HTTPS.  As an
    external system this is a simple stub returning plausible values; the
    scenario may pin its behaviour via 'credit_bureau_result' /
    'credit_bureau_status' and 'credit_score'.
    """

    DEFAULT_SCORE = 720

    def __init__(
        self,
        score: Optional[int] = None,
        result: Any = None,
        available: bool = True,
    ) -> None:
        self._score = score
        self._result = result
        self._available = available

    def pull_credit_report(self, customer_id: Any) -> Dict[str, Any]:
        """Pull the credit report and score for a customer.

        Raises BureauUnavailableError when the bureau is down or errors.
        """
        if not self._available or _is_failure(self._result):
            raise BureauUnavailableError("credit bureau unavailable")

        score = self._score
        if score is None and _is_number(self._result):
            score = self._result
        if score is None:
            score = self.DEFAULT_SCORE
        try:
            score = int(score)
        except (TypeError, ValueError):
            raise BureauUnavailableError("credit bureau returned an unusable score")

        return {
            "customer_id": customer_id,
            "score": score,
            "report_id": "cb-" + uuid.uuid4().hex[:12],
            "bureau": "credit_bureau",
        }


# ---------------------------------------------------------------------------
# System_Ext: Notification Service
# ---------------------------------------------------------------------------


class NotificationService:
    """External messaging provider delivering e-mail and SMS notifications."""

    def __init__(self, result: Any = None, available: bool = True) -> None:
        self._result = result
        self._available = available
        self.sent: list = []

    def send_notification(
        self,
        customer_id: Any,
        decision: str,
        application_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Deliver a decision notification; returns a plausible receipt.

        Notification delivery is best-effort: a failure here does not undo a
        decision that was already made and stored.
        """
        message = {
            DECISION_APPROVED: "Your loan application has been approved.",
            DECISION_DECLINED: "Your loan application has been declined.",
            DECISION_REVIEW: "Your loan application is under manual review.",
        }.get(decision, "Your loan application has been updated.")

        if not self._available or _is_failure(self._result):
            return {
                "delivered": False,
                "channel": "email",
                "customer_id": customer_id,
                "application_id": application_id,
                "decision": decision,
                "error": "notification_service_unavailable",
            }

        receipt = {
            "delivered": True,
            "channel": "email",
            "customer_id": customer_id,
            "application_id": application_id,
            "decision": decision,
            "message": message,
            "notification_id": "ntf-" + uuid.uuid4().hex[:12],
        }
        self.sent.append(receipt)
        return receipt


# ---------------------------------------------------------------------------
# ContainerDb: Application Store
# ---------------------------------------------------------------------------


class ApplicationStore:
    """PostgreSQL 16 -- stores loan applications and their decision status."""

    def __init__(self, result: Any = None, available: bool = True) -> None:
        self._result = result
        self._available = available
        self._records: Dict[str, Dict[str, Any]] = {}

    # -- internal ---------------------------------------------------------
    def _check_available(self) -> None:
        if not self._available or _is_failure(self._result):
            raise StorageUnavailableError("application store unavailable")

    # -- API used by the Origination API ----------------------------------
    def store_application(self, application: Application) -> str:
        """Insert the application with status 'pending'; returns its id."""
        self._check_available()
        application_id = application.application_id or ("app-" + uuid.uuid4().hex[:12])
        application.application_id = application_id
        application.status = STATUS_PENDING
        self._records[application_id] = application.to_dict()
        return application_id

    def update_status(
        self,
        application_id: str,
        status: str,
        credit_score: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Update a stored application to its decision status."""
        self._check_available()
        record = self._records.get(application_id)
        if record is None:
            raise StorageUnavailableError("application %r not found" % (application_id,))
        record["status"] = status
        if credit_score is not None:
            record["credit_score"] = credit_score
        return dict(record)

    def get_application(self, application_id: str) -> Optional[Dict[str, Any]]:
        self._check_available()
        record = self._records.get(application_id)
        return dict(record) if record is not None else None


# ---------------------------------------------------------------------------
# Component: Bureau Gateway (Decision Engine)
# ---------------------------------------------------------------------------


class BureauGateway:
    """Encapsulates the Credit Bureau integration and its failure modes."""

    def __init__(self, credit_bureau: CreditBureau) -> None:
        self.credit_bureau = credit_bureau

    def fetch_score(self, customer_id: Any) -> int:
        """Pull the applicant's credit score from the Credit Bureau.

        Any bureau problem surfaces as BureauUnavailableError -- the engine
        makes no decision in that case (dynamics: bureau unavailable).
        """
        try:
            report = self.credit_bureau.pull_credit_report(customer_id)
        except BureauUnavailableError:
            raise
        except Exception as exc:  # any integration failure is a bureau failure
            raise BureauUnavailableError(str(exc) or "credit bureau error")

        if not isinstance(report, dict) or "score" not in report:
            raise BureauUnavailableError("credit bureau returned no score")
        score = report["score"]
        if not _is_number(score):
            raise BureauUnavailableError("credit bureau returned a non-numeric score")
        return int(score)


# ---------------------------------------------------------------------------
# Component: Scoring Policy (Decision Engine)
# ---------------------------------------------------------------------------


class ScoringPolicy:
    """Maps the applicant's credit score to a credit decision.

        s >= 700         -> approved
        620 <= s <= 699  -> review
        s < 620          -> declined
    """

    approve_threshold = APPROVE_THRESHOLD
    review_threshold = REVIEW_THRESHOLD

    def __init__(self, bureau_gateway: BureauGateway) -> None:
        self.bureau_gateway = bureau_gateway

    def decide(self, customer_id: Any, amount: Any = None, term_months: Any = None) -> Dict[str, Any]:
        """Obtain the score via the Bureau Gateway and apply the policy."""
        score = self.bureau_gateway.fetch_score(customer_id)
        return {"decision": self.classify(score), "score": score}

    def classify(self, score: int) -> str:
        if score >= self.approve_threshold:
            return DECISION_APPROVED
        if score >= self.review_threshold:
            return DECISION_REVIEW
        return DECISION_DECLINED


# ---------------------------------------------------------------------------
# Container: Decision Engine
# ---------------------------------------------------------------------------


class DecisionEngine:
    """Determines the credit decision for a validated application.

    Composed of its components: ScoringPolicy (which calls BureauGateway,
    which calls the Credit Bureau).
    """

    def __init__(self, credit_bureau: CreditBureau) -> None:
        self.bureau_gateway = BureauGateway(credit_bureau)
        self.scoring_policy = ScoringPolicy(self.bureau_gateway)

    def request_decision(self, application: Application) -> Dict[str, Any]:
        """Entry point called by the Origination API over JSON/HTTPS."""
        return self.scoring_policy.decide(
            application.customer_id,
            application.amount,
            application.term_months,
        )


# ---------------------------------------------------------------------------
# Component: Application Validator (Origination API)
# ---------------------------------------------------------------------------


class ApplicationValidator:
    """Checks that an application is complete and within product limits."""

    min_amount = MIN_AMOUNT
    max_amount = MAX_AMOUNT
    min_term_months = MIN_TERM_MONTHS
    max_term_months = MAX_TERM_MONTHS

    def validate(self, application: Application) -> None:
        """Raise InvalidApplicationError if the application is not valid."""
        customer_id = application.customer_id
        if customer_id is None:
            raise InvalidApplicationError("customer_id missing")
        if not isinstance(customer_id, str):
            raise InvalidApplicationError("customer_id must be a string")
        if customer_id.strip() == "":
            raise InvalidApplicationError("customer_id empty")

        amount = application.amount
        if amount is None:
            raise InvalidApplicationError("amount missing")
        if not _is_number(amount):
            raise InvalidApplicationError("amount must be a number")
        if not (self.min_amount <= amount <= self.max_amount):
            raise InvalidApplicationError("amount out of product limits")

        term = application.term_months
        if term is None:
            raise InvalidApplicationError("term_months missing")
        if not _is_number(term):
            raise InvalidApplicationError("term_months must be a number")
        if not (self.min_term_months <= term <= self.max_term_months):
            raise InvalidApplicationError("term_months out of product limits")

    def is_valid(self, application: Application) -> bool:
        try:
            self.validate(application)
        except InvalidApplicationError:
            return False
        return True


# ---------------------------------------------------------------------------
# Component: Application Service (Origination API)
# ---------------------------------------------------------------------------


class ApplicationService:
    """Orchestrates the credit-check flow.

    Flow order (spec.md 'Flow order and error policy'):
      1. validate            -> reject and stop when invalid (no bureau call,
                                no notification)
      2. store as pending    -> 'error: storage_unavailable' on failure
      3. request decision    -> 'error: bureau_unavailable' on failure, the
                                application stays pending, no notification
      4. update stored application to the decision
      5. send the decision notification
      6. return the response
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

    def submit_application(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        application = Application(
            customer_id=payload.get("customer_id"),
            amount=payload.get("amount"),
            term_months=payload.get("term_months"),
            application_id=payload.get("application_id"),
        )

        # 1 -- validation (Rel: application_service -> application_validator)
        try:
            self.application_validator.validate(application)
        except InvalidApplicationError as exc:
            return {
                "status": STATUS_REJECTED_INVALID,
                "reason": exc.reason,
                "notification_sent": False,
                "bureau_called": False,
            }

        # 2 -- store as pending (Rel: application_service -> application_store)
        try:
            application_id = self.application_store.store_application(application)
        except StorageUnavailableError:
            return {
                "status": STATUS_ERROR_STORAGE,
                "reason": "storage_unavailable",
                "notification_sent": False,
                "bureau_called": False,
            }

        # 3 -- decision (Rel: application_service -> decision_engine)
        try:
            outcome = self.decision_engine.request_decision(application)
        except BureauUnavailableError:
            return {
                "status": STATUS_ERROR_BUREAU,
                "application_id": application_id,
                "reason": "bureau_unavailable",
                "application_status": STATUS_PENDING,
                "notification_sent": False,
                "bureau_called": True,
            }

        decision = outcome["decision"]
        score = outcome.get("score")
        application.credit_score = score
        application.status = decision

        # 4 -- update the stored application to the decision
        try:
            self.application_store.update_status(application_id, decision, score)
        except StorageUnavailableError:
            return {
                "status": STATUS_ERROR_STORAGE,
                "application_id": application_id,
                "reason": "storage_unavailable",
                "notification_sent": False,
                "bureau_called": True,
            }

        # 5 -- decision notification (Rel: application_service -> notification_service)
        receipt = self.notification_service.send_notification(
            application.customer_id, decision, application_id
        )
        notification_sent = bool(receipt.get("delivered", True))

        # 6 -- response to the applicant
        return {
            "status": decision,
            "application_id": application_id,
            "credit_score": score,
            "notification_sent": notification_sent,
            "bureau_called": True,
        }


# ---------------------------------------------------------------------------
# Container: Origination API
# ---------------------------------------------------------------------------


class OriginationApi:
    """Python 3.12 / FastAPI -- the system's entry point for applicants.

    Composed of its components: ApplicationService and ApplicationValidator.
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

    def submit_application(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /applications -- JSON/HTTPS."""
        return self.application_service.submit_application(payload)


# ---------------------------------------------------------------------------
# Person: Loan Applicant
# ---------------------------------------------------------------------------


class Applicant:
    """A retail customer applying for a personal loan."""

    def __init__(self, origination_api: OriginationApi) -> None:
        self.origination_api = origination_api

    def submit_loan_application(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Submits the loan application to the Origination API."""
        return self.origination_api.submit_application(payload)


# ---------------------------------------------------------------------------
# System assembly
# ---------------------------------------------------------------------------


class LoanCheckSystem:
    """Wires the containers and external systems together for one scenario."""

    def __init__(
        self,
        credit_bureau: Optional[CreditBureau] = None,
        notification_service: Optional[NotificationService] = None,
        application_store: Optional[ApplicationStore] = None,
    ) -> None:
        self.credit_bureau = credit_bureau or CreditBureau()
        self.notification_service = notification_service or NotificationService()
        self.application_store = application_store or ApplicationStore()
        self.decision_engine = DecisionEngine(self.credit_bureau)
        self.origination_api = OriginationApi(
            self.application_store, self.decision_engine, self.notification_service
        )
        self.applicant = Applicant(self.origination_api)

    def submit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.applicant.submit_loan_application(payload)


# ---------------------------------------------------------------------------
# Scenario wiring for handle()
# ---------------------------------------------------------------------------


def _first_present(request: Dict[str, Any], *keys: str) -> Any:
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
            text = str(value).strip().lower()
            if text in ("true", "yes", "1", "found", "present", "exists"):
                return True
            if text in ("false", "no", "0", "missing", "absent", "not_found"):
                return False
    return None


def _extract_score(request: Dict[str, Any]) -> Optional[int]:
    candidate = _first_present(
        request,
        "credit_score",
        "score",
        "credit_bureau_score",
        "bureau_score",
        "credit_bureau_result",
        "credit_bureau_status",
        "bureau_result",
        "bureau_status",
        "scoring_policy_result",
    )
    if _is_number(candidate):
        return int(candidate)
    if isinstance(candidate, str):
        text = candidate.strip()
        try:
            return int(float(text))
        except ValueError:
            return None
    return None


def _build_system(request: Dict[str, Any]) -> LoanCheckSystem:
    # --- Credit Bureau ---------------------------------------------------
    bureau_word = _first_present(
        request,
        "credit_bureau_result",
        "credit_bureau_status",
        "bureau_result",
        "bureau_status",
    )
    bureau_available = _exists_flag(
        request,
        "credit_bureau_available",
        "credit_bureau_exists",
        "credit_bureau_found",
        "bureau_available",
        "bureau_exists",
        "bureau_found",
    )
    bureau_failed = _is_failure(bureau_word) and not _is_number(bureau_word)
    if bureau_available is None:
        bureau_available = True
    credit_bureau = CreditBureau(
        score=_extract_score(request),
        result=None if _is_number(bureau_word) else bureau_word,
        available=bool(bureau_available) and not bureau_failed,
    )

    # --- Application Store -----------------------------------------------
    store_word = _first_present(
        request,
        "application_store_result",
        "application_store_status",
        "store_result",
        "store_status",
        "storage_result",
        "storage_status",
    )
    store_available = _exists_flag(
        request,
        "application_store_available",
        "application_store_exists",
        "application_store_found",
        "store_available",
        "store_exists",
        "storage_available",
    )
    if store_available is None:
        store_available = True
    application_store = ApplicationStore(
        result=store_word, available=bool(store_available)
    )

    # --- Notification Service --------------------------------------------
    notify_word = _first_present(
        request,
        "notification_service_result",
        "notification_service_status",
        "notification_result",
        "notification_status",
    )
    notify_available = _exists_flag(
        request,
        "notification_service_available",
        "notification_service_exists",
        "notification_service_found",
        "notification_available",
    )
    if notify_available is None:
        notify_available = True
    notification_service = NotificationService(
        result=notify_word, available=bool(notify_available)
    )

    return LoanCheckSystem(
        credit_bureau=credit_bureau,
        notification_service=notification_service,
        application_store=application_store,
    )


def handle(request: dict) -> dict:
    """Run one end-to-end credit-check flow.

    Request keys: 'customer_id', 'amount', 'term_months', plus optional
    scenario controls such as 'credit_score' / 'credit_bureau_result',
    'application_store_result', 'notification_service_result' and
    '<entity>_exists' / '<entity>_found' flags.

    Returns a dict whose 'status' is one of:
        'approved' | 'declined' | 'review'
        'rejected: invalid_application'
        'error: bureau_unavailable'
        'error: storage_unavailable'
        'error: <reason>'
    plus 'application_id' when the application was stored.
    """
    if not isinstance(request, dict):
        return {"status": "error: invalid_request"}

    # The applicant themselves must exist for a submission to happen.
    applicant_exists = _exists_flag(
        request, "applicant_exists", "applicant_found", "customer_exists", "customer_found"
    )
    if applicant_exists is False:
        return {
            "status": STATUS_REJECTED_INVALID,
            "reason": "applicant_not_found",
            "notification_sent": False,
            "bureau_called": False,
        }

    payload = {
        "customer_id": _first_present(request, "customer_id", "applicant_id", "customer"),
        "amount": _first_present(request, "amount", "loan_amount", "principal"),
        "term_months": _first_present(request, "term_months", "term", "months"),
        "application_id": _first_present(request, "application_id"),
    }

    try:
        system = _build_system(request)
        return system.submit(payload)
    except LoanCheckError as exc:
        return {"status": exc.status, "reason": str(exc), "notification_sent": False}
    except Exception as exc:  # defensive: never leak an unhandled exception
        return {"status": "error: %s" % (type(exc).__name__.lower(),), "reason": str(exc)}


if __name__ == "__main__":  # pragma: no cover - manual smoke check
    scenarios = [
        {"customer_id": "c-1", "amount": 5000, "term_months": 36, "credit_score": 760},
        {"customer_id": "c-2", "amount": 5000, "term_months": 36, "credit_score": 700},
        {"customer_id": "c-3", "amount": 5000, "term_months": 36, "credit_score": 540},
        {"customer_id": "c-4", "amount": 5000, "term_months": 36, "credit_score": 660},
        {"customer_id": "c-5", "amount": 0, "term_months": 36, "credit_score": 760},
        {"customer_id": "c-6", "amount": 250000, "term_months": 36, "credit_score": 760},
        {"customer_id": "c-7", "amount": 5000, "term_months": 36, "credit_bureau_result": "error"},
        {"customer_id": "c-8", "amount": 5000, "term_months": 36, "application_store_result": "error"},
    ]
    for index, scenario in enumerate(scenarios, start=1):
        print(index, handle(scenario))
