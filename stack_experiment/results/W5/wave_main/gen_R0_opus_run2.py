class CreditBureau:
    """External system: Credit Bureau."""

    def get_credit_score(self, applicant_id, result=None, score=None):
        if result == "error":
            raise RuntimeError("credit bureau unavailable")
        if score is not None:
            try:
                return int(score)
            except (TypeError, ValueError):
                pass
        if result == "declined":
            return 500
        return 720


class NotificationService:
    """External system: Notifications."""

    def send(self, applicant_id, message, result=None):
        if result == "error":
            raise RuntimeError("notification service unavailable")
        return {"delivered": True, "message": message}


class ApplicationStore:
    """ContainerDb: DB storing loan applications."""

    def __init__(self):
        self._data = {}

    def save(self, application_id, record, result=None):
        if result == "error":
            raise RuntimeError("application store error")
        self._data[application_id] = record
        return "stored"

    def get(self, application_id):
        return self._data.get(application_id)

    def update_status(self, application_id, status):
        if application_id in self._data:
            self._data[application_id]["status"] = status
            return True
        return False


class DecisionEngine:
    """Container: Engine that makes loan decisions using the Credit Bureau."""

    APPROVAL_THRESHOLD = 640

    def __init__(self, credit_bureau):
        self.credit_bureau = credit_bureau

    def evaluate(self, applicant_id, amount, request):
        engine_status = request.get("decision_engine_result") or request.get(
            "decision_engine_status"
        )
        if engine_status == "error":
            raise RuntimeError("decision engine failure")

        score = self.credit_bureau.get_credit_score(
            applicant_id,
            result=request.get("credit_bureau_result")
            or request.get("credit_bureau_status"),
            score=request.get("credit_bureau_score"),
        )

        if engine_status == "approved":
            return {"decision": "approved", "score": score}
        if engine_status == "declined":
            return {"decision": "declined", "score": score}

        if score >= self.APPROVAL_THRESHOLD:
            return {"decision": "approved", "score": score}
        return {"decision": "declined", "score": score}


class OriginationApi:
    """Container: API — entry point used by the Applicant."""

    def __init__(self, application_store, decision_engine, notification_service):
        self.application_store = application_store
        self.decision_engine = decision_engine
        self.notification_service = notification_service

    def submit_application(self, request):
        applicant_id = request.get("applicant_id")
        if not applicant_id or not request.get("applicant_exists", True):
            raise ValueError("applicant not found")

        application_id = request.get("application_id", "app-1")
        amount = request.get("amount", 0)

        try:
            amount_value = float(amount)
        except (TypeError, ValueError):
            raise ValueError("invalid amount")
        if amount_value <= 0:
            raise ValueError("invalid amount")

        record = {
            "application_id": application_id,
            "applicant_id": applicant_id,
            "amount": amount,
            "status": "received",
        }
        self.application_store.save(
            application_id,
            record,
            result=request.get("application_store_result")
            or request.get("application_store_status"),
        )

        decision = self.decision_engine.evaluate(applicant_id, amount, request)

        outcome = "confirmed" if decision["decision"] == "approved" else "rejected"
        self.application_store.update_status(application_id, decision["decision"])

        self.notification_service.send(
            applicant_id,
            "Your loan application was %s" % decision["decision"],
            result=request.get("notification_service_result")
            or request.get("notification_service_status"),
        )

        return {
            "status": outcome,
            "decision": decision["decision"],
            "score": decision["score"],
            "application_id": application_id,
        }


class Applicant:
    """Person: Applicant who uses the API."""

    def __init__(self, origination_api):
        self.origination_api = origination_api

    def apply(self, request):
        return self.origination_api.submit_application(request)


def handle(request: dict) -> dict:
    credit_bureau = CreditBureau()
    notification_service = NotificationService()
    application_store = ApplicationStore()
    decision_engine = DecisionEngine(credit_bureau)
    origination_api = OriginationApi(
        application_store, decision_engine, notification_service
    )
    applicant = Applicant(origination_api)

    try:
        return applicant.apply(request)
    except Exception as exc:
        return {"status": "error: %s" % str(exc)}