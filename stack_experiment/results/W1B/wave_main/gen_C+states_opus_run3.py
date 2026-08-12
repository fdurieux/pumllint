import uuid

# Decision-table thresholds (DT-S)
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70

# Validation bounds (DT-V)
WEIGHT_MIN, WEIGHT_MAX = 1, 26000
DISTANCE_MIN, DISTANCE_MAX = 1, 3000
VALUE_MIN, VALUE_MAX = 1, 10_000_000


class ScreeningService:
    """External denied-party screening provider — returns a shipper risk index."""

    def screen(self, shipper_id, outcome=None):
        if outcome is None:
            return 10
        if isinstance(outcome, (int, float)):
            return outcome
        word = str(outcome).lower()
        if word in ("error", "unavailable", "down", "timeout"):
            raise RuntimeError("screeningUnavailableError")
        if word in ("approved", "accept", "clear", "active", "low"):
            return 10
        if word in ("review", "hold", "manual", "medium"):
            return 50
        if word in ("declined", "refused", "denied", "high"):
            return 90
        try:
            return float(word)
        except ValueError:
            return 10


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules."""

    BASE = 25.0
    RATE_PER_KG = 0.15
    RATE_PER_KM = 0.40

    def price(self, weight_kg, distance_km):
        return round(self.BASE + weight_kg * self.RATE_PER_KG
                     + distance_km * self.RATE_PER_KM, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value,
                    available=True):
        if not available:
            raise RuntimeError("storeUnavailableError")
        quote_id = str(uuid.uuid4())
        self._records[quote_id] = {
            "shipperId": shipper_id,
            "weightKg": weight_kg,
            "distanceKm": distance_km,
            "declaredValue": declared_value,
            "status": "Draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price=None):
        record = self._records.get(quote_id)
        if record is None:
            raise RuntimeError("unknownQuote")
        record["status"] = status
        if price is not None:
            record["price"] = price
        return quote_id


class NotificationService:
    """External messaging provider — fire-and-forget delivery."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class QuoteApi:
    """Receives quote requests, orchestrates screening and pricing."""

    def __init__(self, tariff_engine=None, quote_store=None,
                 screening_service=None, notification_service=None):
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            return False
        for value, lo, hi in (
            (weight_kg, WEIGHT_MIN, WEIGHT_MAX),
            (distance_km, DISTANCE_MIN, DISTANCE_MAX),
            (declared_value, VALUE_MIN, VALUE_MAX),
        ):
            if not isinstance(value, (int, float)):
                return False
            if value < lo or value > hi:
                return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value,
                      store_available=True, screening_outcome=None):
        # Validation (DT-V)
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value,
                available=store_available)
        except RuntimeError:
            # DT-S note 3: nothing else runs on storage failure
            return {"status": "error: store_unavailable"}

        # Screening
        try:
            risk_index = self.screening_service.screen(shipper_id, screening_outcome)
        except RuntimeError:
            # DT-S note 5: screening outage — price, hold, do not notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "HeldUnscreened", price_amount)
            return {"status": "held_unscreened", "quoteId": quote_id,
                    "price": price_amount}

        # Screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "Quoted", price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quoteId": quote_id, "price": price_amount}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # DT-S note 1: no pricing, no notification
            self.quote_store.update_quote(quote_id, "ReviewHold")
            return {"status": "review_hold", "quoteId": quote_id}

        # risk_index >= REFUSE_MIN
        self.quote_store.update_quote(quote_id, "RefusedScreening")
        self.notification_service.send_refusal_notice(shipper_id, quote_id)
        return {"status": "refused_screening", "quoteId": quote_id}


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id") or request.get("shipperId")

    def _num(*keys):
        for k in keys:
            if k in request and request[k] is not None:
                return request[k]
        return None

    weight_kg = _num("weightKg", "weight_kg", "weight")
    distance_km = _num("distanceKm", "distance_km", "distance")
    declared_value = _num("declaredValue", "declared_value", "value")

    # Store availability
    store_status = str(request.get("store_result")
                       or request.get("quote_store_result")
                       or request.get("store_status") or "").lower()
    store_available = True
    if "shipper_exists" in request and not request["shipper_exists"]:
        pass
    if store_status in ("error", "unavailable", "down"):
        store_available = False

    # Screening outcome
    screening_outcome = None
    for k in ("screening_result", "screening_status", "screening_score",
              "screening"):
        if k in request and request[k] is not None:
            screening_outcome = request[k]
            break

    api = QuoteApi()
    try:
        return api.request_quote(
            shipper_id, weight_kg, distance_km, declared_value,
            store_available=store_available,
            screening_outcome=screening_outcome)
    except Exception as exc:  # pragma: no cover
        return {"status": f"error: {exc}"}