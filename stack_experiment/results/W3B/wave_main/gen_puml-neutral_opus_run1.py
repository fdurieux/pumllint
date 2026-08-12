ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70

WEIGHT_MIN, WEIGHT_MAX = 1, 30000
DISTANCE_MIN, DISTANCE_MAX = 1, 3000
VALUE_MIN, VALUE_MAX = 0, 1_000_000


class ScreeningUnavailable(Exception):
    pass


class StoreUnavailable(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, request=None):
        self._request = request or {}

    def screen(self, shipper_id):
        req = self._request
        status = str(req.get("screening_result",
                     req.get("screening_status", "approved"))).lower()

        if status in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailable("screening service unavailable")

        # explicit numeric score wins
        for key in ("screening_score", "risk_index", "screening_result",
                    "screening_status"):
            val = req.get(key)
            if isinstance(val, (int, float)):
                return val
            if isinstance(val, str):
                try:
                    return float(val)
                except ValueError:
                    pass

        if status in ("approved", "accept", "accepted", "clear", "active"):
            return 10
        if status in ("review", "hold", "assessed", "manual"):
            return 50
        if status in ("declined", "refused", "denied", "reject", "rejected"):
            return 90
        return 10


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "delivered"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "delivered"


class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    BASE = 25.0
    PER_KG = 0.20
    PER_KM = 0.15

    def price(self, weight_kg, distance_km):
        return round(self.BASE + self.PER_KG * weight_kg + self.PER_KM * distance_km, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, request=None):
        self._request = request or {}
        self._data = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        status = str(self._request.get("store_result",
                     self._request.get("store_status", "stored"))).lower()
        if status in ("error", "unavailable", "down"):
            raise StoreUnavailable("store unavailable")
        self._seq += 1
        quote_id = "Q%04d" % self._seq
        self._data[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        rec = self._data.get(quote_id, {})
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        self._data[quote_id] = rec
        return "updated"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service,
                 notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            return False
        try:
            w = float(weight_kg)
            d = float(distance_km)
            v = float(declared_value)
        except (TypeError, ValueError):
            return False
        if not (WEIGHT_MIN <= w <= WEIGHT_MAX):
            return False
        if not (DISTANCE_MIN <= d <= DISTANCE_MAX):
            return False
        if not (VALUE_MIN <= v <= VALUE_MAX):
            return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Validation (DT-V)
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected", "reason": "invalid_request"}

        # Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailable:
            return {"status": "error: store_unavailable"}

        # Screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailable:
            # Outage does not fail the quote: price, store on hold, no notify.
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, "held_unscreened", price_amount)
            return {"status": "held_unscreened", "quote_id": quote_id,
                    "price": price_amount}

        # Decision table DT-S
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quote_id": quote_id,
                    "price": price_amount}
        elif risk_index >= REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused", "quote_id": quote_id}
        else:
            # REVIEW_MIN <= risk_index <= REVIEW_MAX
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}


def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = request.get("shipperId", request.get("shipper_id"))
    weight_kg = request.get("weightKg", request.get("weight_kg"))
    distance_km = request.get("distanceKm", request.get("distance_km"))
    declared_value = request.get("declaredValue", request.get("declared_value"))

    tariff_engine = TariffEngine()
    quote_store = QuoteStore(request)
    screening_service = ScreeningService(request)
    notification_service = NotificationService()

    api = QuoteApi(tariff_engine, quote_store, screening_service,
                   notification_service)

    try:
        return api.request_quote(shipper_id, weight_kg, distance_km,
                                 declared_value)
    except Exception as exc:  # pragma: no cover
        return {"status": "error: %s" % exc}