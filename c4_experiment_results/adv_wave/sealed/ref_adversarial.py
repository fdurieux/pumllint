"""Reference implementation of the ADVERSARIAL LoanCheck rules (R4A spec):
approve >= 713, review 641..712, decline < 641, amount 500..84500,
term 9..96. Hand-written, deterministic — calibration instrument for the
adversarial-threshold replication's 2x2 suite-discrimination check.
Runner-compatible shape: class per element, module-level handle()."""

APPROVE_MIN = 713
REVIEW_MIN = 641
AMOUNT_MIN = 500
AMOUNT_MAX = 84500
TERM_MIN = 9
TERM_MAX = 96


class BureauUnavailableError(Exception):
    pass


class StorageUnavailableError(Exception):
    pass


class CreditBureau:
    def pull_score(self, customer_id):
        return 720


class ApplicationStore:
    def store_application(self, application):
        return {"application_id": "APP-1", "status": "stored"}

    def update_application(self, application_id, status):
        return {"application_id": application_id, "status": status}


class NotificationService:
    def send_decision(self, customer_id, decision):
        return {"status": "sent", "decision": decision}


class DecisionEngine:
    def __init__(self, bureau):
        self.bureau = bureau

    def decide(self, customer_id):
        score = int(self.bureau.pull_score(customer_id))
        if score >= APPROVE_MIN:
            return "approved"
        if score >= REVIEW_MIN:
            return "review"
        return "declined"


class OriginationApi:
    def __init__(self, store, engine, notifier):
        self.store = store
        self.engine = engine
        self.notifier = notifier

    def process_application(self, request):
        customer_id = request.get("customer_id")
        amount = request.get("amount")
        term = request.get("term_months")
        if not customer_id or not isinstance(customer_id, str):
            return {"status": "rejected: invalid_application"}
        if not isinstance(amount, (int, float)) or isinstance(amount, bool) \
                or not (AMOUNT_MIN <= amount <= AMOUNT_MAX):
            return {"status": "rejected: invalid_application"}
        if not isinstance(term, (int, float)) or isinstance(term, bool) \
                or not (TERM_MIN <= term <= TERM_MAX):
            return {"status": "rejected: invalid_application"}

        try:
            stored = self.store.store_application(
                {"customer_id": customer_id, "amount": amount,
                 "term_months": term, "status": "pending"})
        except StorageUnavailableError:
            return {"status": "error: storage_unavailable"}

        try:
            decision = self.engine.decide(customer_id)
        except BureauUnavailableError:
            return {"status": "error: bureau_unavailable"}

        try:
            self.store.update_application("APP-1", decision)
        except StorageUnavailableError:
            return {"status": "error: storage_unavailable"}

        self.notifier.send_decision(customer_id, decision)
        return {"status": decision, "application_id": "APP-1"}


def handle(request: dict) -> dict:
    bureau = CreditBureau()
    store = ApplicationStore()
    notifier = NotificationService()
    engine = DecisionEngine(bureau)
    api = OriginationApi(store, engine, notifier)
    return api.process_application(request)
