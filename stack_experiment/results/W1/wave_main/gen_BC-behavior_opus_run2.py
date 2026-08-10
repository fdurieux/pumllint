import uuid


class ScreeningUnavailable(Exception):
    pass


class StoreUnavailable(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, request):
        status = str(request.get("screening_status", "")).lower()
        raw = request.get("screening_result", request.get("risk_index"))
        raw_s = str(raw).lower()
        if status in ("error", "unavailable", "outage", "down") or raw_s in (
            "error",
            "unavailable",
            "outage",
        ):
            raise ScreeningUnavailable()
        source = raw
        if source is None:
            source = request.get("screening_status")
        try:
            return int(float(source))
        except (TypeError, ValueError):
            raise ScreeningUnavailable()


class TariffEngine:
    """Computes the freight price per DT-P."""

    def price(self, request):
        weight = float(request["weight_kg"])
        distance = float(request["distance_km"])
        result = 0.87 * weight + 1.13 * distance
        if weight > 1244:
            result += 316.00
        if distance >= 4912:
            result *= 1.19
        return round(result, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}

    def store_draft(self, request):
        status = str(request.get("store_status", request.get("store_result", ""))).lower()
        if status in ("error", "unavailable", "down", "fail", "failed"):
            raise StoreUnavailable()
        quote_id = "Q-" + uuid.uuid4().hex[:12]
        self._records[quote_id] = {"request": dict(request), "status": "draft"}
        return quote_id

    def update_status(self, quote_id, status):
        if quote_id in self._records:
            self._records[quote_id]["status"] = status
        return "updated"


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send(self, shipper_id, kind, request):
        status = str(request.get("notification_status", request.get("notification_result", ""))).lower()
        if status in ("error", "unavailable", "fail", "failed", "undelivered"):
            raise RuntimeError("notification delivery failed")
        return "delivered"


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class QuoteApi:
    """Receives quote requests, orchestrates screening and pricing."""

    def __init__(self, store=None, screening=None, tariff=None, notification=None):
        self.store = store or QuoteStore()
        self.screening = screening or ScreeningService()
        self.tariff = tariff or TariffEngine()
        self.notification = notification or NotificationService()

    def _validate(self, request):
        shipper = request.get("shipper_id")
        if not isinstance(shipper, str) or shipper.strip() == "":
            return False
        if not self._num_in(request.get("weight_kg"), 3, 19400):
            return False
        if not self._num_in(request.get("distance_km"), 25, 7150):
            return False
        if not self._num_in(request.get("declared_value"), 50, 83000):
            return False
        return True

    @staticmethod
    def _num_in(value, lo, hi):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        return lo <= value <= hi

    def request_quote(self, request):
        # 1. Validate
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        # 2. Store draft
        try:
            quote_id = self.store.store_draft(request)
        except StoreUnavailable:
            return {"status": "error: store_unavailable"}

        # 3. Screening
        try:
            risk_index = self.screening.screen(request)
        except ScreeningUnavailable:
            # Screening outage: price anyway, hold unscreened, no notification
            price = self.tariff.price(request)
            self.store.update_status(quote_id, "held_unscreened")
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4. Apply screening decision
        if risk_index <= ACCEPT_MAX:
            self.store.update_status(quote_id, "quoted")
            price = self.tariff.price(request)
            self._notify(request, "quote_document")
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif risk_index <= REVIEW_MAX:
            self.store.update_status(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:
            self.store.update_status(quote_id, "refused_screening")
            self._notify(request, "refusal_notice")
            return {"status": "refused_screening", "quote_id": quote_id}

    def _notify(self, request, kind):
        # fire-and-forget: delivery failure never changes the outcome
        try:
            self.notification.send(request.get("shipper_id"), kind, request)
        except Exception:
            pass


def handle(request: dict) -> dict:
    api = QuoteApi()
    return api.request_quote(request)