import numbers


class ScreeningError(Exception):
    """Raised when the external screening provider is unavailable."""
    pass


class StoreError(Exception):
    """Raised when the quote store is unavailable."""
    pass


# Screening decision thresholds (decision table DT-S).
ACCEPT_MAX = 30
REVIEW_MIN = 30
REVIEW_MAX = 70
REFUSE_MIN = 70

# Validation bounds (decision table DT-V, mirrored from the OpenAPI schema).
WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, ctx=None):
        ctx = ctx or {}
        raw = ctx.get("screening_result", ctx.get("screening_status", "approved"))
        status = str(raw).lower()
        if status in ("error", "unavailable", "down", "timeout"):
            raise ScreeningError("screening service unavailable")
        try:
            return float(status)
        except ValueError:
            pass
        mapping = {
            "approved": 10, "accept": 10, "clear": 10, "low": 10,
            "review": 50, "hold": 50, "medium": 50, "assessed": 50,
            "declined": 90, "refused": 90, "denied": 90, "high": 90,
        }
        return mapping.get(status, 10)


class TariffEngine:
    """Computes the freight price from weight and distance per published tariff rules."""

    def price(self, weight_kg, distance_km):
        return round(weight_kg * 0.5 + distance_km * 0.1, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._counter = 0
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, ctx=None):
        ctx = ctx or {}
        raw = ctx.get("store_result", ctx.get("store_status", "stored"))
        status = str(raw).lower()
        if status in ("error", "unavailable", "down"):
            raise StoreError("store unavailable")
        self._counter += 1
        quote_id = "Q-{}".format(self._counter)
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price=None):
        record = self._records.get(quote_id, {})
        record["status"] = status
        if price is not None:
            record["price"] = price
        self._records[quote_id] = record
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine=None, quote_store=None,
                 screening_service=None, notification_service=None):
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    def _valid_number(self, value, low, high):
        if not isinstance(value, numbers.Number) or isinstance(value, bool):
            return False
        return low <= value <= high

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or len(shipper_id) < 1:
            return False
        if not self._valid_number(request.get("weight_kg"), WEIGHT_MIN, WEIGHT_MAX):
            return False
        if not self._valid_number(request.get("distance_km"), DISTANCE_MIN, DISTANCE_MAX):
            return False
        if not self._valid_number(request.get("declared_value"), VALUE_MIN, VALUE_MAX):
            return False
        return True

    def request_quote(self, request):
        # Validation (DT-V).
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]

        # Store draft; on failure nothing else runs (DT-S note 3).
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, request)
        except StoreError:
            return {"status": "error: store_unavailable"}

        # Screening.
        try:
            risk_index = self.screening_service.screen(shipper_id, request)
        except ScreeningError:
            # Screening outage: price it, hold it, do not notify (DT-S note 5).
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Accept row.
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        # Refuse row (pricing never runs; refusal IS notified) (DT-S note 2).
        if risk_index >= REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}

        # Review row (no pricing, no notification) (DT-S note 1).
        self.quote_store.update_quote(quote_id, "review_hold")
        return {"status": "review_hold", "quote_id": quote_id}


def handle(request: dict) -> dict:
    api = QuoteApi()
    return api.request_quote(request or {})