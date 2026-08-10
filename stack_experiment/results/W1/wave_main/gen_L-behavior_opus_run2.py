import uuid


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def risk_index(self, shipper_id, request):
        val = request.get("screening_result", request.get("screening_status"))
        if val is None:
            val = request.get("risk_index")
        if isinstance(val, str):
            if val in ("error", "unavailable", "outage", "down"):
                raise RuntimeError("screening_unavailable")
            try:
                return int(val)
            except ValueError:
                raise RuntimeError("screening_unavailable")
        if val is None:
            return 0
        return int(val)


class TariffEngine:
    """Computes the freight price per DT-P."""

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

    def store_draft(self, request):
        status = request.get("store_result", request.get("store_status", "stored"))
        if status in ("error", "unavailable", "fail", "failed"):
            raise RuntimeError("store_unavailable")
        quote_id = str(uuid.uuid4())
        self._records[quote_id] = {"status": "draft"}
        return quote_id

    def update_status(self, quote_id, status):
        if quote_id in self._records:
            self._records[quote_id]["status"] = status
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send(self, shipper_id, kind, request):
        status = request.get("notification_result", request.get("notification_status", "delivered"))
        if status in ("error", "fail", "failed", "undelivered"):
            return "failed"
        return "delivered"


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, store=None, screening=None, tariff=None, notification=None):
        self.store = store or QuoteStore()
        self.screening = screening or ScreeningService()
        self.tariff = tariff or TariffEngine()
        self.notification = notification or NotificationService()

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or not shipper_id:
            return False
        weight = request.get("weight_kg")
        if not isinstance(weight, (int, float)) or isinstance(weight, bool):
            return False
        if not (3 <= weight <= 19400):
            return False
        distance = request.get("distance_km")
        if not isinstance(distance, (int, float)) or isinstance(distance, bool):
            return False
        if not (25 <= distance <= 7150):
            return False
        value = request.get("declared_value")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False
        if not (50 <= value <= 83000):
            return False
        return True

    def request_quote(self, request):
        # 1. Validate
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        # 2. Store draft
        try:
            quote_id = self.store.store_draft(request)
        except Exception:
            return {"status": "error: store_unavailable"}

        shipper_id = request["shipper_id"]
        weight = request["weight_kg"]
        distance = request["distance_km"]

        # 3. Screening
        try:
            risk = self.screening.risk_index(shipper_id, request)
        except Exception:
            # Screening outage: price anyway, hold, do not notify
            price = self.tariff.price(weight, distance)
            self.store.update_status(quote_id, "held_unscreened")
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4-6. Apply screening decision
        if risk <= ACCEPT_MAX:
            self.store.update_status(quote_id, "quoted")
            price = self.tariff.price(weight, distance)
            self.notification.send(shipper_id, "quote_document", request)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif risk <= REVIEW_MAX:
            self.store.update_status(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:
            self.store.update_status(quote_id, "refused_screening")
            self.notification.send(shipper_id, "refusal_notice", request)
            return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    api = QuoteApi()
    return api.request_quote(request)