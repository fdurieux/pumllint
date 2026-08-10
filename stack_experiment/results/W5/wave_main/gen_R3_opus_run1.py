class ApplicationValidator:
    """Checks that a submitted application is complete and within product limits."""

    MIN_AMOUNT = 1000
    MAX_AMOUNT = 50000
    REQUIRED_FIELDS = ("applicant_id", "amount")

    def validate(self, application: dict) -> None:
        if not application.get("applicant_exists", True):
            raise ValueError("unknown applicant")
        for field in self.REQUIRED_FIELDS:
            if application.get(field) in (None, ""):
                raise ValueError(f"missing field: {field}")
        amount = application.get("amount")
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

    def _check_available(self, application: dict) -> None:
        status = application.get("application_store_status")
        if status in ("error", "unavailable", "down"):
            raise ConnectionError("application store unavailable")

    def store_pending(self, application: dict) -> str:
        self._check_available(application)
        app_id = application.get("application_id", "app-1")
        record = dict(application)
        record["status"] = "pending"
        self._records[app_id] = record
        return app_id

    def update_status(self, app_id: str, status: str) -> None:
        if app_id in self._records:
            self._records[app_id]["status"] = status


class CreditBureau:
    """External credit reference agency providing credit reports and scores."""

    def pull_credit_report(self, request: dict) -> dict:
        status = request.get("credit_bureau_status")
        if status in ("error", "unavailable", "down"):
            raise ConnectionError("credit bureau unavailable")
        result = request.get("credit_bureau_result")
        score = None
        if isinstance(result, (int, float)):
            score = int(result)
        elif isinstance(result, str):
            if result.isdigit():
                score = int(result)
            elif result in ("error", "unavailable"):
                raise ConnectionError("credit bureau unavailable")
        if score is None:
            score = request.get("credit_score", 720)
        return {"score": int(score)}


class BureauGateway:
    """Encapsulates the credit bureau integration and its failure modes."""

    def __init__(self, credit_bureau: CreditBureau):
        self.credit_bureau = credit_bureau

    def get_score(self, request: dict) -> int:
        try:
            report = self.credit_bureau.pull_credit_report(request)
        except ConnectionError as exc:
            raise ConnectionError(f"bureau failure: {exc}")
        return report["score"]


class ScoringPolicy:
    """Maps the applicant's credit score to a credit decision."""

    APPROVE_THRESHOLD = 700
    DECLINE_THRESHOLD = 600

    def __init__(self, bureau_gateway: BureauGateway):
        self.bureau_gateway = bureau_gateway

    def decide(self, request: dict) -> dict:
        score = self.bureau_gateway.get_score(request)
        if score >= self.APPROVE_THRESHOLD:
            decision = "approve"
        elif score < self.DECLINE_THRESHOLD:
            decision = "decline"
        else:
            decision = "review"
        return {"decision": decision, "score": score}


class DecisionEngine:
    """Determines the credit decision for a validated application."""

    def __init__(self, scoring_policy: ScoringPolicy):
        self.scoring_policy = scoring_policy

    def request_decision(self, request: dict) -> dict:
        return self.scoring_policy.decide(request)


class NotificationService:
    """External messaging provider delivering e-mail and SMS notifications."""

    def send(self, applicant_id: str, kind: str) -> dict:
        return {"delivered": True, "applicant": applicant_id, "kind": kind}


class ApplicationService:
    """Orchestrates the credit-check flow: validation, storage, decision, notification."""

    _STATUS_MAP = {
        "approve": ("approved", "approval", "confirmed"),
        "decline": ("declined", "decline", "rejected"),
        "review": ("under_manual_review", "under-review", "review"),
    }

    def __init__(self, validator, store, decision_engine, notification_service):
        self.validator = validator
        self.store = store
        self.decision_engine = decision_engine
        self.notification_service = notification_service

    def submit_application(self, application: dict) -> dict:
        applicant_id = application.get("applicant_id", "unknown")

        # 1. Validate — invalid applications are rejected, no credit report pulled.
        try:
            self.validator.validate(application)
        except ValueError as exc:
            return {"status": "rejected", "reason": str(exc)}

        # 2. Store as pending — storage failure aborts the flow.
        try:
            app_id = self.store.store_pending(application)
        except ConnectionError as exc:
            return {"status": f"error: storage failure", "reason": str(exc)}

        # 3. Request credit decision — bureau failure leaves application pending.
        try:
            result = self.decision_engine.request_decision(application)
        except ConnectionError as exc:
            return {
                "status": "error: bureau unavailable",
                "reason": str(exc),
                "application_status": "pending",
            }

        decision = result["decision"]
        store_status, notif_kind, outcome = self._STATUS_MAP[decision]

        # 4. Update stored application status.
        self.store.update_status(app_id, store_status)

        # 5. Send notification.
        self.notification_service.send(applicant_id, notif_kind)

        # 6. Return response.
        return {
            "status": outcome,
            "decision": decision,
            "score": result.get("score"),
            "application_id": app_id,
        }


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
    application = dict(request)
    application.setdefault("application_id", request.get("application_id", "app-1"))
    return service.submit_application(application)