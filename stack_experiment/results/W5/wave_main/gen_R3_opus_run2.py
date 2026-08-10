from typing import Optional


class ApplicationValidator:
    """Checks that a submitted application is complete and within product limits."""

    MIN_AMOUNT = 1000
    MAX_AMOUNT = 50000

    def validate(self, application: dict) -> None:
        applicant_id = application.get("applicant_id")
        if not applicant_id:
            raise ValueError("missing applicant_id")
        amount = application.get("amount")
        if amount is None:
            raise ValueError("missing amount")
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            raise ValueError("invalid amount")
        if amount < self.MIN_AMOUNT or amount > self.MAX_AMOUNT:
            raise ValueError("amount out of product limits")


class ApplicationStore:
    """Stores loan applications and their decision status (PostgreSQL 16)."""

    def __init__(self):
        self._records = {}

    def store_pending(self, application: dict, available: bool = True) -> str:
        if not available:
            raise RuntimeError("application store unavailable")
        app_id = application.get("application_id", application.get("applicant_id", "app"))
        self._records[app_id] = dict(application, status="pending")
        return app_id

    def update_status(self, app_id: str, status: str, available: bool = True) -> None:
        if not available:
            raise RuntimeError("application store unavailable")
        if app_id in self._records:
            self._records[app_id]["status"] = status


class CreditBureau:
    """External credit reference agency providing credit reports and scores."""

    def pull_report(self, applicant_id: str, status: str = "active",
                    score: Optional[int] = None) -> dict:
        if status in ("error", "unavailable", "down"):
            raise RuntimeError("credit bureau unavailable")
        if score is None:
            score = 720
        return {"applicant_id": applicant_id, "score": int(score)}


class BureauGateway:
    """Encapsulates the credit bureau integration and its failure modes."""

    def __init__(self, credit_bureau: CreditBureau):
        self.credit_bureau = credit_bureau

    def get_score(self, applicant_id: str, bureau_status: str = "active",
                  score: Optional[int] = None) -> int:
        try:
            report = self.credit_bureau.pull_report(applicant_id, bureau_status, score)
        except RuntimeError as exc:
            raise RuntimeError("bureau_unavailable") from exc
        return report["score"]


class ScoringPolicy:
    """Maps the applicant's credit score to a credit decision."""

    APPROVE_THRESHOLD = 700
    DECLINE_THRESHOLD = 580

    def __init__(self, bureau_gateway: BureauGateway):
        self.bureau_gateway = bureau_gateway

    def decide(self, applicant_id: str, bureau_status: str = "active",
               score: Optional[int] = None) -> str:
        credit_score = self.bureau_gateway.get_score(applicant_id, bureau_status, score)
        if credit_score >= self.APPROVE_THRESHOLD:
            return "approved"
        if credit_score < self.DECLINE_THRESHOLD:
            return "declined"
        return "review"


class DecisionEngine:
    """Determines the credit decision for a validated application."""

    def __init__(self, scoring_policy: ScoringPolicy):
        self.scoring_policy = scoring_policy

    def request_decision(self, application: dict, bureau_status: str = "active",
                         score: Optional[int] = None) -> str:
        return self.scoring_policy.decide(
            application.get("applicant_id"), bureau_status, score)


class NotificationService:
    """External messaging provider delivering e-mail and SMS notifications."""

    def send(self, applicant_id: str, message: str) -> dict:
        return {"delivered": True, "applicant_id": applicant_id, "message": message}


class ApplicationService:
    """Orchestrates the credit-check flow: validation, storage, decision, notification."""

    def __init__(self, validator: ApplicationValidator, store: ApplicationStore,
                 decision_engine: DecisionEngine, notification_service: NotificationService):
        self.validator = validator
        self.store = store
        self.decision_engine = decision_engine
        self.notification_service = notification_service

    def submit_application(self, application: dict) -> dict:
        # Step: validate
        try:
            self.validator.validate(application)
        except ValueError as exc:
            return {"status": "rejected", "reason": str(exc)}

        applicant_id = application.get("applicant_id")

        # Step: store as pending
        store_available = application.get("store_available", True)
        try:
            app_id = self.store.store_pending(application, store_available)
        except RuntimeError:
            return {"status": "error: storage_failure"}

        # Step: request credit decision
        bureau_status = application.get("bureau_status", "active")
        score = application.get("score")
        try:
            decision = self.decision_engine.request_decision(application, bureau_status, score)
        except RuntimeError:
            # bureau unavailable - stays pending, no notification
            return {"status": "error: bureau_unavailable"}

        # Step: update status and notify
        if decision == "approved":
            self.store.update_status(app_id, "approved", store_available)
            self.notification_service.send(applicant_id, "Your loan is approved")
            return {"status": "confirmed", "decision": "approved"}
        if decision == "declined":
            self.store.update_status(app_id, "declined", store_available)
            self.notification_service.send(applicant_id, "Your loan is declined")
            return {"status": "declined", "decision": "declined"}
        # review
        self.store.update_status(app_id, "under_manual_review", store_available)
        self.notification_service.send(applicant_id, "Your loan is under review")
        return {"status": "review", "decision": "review"}


def _build_service() -> ApplicationService:
    credit_bureau = CreditBureau()
    bureau_gateway = BureauGateway(credit_bureau)
    scoring_policy = ScoringPolicy(bureau_gateway)
    decision_engine = DecisionEngine(scoring_policy)
    validator = ApplicationValidator()
    store = ApplicationStore()
    notification_service = NotificationService()
    return ApplicationService(validator, store, decision_engine, notification_service)


def handle(request: dict) -> dict:
    service = _build_service()

    application = {
        "applicant_id": request.get("applicant_id", request.get("application_id")),
        "application_id": request.get("application_id", request.get("applicant_id")),
        "amount": request.get("amount", 5000),
    }

    # Storage availability
    store_result = request.get("application_store_result",
                               request.get("application_store_status"))
    if store_result in ("error", "unavailable", "down"):
        application["store_available"] = False
    else:
        application["store_available"] = request.get("store_available", True)

    # Bureau outcome
    bureau_result = request.get("credit_bureau_result", request.get("credit_bureau_status"))
    if bureau_result in ("error", "unavailable", "down", "lapsed"):
        application["bureau_status"] = "error"
    else:
        application["bureau_status"] = "active"

    # Credit score: from decision_engine_result or explicit score
    engine_result = request.get("decision_engine_result", request.get("decision_engine_status"))
    if request.get("score") is not None:
        application["score"] = request.get("score")
    elif request.get("credit_score") is not None:
        application["score"] = request.get("credit_score")
    elif engine_result == "approved":
        application["score"] = 750
    elif engine_result == "declined":
        application["score"] = 500
    elif engine_result in ("review", "borderline"):
        application["score"] = 640

    return service.submit_application(application)