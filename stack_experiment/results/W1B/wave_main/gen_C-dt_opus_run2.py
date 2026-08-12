import uuid

# --- Decision table constants ---

# DT-V validation bounds (mirrored from OpenAPI schema)
WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000

# DT-S screening bands (higher risk index is worse)
ACCEPT_MAX = 30
REVIEW_MIN, REVIEW_MAX = 31, 70
REFUSE_MIN = 71

# DT-P pricing parameters
BASE_RATE = 25.0
RATE_PER_KG = 0.12
RATE_PER_KM = 0.35


class ScreeningUnavailable(Exception):
    pass


class StoreUnavailable(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, request):
        raw = request.get("screening_result", request.get("screening_status"))
        if isinstance(raw, bool):
            raw = None
        if isinstance(raw, (int, float)):
            return int(raw)
        if raw in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailable("screening service unavailable")
        if raw in ("approved", "accept", "clear"):
            return 10
        if raw in ("review", "hold", "manual"):
            return 50
        if raw in ("declined", "refused", "refuse", "denied"):
            return 90
        # default: clean shipper
        return 10


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

    def price(self, weight_kg, distance_km):
        amount = BASE_RATE + weight_kg * RATE_PER_KG + distance_km * RATE_PER_KM
        return round(amount, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, request):
        raw = request.get("store_result", request.get("store_status"))
        if raw in ("error", "unavailable", "down", "fail", "failure"):
            raise StoreUnavailable("quote store unavailable")
        quote_id = "Q-" + uuid.uuid4().hex[:12]
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
        rec = self._records.get(quote_id)
        if rec is not None:
            rec["status"] = status
            if price is not None:
                rec["price"] = price
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, request=None):
        self._request = request or {}

    def _fail_requested(self):
        raw = self._request.get("notification_result",
                                self._request.get("notification_status"))
        return raw in ("error", "unavailable", "down", "fail", "failure")

    def send_quote_document(self, shipper_id, quote_id, price):
        if self._fail_requested():
            raise Exception("notification delivery failed")
        return True

    def send_refusal_notice(self, shipper_id, quote_id):
        if self._fail_requested():
            raise Exception("notification delivery failed")
        return True


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or len(shipper_id) < 1:
            return False
        try:
            weight = float(request["weight_kg"])
            distance = float(request["distance_km"])
            value = float(request["declared_value"])
        except (KeyError, TypeError, ValueError):
            return False
        if not (WEIGHT_MIN <= weight <= WEIGHT_MAX):
            return False
        if not (DISTANCE_MIN <= distance <= DISTANCE_MAX):
            return False
        if not (VALUE_MIN <= value <= VALUE_MAX):
            return False
        return True

    def request_quote(self, request):
        # Step 1: validate
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight = float(request["weight_kg"])
        distance = float(request["distance_km"])
        value = float(request["declared_value"])

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight, distance, value, request)
        except StoreUnavailable:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id, request)
        except ScreeningUnavailable:
            # screening outage: price anyway, hold, no notification
            price = self.tariff_engine.price(weight, distance)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4-6: apply DT-S decision
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight, distance)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self._notify_quote(shipper_id, quote_id, price)
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        if risk_index >= REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self._notify_refusal(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}

        # Fallback (should not occur): treat as review hold
        self.quote_store.update_quote(quote_id, "review_hold")
        return {"status": "review_hold", "quote_id": quote_id}

    def _notify_quote(self, shipper_id, quote_id, price):
        # fire-and-forget; delivery failure never changes the response
        try:
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
        except Exception:
            pass

    def _notify_refusal(self, shipper_id, quote_id):
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            pass


def handle(request: dict) -> dict:
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    notification_service = NotificationService(request)
    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)
    return api.request_quote(request)