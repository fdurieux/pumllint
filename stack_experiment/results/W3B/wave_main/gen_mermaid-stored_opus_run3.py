import enum


class ScreeningUnavailableError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


# Decision table DT-S thresholds (risk index 0..100)
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

# Decision table DT-V validation bounds
WEIGHT_MIN, WEIGHT_MAX = 1, 24000
DISTANCE_MIN, DISTANCE_MAX = 1, 3000
VALUE_MIN, VALUE_MAX = 1, 1_000_000


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, result=None):
        self._result = result

    def screen(self, shipper_id):
        r = self._result
        if r is None:
            return 10
        if isinstance(r, (int, float)):
            return r
        word = str(r).strip().lower()
        if word in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailableError("screening service unavailable")
        mapping = {
            "approved": 10,
            "accepted": 10,
            "accept": 10,
            "clear": 10,
            "review": 50,
            "hold": 50,
            "declined": 90,
            "refused": 90,
            "refuse": 90,
            "denied": 90,
        }
        try:
            return float(word)
        except ValueError:
            return mapping.get(word, 10)


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff rules."""

    BASE = 25.0
    PER_KG = 0.15
    PER_KM = 0.40

    def price(self, weight_kg, distance_km):
        return round(self.BASE + self.PER_KG * weight_kg + self.PER_KM * distance_km, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, store_result=None):
        self._store_result = store_result
        self._seq = 0
        self._records = {}

    def _available(self):
        r = self._store_result
        if r is None:
            return True
        word = str(r).strip().lower()
        return word not in ("error", "unavailable", "down", "fail", "failed")

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._available():
            raise StoreUnavailableError("quote store unavailable")
        self._seq += 1
        quote_id = "Q-%04d" % self._seq
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        rec = self._records.get(quote_id, {})
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        self._records[quote_id] = rec
        return "updated"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            return "missing shipper"
        try:
            w = float(weight_kg)
            d = float(distance_km)
            v = float(declared_value)
        except (TypeError, ValueError):
            return "non-numeric field"
        if not (WEIGHT_MIN <= w <= WEIGHT_MAX):
            return "weight out of bounds"
        if not (DISTANCE_MIN <= d <= DISTANCE_MAX):
            return "distance out of bounds"
        if not (VALUE_MIN <= v <= VALUE_MAX):
            return "declared value out of bounds"
        return None

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Validation (DT-V)
        error = self._validate(shipper_id, weight_kg, distance_km, declared_value)
        if error is not None:
            return {"status": "rejected", "reason": error}

        # Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Screening (DT-S)
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Note 5: screening outage does not fail the quote
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused", "quote_id": quote_id}


def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = request.get("shipper_id", request.get("shipperId"))
    if shipper_id is None and request.get("shipper_exists", True):
        shipper_id = "shipper-1"
    if request.get("shipper_exists") is False or request.get("shipper_found") is False:
        shipper_id = None

    weight_kg = request.get("weight_kg", request.get("weightKg", 1000))
    distance_km = request.get("distance_km", request.get("distanceKm", 500))
    declared_value = request.get("declared_value", request.get("declaredValue", 10000))

    screening_result = request.get("screening_result", request.get("screening_status"))
    store_result = request.get("store_result", request.get("store_status"))

    api = QuoteApi(
        TariffEngine(),
        QuoteStore(store_result),
        ScreeningService(screening_result),
        NotificationService(),
    )

    try:
        return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    except Exception as exc:  # pragma: no cover
        return {"status": "error: %s" % exc}