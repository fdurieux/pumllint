BASE_FEE = 25.0
RATE_PER_KG = 0.05
RATE_PER_KM = 0.10

WEIGHT_MIN, WEIGHT_MAX = 1.0, 26000.0
DISTANCE_MIN, DISTANCE_MAX = 1.0, 3000.0
VALUE_MIN, VALUE_MAX = 0.01, 1_000_000.0

ACCEPT_MAX = 30
REVIEW_MIN, REVIEW_MAX = 31, 69
REFUSE_MIN = 70


class ScreeningError(Exception):
    pass


class StoreError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, outcome=None):
        if outcome is None:
            return 10
        if isinstance(outcome, (int, float)):
            return outcome
        word = str(outcome).lower()
        if word in ("error", "unavailable", "timeout", "down"):
            raise ScreeningError("screening service unavailable")
        if word in ("approved", "clear", "accept", "low"):
            return 10
        if word in ("review", "hold", "medium", "assessed"):
            return 50
        if word in ("declined", "refused", "refuse", "denied", "high"):
            return 90
        try:
            return float(word)
        except ValueError:
            return 10


class TariffEngine:
    """Computes the freight price from weight and distance per published tariff."""

    def price(self, weight_kg, distance_km):
        return round(BASE_FEE + weight_kg * RATE_PER_KG + distance_km * RATE_PER_KM, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, outcome=None):
        if outcome is not None and str(outcome).lower() in ("error", "unavailable", "down"):
            raise StoreError("store unavailable")
        self._seq += 1
        quote_id = "Q%05d" % self._seq
        self._records[quote_id] = {
            "shipperId": shipper_id,
            "weightKg": weight_kg,
            "distanceKm": distance_km,
            "declaredValue": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price=None):
        record = self._records.get(quote_id)
        if record is None:
            raise StoreError("unknown quote")
        record["status"] = status
        if price is not None:
            record["price"] = price
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
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

    def _validate(self, weight_kg, distance_km, declared_value):
        if weight_kg is None or distance_km is None or declared_value is None:
            return "missing field"
        try:
            weight_kg = float(weight_kg)
            distance_km = float(distance_km)
            declared_value = float(declared_value)
        except (TypeError, ValueError):
            return "non-numeric field"
        if not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            return "weight out of bounds"
        if not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            return "distance out of bounds"
        if not (VALUE_MIN <= declared_value <= VALUE_MAX):
            return "value out of bounds"
        return None

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value,
                      screening_outcome=None, store_outcome=None):
        # Validation (DT-V)
        error = self._validate(weight_kg, distance_km, declared_value)
        if error is not None:
            return {"status": "rejected: invalid request", "reason": error}

        weight_kg = float(weight_kg)
        distance_km = float(distance_km)
        declared_value = float(declared_value)

        # Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, store_outcome)
        except StoreError:
            return {"status": "error: store unavailable"}

        # Screening
        try:
            risk_index = self.screening_service.screen(shipper_id, screening_outcome)
        except ScreeningError:
            # Screening outage: price, hold unscreened, do not notify (note 5)
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {"status": "held_unscreened", "quoteId": quote_id,
                    "price": price_amount}

        # Accept path (DT-S accept)
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quoteId": quote_id, "price": price_amount}

        # Refuse path (DT-S refuse)
        if risk_index >= REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quoteId": quote_id}

        # Review hold path (DT-S review)
        self.quote_store.update_quote(quote_id, "review_hold")
        return {"status": "review_hold", "quoteId": quote_id}


def _pick(request, *keys, default=None):
    for k in keys:
        if k in request and request[k] is not None:
            return request[k]
    return default


def handle(request: dict) -> dict:
    api = QuoteApi()

    shipper_id = _pick(request, "shipperId", "shipper_id", "shipper", default="unknown")

    if request.get("shipper_exists") is False or request.get("shipper_found") is False:
        return {"status": "rejected: invalid request", "reason": "unknown shipper"}

    weight_kg = _pick(request, "weightKg", "weight_kg", "weight")
    distance_km = _pick(request, "distanceKm", "distance_km", "distance")
    declared_value = _pick(request, "declaredValue", "declared_value", "value")

    screening_outcome = _pick(request, "screening_result", "screening_status")
    store_outcome = _pick(request, "store_result", "store_status")

    return api.request_quote(
        shipper_id, weight_kg, distance_km, declared_value,
        screening_outcome=screening_outcome, store_outcome=store_outcome)