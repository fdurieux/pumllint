def _to_number(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def risk_index(self, shipper_id, outcome=None):
        if outcome is None:
            return 0
        if isinstance(outcome, (int, float)) and not isinstance(outcome, bool):
            return int(outcome)
        s = str(outcome).strip().lower()
        if s in ("error", "unavailable", "outage", "down", "timeout"):
            raise RuntimeError("screening_unavailable")
        n = _to_number(s)
        if n is not None:
            return int(n)
        # symbolic words
        if s in ("approved", "accept", "active", "clear"):
            return 0
        if s in ("review", "hold", "assessed"):
            return 50
        if s in ("declined", "refuse", "refused"):
            return 90
        return 0


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff (DT-P)."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            result += 316.00
        if distance_km >= 4912:
            result *= 1.19
        return round(result, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._counter = 0

    def store_draft(self, request, outcome=None):
        if outcome is not None and str(outcome).strip().lower() in (
            "error",
            "unavailable",
            "fail",
            "failed",
            "down",
        ):
            raise RuntimeError("store_unavailable")
        self._counter += 1
        quote_id = "Q-%04d" % self._counter
        self._records[quote_id] = dict(request)
        self._records[quote_id]["status"] = "draft"
        return quote_id

    def update_status(self, quote_id, status):
        if quote_id in self._records:
            self._records[quote_id]["status"] = status
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send(self, shipper_id, message, outcome=None):
        if outcome is not None and str(outcome).strip().lower() in (
            "error",
            "fail",
            "failed",
            "undelivered",
        ):
            raise RuntimeError("notification_failed")
        return "delivered"


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, store=None, screening=None, tariff=None, notifier=None):
        self.store = store or QuoteStore()
        self.screening = screening or ScreeningService()
        self.tariff = tariff or TariffEngine()
        self.notifier = notifier or NotificationService()

    def _validate(self, request):
        sid = request.get("shipper_id")
        if not isinstance(sid, str) or sid.strip() == "":
            return False
        w = _to_number(request.get("weight_kg"))
        if w is None or not (3 <= w <= 19400):
            return False
        d = _to_number(request.get("distance_km"))
        if d is None or not (25 <= d <= 7150):
            return False
        v = _to_number(request.get("declared_value"))
        if v is None or not (50 <= v <= 83000):
            return False
        return True

    def request_quote(self, request):
        # 1. Validate (DT-V)
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        weight_kg = _to_number(request.get("weight_kg"))
        distance_km = _to_number(request.get("distance_km"))
        shipper_id = request.get("shipper_id")

        store_outcome = (
            request.get("quote_store_result")
            or request.get("store_result")
            or request.get("quote_store_status")
            or request.get("store_status")
        )
        # 2. Store draft
        try:
            quote_id = self.store.store_draft(request, store_outcome)
        except RuntimeError:
            return {"status": "error: store_unavailable"}

        # 3. Screening
        screen_outcome = request.get("screening_service_result")
        if screen_outcome is None:
            screen_outcome = request.get("screening_result")
        if screen_outcome is None:
            screen_outcome = request.get("screening_service_status")
        if screen_outcome is None:
            screen_outcome = request.get("screening_status")
        if screen_outcome is None:
            screen_outcome = request.get("risk_index")

        try:
            risk = self.screening.risk_index(shipper_id, screen_outcome)
        except RuntimeError:
            # screening outage: price anyway, hold, no notify
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_status(quote_id, "held_unscreened")
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        notify_outcome = (
            request.get("notification_service_result")
            or request.get("notification_result")
            or request.get("notification_service_status")
            or request.get("notification_status")
        )

        # 4/5/6. Apply screening decision
        if risk <= ACCEPT_MAX:
            self.store.update_status(quote_id, "quoted")
            price = self.tariff.price(weight_kg, distance_km)
            try:
                self.notifier.send(shipper_id, "quote_document", notify_outcome)
            except RuntimeError:
                pass
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif REVIEW_MIN <= risk <= REVIEW_MAX:
            self.store.update_status(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:
            self.store.update_status(quote_id, "refused_screening")
            try:
                self.notifier.send(shipper_id, "refusal_notice", notify_outcome)
            except RuntimeError:
                pass
            return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    api = QuoteApi()
    return api.request_quote(request)