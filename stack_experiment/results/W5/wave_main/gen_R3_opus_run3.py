class CreditBureau:
    """External credit reference agency (System_Ext)."""

    def pull_credit_report(self, request):
        status = request.get("credit_bureau_status", request.get("credit_bureau_result"))
        if status in ("error", "unavailable", "down", "timeout"):
            raise RuntimeError("credit bureau unavailable")
        score = request.get("credit_bureau_score", request.get("credit_score"))
        if score is None:
            score = request.get("credit_bureau_result")
        try:
            return {"score": int(score)}
        except (TypeError, ValueError):
            return {"score": 720}


class NotificationService:
    """External messaging provider (System_Ext)."""

    def send(self, kind, application_id):
        return {"status": "sent", "kind": kind, "application_id": application_id}


class ApplicationStore:
    """Stores loan applications and their decision status (ContainerDb)."""

    def __init__(self):
        self._records = {}

    def _check_available(self, request):
        status = request.get("application_store_status", request.get("application_store_result"))
        if status in ("error", "unavailable", "down"):
            raise RuntimeError("application store unavailable")

    def store_pending(self, application_id, request):
        self._check_available(request)
        self._records[application_id] = {"status": "pending", "data": request}
        return True

    def update_status(self, application_id, status, request):
        self._check_available(request)
        if application_id in self._records:
            self._records[application_id]["status"] = status
        return True


class BureauGateway:
    """Encapsulates the credit bureau integration and its failure modes (Component)."""

    def __init__(self, credit_bureau):
        self._credit_bureau = credit_bureau

    def get_score(self, request):
        report = self._credit_bureau.pull_credit_report(request)
        score = report.get("score")
        if score is None:
            raise RuntimeError("no score returned")
        return score


class ScoringPolicy:
    """Maps the applicant's credit score to a credit decision (Component)."""

    APPROVE_THRESHOLD = 700
    DECLINE_THRESHOLD = 600

    def __init__(self, bureau_gateway):
        self._bureau_gateway = bureau_gateway

    def decide(self, request):
        score = self._bureau_gateway.get_score(request)
        if score >= self.APPROVE_THRESHOLD:
            return {"decision": "approve", "score": score}
        if score < self.DECLINE_THRESHOLD:
            return {"decision": "decline", "score": score}
        return {"decision": "review", "score": score}


class DecisionEngine:
    """Determines the credit decision for a validated application (Container)."""

    def __init__(self, scoring_policy):
        self._scoring_policy = scoring_policy

    def request_decision(self, request):
        return self._scoring_policy.decide(request)


class ApplicationValidator:
    """Checks that a submitted application is complete and within product limits (Component)."""

    MIN_AMOUNT = 1000
    MAX_AMOUNT = 50000

    def validate(self, request):
        if request.get("application_exists") is False:
            return False, "application missing"
        applicant_id = request.get("applicant_id")
        if not applicant_id:
            return False, "missing applicant"
        amount = request.get("amount")
        if amount is None:
            return False, "missing amount"
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return False, "invalid amount"
        if amount < self.MIN_AMOUNT or amount > self.MAX_AMOUNT:
            return False, "amount out of product limits"
        return True, "valid"


class ApplicationService:
    """Orchestrates the credit-check flow (Component)."""

    def __init__(self, validator, store, decision_engine, notification_service):
        self._validator = validator
        self._store = store
        self._decision_engine = decision_engine
        self._notification_service = notification_service

    def submit_application(self, request):
        application_id = request.get("application_id", "app-unknown")

        # Step: validate
        valid, reason = self._validator.validate(request)
        if not valid:
            return {"status": "rejected", "reason": reason, "application_id": application_id}

        # Step: store as pending
        try:
            self._store.store_pending(application_id, request)
        except Exception as exc:
            return {"status": "error: storage_failure", "reason": str(exc),
                    "application_id": application_id}

        # Step: request credit decision
        try:
            result = self._decision_engine.request_decision(request)
        except Exception as exc:
            # Bureau failure: application stays pending, no notification
            return {"status": "error: bureau_unavailable", "reason": str(exc),
                    "application_id": application_id}

        decision = result["decision"]
        if decision == "approve":
            final_status, kind = "approved", "approval"
        elif decision == "decline":
            final_status, kind = "declined", "decline"
        else:
            final_status, kind = "under_manual_review", "under-review"

        # Step: update store
        try:
            self._store.update_status(application_id, final_status, request)
        except Exception as exc:
            return {"status": "error: storage_failure", "reason": str(exc),
                    "application_id": application_id}

        # Step: notify
        self._notification_service.send(kind, application_id)

        return {"status": final_status, "score": result.get("score"),
                "application_id": application_id}


class OriginationApi:
    """Receives loan applications and orchestrates the credit decision (Container)."""

    def __init__(self):
        self.credit_bureau = CreditBureau()
        self.notification_service = NotificationService()
        self.application_store = ApplicationStore()
        bureau_gateway = BureauGateway(self.credit_bureau)
        scoring_policy = ScoringPolicy(bureau_gateway)
        self.decision_engine = DecisionEngine(scoring_policy)
        self.application_service = ApplicationService(
            ApplicationValidator(),
            self.application_store,
            self.decision_engine,
            self.notification_service,
        )

    def submit(self, request):
        return self.application_service.submit_application(request)


def handle(request: dict) -> dict:
    api = OriginationApi()
    try:
        return api.submit(request)
    except Exception as exc:
        return {"status": "error: %s" % exc}