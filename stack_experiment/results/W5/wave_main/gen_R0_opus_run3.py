class CreditBureau:
    """External system: Credit Bureau."""

    def get_credit_score(self, applicant_id, request=None):
        request = request or {}
        status = request.get("credit_bureau_status") or request.get("credit_bureau_result")
        if status == "error":
            raise RuntimeError("credit bureau unavailable")
        score = request.get("credit_bureau_score")
        if score is not None:
            return int(score)
        if status == "declined":
            return 500
        return 720


class NotificationService:
    """External system: Notifications."""

    def send(self, applicant_id, message, request=None):
        request = request or {}
        status = request.get("notification_service_status") or request.get("notification_service_result")
        if status == "error":
            raise RuntimeError("notification service unavailable")
        return {"delivered": True, "message": message}


class ApplicationStore:
    """ContainerDb: DB for loan applications."""

    def __init__(self):
        self._applications = {}

    def save(self, application_id, data, request=None):
        request = request or {}
        status = request.get("application_store_status") or request.get("application_store_result")
        if status == "error":
            raise RuntimeError("database error")
        self._applications[application_id] = data
        return True

    def get(self, application_id):
        return self._applications.get(application_id)

    def update_status(self, application_id, new_status):
        if application_id not in self._applications:
            raise KeyError("application not found")
        self._applications[application_id]["status"] = new_status
        return True


class DecisionEngine:
    """Container: Engine. Evaluates loan applications using credit data."""

    APPROVAL_THRESHOLD = 650

    def __init__(self, credit_bureau):
        self.credit_bureau = credit_bureau

    def evaluate(self, applicant_id, amount, request=None):
        request = request or {}
        score = self.credit_bureau.get_credit_score(applicant_id, request)

        explicit = request.get("decision_engine_result") or request.get("decision_engine_status")
        if explicit in ("approved", "declined"):
            return {"decision": explicit, "score": score}

        if score >= self.APPROVAL_THRESHOLD:
            return {"decision": "approved", "score": score}
        return {"decision": "declined", "score": score}


class OriginationApi:
    """Container: API. Orchestrates the loan origination flow."""

    def __init__(self, application_store, decision_engine, notification_service):
        self.application_store = application_store
        self.decision_engine = decision_engine
        self.notification_service = notification_service

    def submit_application(self, applicant_id, application_id, amount, request=None):
        request = request or {}

        if not applicant_id or not application_id:
            raise ValueError("missing applicant or application id")
        if amount is None or amount <= 0:
            raise ValueError("invalid loan amount")

        # Persist the incoming application
        self.application_store.save(
            application_id,
            {"applicant_id": applicant_id, "amount": amount, "status": "received"},
            request,
        )

        # Ask the decision engine to evaluate
        result = self.decision_engine.evaluate(applicant_id, amount, request)
        decision = result["decision"]

        if decision == "approved":
            self.application_store.update_status(application_id, "approved")
            self.notification_service.send(
                applicant_id, "Your loan has been approved.", request
            )
            return {"status": "confirmed", "decision": decision, "score": result["score"]}
        else:
            self.application_store.update_status(application_id, "declined")
            self.notification_service.send(
                applicant_id, "Your loan has been declined.", request
            )
            return {"status": "rejected", "decision": decision, "score": result["score"]}


class Applicant:
    """Person: Applicant who uses the API."""

    def __init__(self, origination_api):
        self.origination_api = origination_api

    def apply(self, applicant_id, application_id, amount, request=None):
        return self.origination_api.submit_application(
            applicant_id, application_id, amount, request
        )


def handle(request: dict) -> dict:
    request = request or {}

    credit_bureau = CreditBureau()
    notification_service = NotificationService()
    application_store = ApplicationStore()
    decision_engine = DecisionEngine(credit_bureau)
    origination_api = OriginationApi(application_store, decision_engine, notification_service)
    applicant = Applicant(origination_api)

    applicant_id = request.get("applicant_id", "applicant-1")
    application_id = request.get("application_id", "application-1")
    amount = request.get("amount", 1000)

    try:
        if request.get("applicant_exists") is False:
            return {"status": "error: applicant not found"}

        return applicant.apply(applicant_id, application_id, amount, request)
    except Exception as exc:
        return {"status": "error: {}".format(exc)}