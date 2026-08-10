class Applicant:
    """Person who applies for a loan."""

    def __init__(self, applicant_id="applicant", api=None):
        self.applicant_id = applicant_id
        self.api = api or OriginationApi()

    def apply(self, request):
        return self.api.submit_application(request)


class CreditBureau:
    """External system: provides credit scores."""

    def get_credit_score(self, applicant_id, result=None, score=None):
        if result == "error":
            raise RuntimeError("credit bureau error")
        if score is not None:
            return int(score)
        if result == "declined":
            return 500
        return 720


class NotificationService:
    """External system: sends notifications to applicants."""

    def notify(self, applicant_id, message):
        return {"delivered": True, "applicant_id": applicant_id, "message": message}


class ApplicationStore:
    """Container DB: persists loan applications."""

    def __init__(self):
        self._store = {}

    def save(self, application_id, data):
        self._store[application_id] = dict(data)
        return "stored"

    def get(self, application_id):
        return self._store.get(application_id)

    def update(self, application_id, data):
        if application_id not in self._store:
            raise KeyError("application not found")
        self._store[application_id].update(data)
        return "updated"


class DecisionEngine:
    """Container: evaluates loan applications using credit data."""

    MIN_SCORE = 640

    def __init__(self, credit_bureau=None):
        self.credit_bureau = credit_bureau or CreditBureau()

    def evaluate(self, applicant_id, amount, bureau_result=None, bureau_score=None):
        score = self.credit_bureau.get_credit_score(
            applicant_id, result=bureau_result, score=bureau_score
        )
        if score < self.MIN_SCORE:
            return {"decision": "declined", "score": score, "reason": "low_score"}
        if amount is not None and amount > 100000:
            return {"decision": "declined", "score": score, "reason": "amount_exceeds_limit"}
        return {"decision": "approved", "score": score}


class OriginationApi:
    """Container: entry point orchestrating origination flow."""

    def __init__(self, store=None, engine=None, notifications=None):
        self.store = store or ApplicationStore()
        self.engine = engine or DecisionEngine()
        self.notifications = notifications or NotificationService()

    def submit_application(self, request):
        applicant_id = request.get("applicant_id", "applicant")
        application_id = request.get("application_id", "app-1")
        amount = request.get("amount")

        if request.get("applicant_exists") is False:
            raise ValueError("applicant not found")

        # Validate the requested amount before doing any work.
        if amount is not None and amount <= 0:
            raise ValueError("invalid amount")

        # Persist the incoming application.
        self.store.save(
            application_id,
            {"applicant_id": applicant_id, "amount": amount, "status": "received"},
        )

        # Delegate decision to the engine.
        result = self.engine.evaluate(
            applicant_id,
            amount,
            bureau_result=request.get("credit_bureau_result"),
            bureau_score=request.get("credit_bureau_score"),
        )

        decision = result["decision"]
        outcome = "confirmed" if decision == "approved" else "rejected"

        self.store.update(application_id, {"status": decision, "score": result.get("score")})

        # Notify the applicant of the outcome.
        self.notifications.notify(
            applicant_id, "Your loan application was {}".format(decision)
        )

        return {
            "status": outcome,
            "decision": decision,
            "score": result.get("score"),
            "reason": result.get("reason"),
            "application_id": application_id,
        }


def handle(request: dict) -> dict:
    try:
        store = ApplicationStore()
        bureau = CreditBureau()
        engine = DecisionEngine(credit_bureau=bureau)
        notifications = NotificationService()
        api = OriginationApi(store=store, engine=engine, notifications=notifications)
        applicant = Applicant(
            applicant_id=request.get("applicant_id", "applicant"), api=api
        )
        return applicant.apply(request)
    except Exception as exc:
        return {"status": "error: {}".format(exc)}