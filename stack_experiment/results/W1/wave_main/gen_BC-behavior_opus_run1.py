import math


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def risk_index(self, shipper_id, request):
        status = str(request.get("screening_service_status",
                                 request.get("screening_status",
                                             request.get("screening_service_result",
                                                         request.get("screening_result", "")))))
        if status in ("error", "unavailable", "outage", "down", "timeout"):
            raise RuntimeError("screening_unavailable")
        val = request.get("screening_result", request.get("risk_index"))
        if val is None:
            val = request.get("screening_service_result")
        try:
            return int(val)
        except (TypeError, ValueError):
            return 0


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

    def compute_price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            result += 316.00
        if distance_km >= 4912:
            result *= 1.19
        return round(result, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._seq = 0
        self._records = {}

    def store_draft(self, request):
        status = str(request.get("quote_store_status",
                                 request.get("store_status",
                                             request.get("quote_store_result",
                                                         request.get("store_result", "")))))
        if status in ("error", "unavailable", "down", "fail", "failed"):
            raise RuntimeError("store_unavailable")
        self._seq += 1
        quote_id = "Q-{:06d}".format(self._seq)
        self._records[quote_id] = dict(request)
        self._records[quote_id]["status"] = "draft"
        return quote_id

    def update_status(self, quote_id, status):
        if quote_id in self._records:
            self._records[quote_id]["status"] = status
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send(self, shipper_id, kind, request):
        status = str(request.get("notification_service_status",
                                 request.get("notification_status",
                                             request.get("notification_service_result",
                                                         request.get("notification_result", "")))))
        if status in ("error", "unavailable", "fail", "failed", "down"):
            return "failed"
        return "delivered"


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening
    and pricing, and returns the quotation outcome."""

    def __init__(self, tariff_engine=None, quote_store=None,
                 screening_service=None, notification_service=None):
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False
        weight = request.get("weight_kg")
        if not self._is_number(weight) or not (3 <= weight <= 19400):
            return False
        distance = request.get("distance_km")
        if not self._is_number(distance) or not (25 <= distance <= 7150):
            return False
        value = request.get("declared_value")
        if not self._is_number(value) or not (50 <= value <= 83000):
            return False
        return True

    @staticmethod
    def _is_number(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    def request_quote(self, request):
        # 1. Validate (DT-V)
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        # 2. Store draft
        try:
            quote_id = self.quote_store.store_draft(request)
        except RuntimeError:
            return {"status": "error: store_unavailable"}

        shipper_id = request["shipper_id"]
        weight = request["weight_kg"]
        distance = request["distance_km"]

        # 3. Screening
        try:
            risk_index = self.screening_service.risk_index(shipper_id, request)
        except RuntimeError:
            # screening outage: price anyway, hold_unscreened, no notify
            price = self.tariff_engine.compute_price(weight, distance)
            self.quote_store.update_status(quote_id, "held_unscreened")
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4. Apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            self.quote_store.update_status(quote_id, "quoted")
            price = self.tariff_engine.compute_price(weight, distance)
            self.notification_service.send(shipper_id, "quote_document", request)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif risk_index <= REVIEW_MAX:
            self.quote_store.update_status(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:
            self.quote_store.update_status(quote_id, "refused_screening")
            self.notification_service.send(shipper_id, "refusal_notice", request)
            return {"status": "refused_screening", "quote_id": quote_id}


_api = QuoteApi()


def handle(request: dict) -> dict:
    return _api.request_quote(request)