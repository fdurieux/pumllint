import uuid


# --- Constants (decision tables DT-V and DT-S) ---

# DT-V: validation bounds
WEIGHT_MIN = 1
WEIGHT_MAX = 30000
DISTANCE_MIN = 1
DISTANCE_MAX = 3000
VALUE_MIN = 1
VALUE_MAX = 1_000_000

# DT-S: screening risk index thresholds (0..100 scale)
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70

# Sentinel returned by screening when the provider is unavailable
SCREENING_UNAVAILABLE = "screeningUnavailableError"
STORE_UNAVAILABLE = "storeUnavailableError"


# --- External systems (outside the boundary) ---

class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, outcome=None):
        # outcome may be a number, a word, or "error"
        self._outcome = outcome

    def screen(self, shipper_id):
        o = self._outcome
        if o == "error" or o == "unavailable":
            return SCREENING_UNAVAILABLE
        if isinstance(o, (int, float)):
            return o
        if isinstance(o, str):
            word = o.strip().lower()
            if word in ("approved", "accept", "accepted", "active", "clear"):
                return 10
            if word in ("review", "hold", "assessed"):
                return 50
            if word in ("declined", "refuse", "refused", "denied"):
                return 90
            try:
                return float(word)
            except ValueError:
                pass
        # default plausible low-risk value
        return 5


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        # fire-and-forget
        return "sent"

    def sendRefusalNotice(self, shipper_id, quote_id):
        # fire-and-forget
        return "sent"


# --- Internal containers ---

class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG = 0.15
    RATE_PER_KM = 0.40

    def price(self, weight_kg, distance_km):
        amount = (
            self.BASE_FEE
            + weight_kg * self.RATE_PER_KG
            + distance_km * self.RATE_PER_KM
        )
        return round(amount, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self._available = available
        self._records = {}

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._available:
            return STORE_UNAVAILABLE
        quote_id = str(uuid.uuid4())
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def updateQuote(self, quote_id, status, price_amount=None):
        rec = self._records.get(quote_id)
        if rec is None:
            rec = {"status": None}
            self._records[quote_id] = rec
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        return "updatedQuote"


class ValidationError(Exception):
    pass


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, weight_kg, distance_km, declared_value):
        if weight_kg is None or distance_km is None or declared_value is None:
            raise ValidationError("missing_field")
        try:
            w = float(weight_kg)
            d = float(distance_km)
            v = float(declared_value)
        except (TypeError, ValueError):
            raise ValidationError("non_numeric")
        if not (WEIGHT_MIN <= w <= WEIGHT_MAX):
            raise ValidationError("weight_out_of_bounds")
        if not (DISTANCE_MIN <= d <= DISTANCE_MAX):
            raise ValidationError("distance_out_of_bounds")
        if not (VALUE_MIN <= v <= VALUE_MAX):
            raise ValidationError("value_out_of_bounds")
        return w, d, v

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Validate (DT-V)
        try:
            w, d, v = self._validate(weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": "rejected", "reason": str(e)}

        # Store draft
        quote_id = self.quote_store.storeDraft(shipper_id, w, d, v)
        if quote_id == STORE_UNAVAILABLE:
            # DT-S note 3: nothing else runs
            return {"status": "error: store_unavailable"}

        # Screening
        risk_index = self.screening_service.screen(shipper_id)

        # Screening failure path (DT-S note 5): price, hold, no notification
        if risk_index == SCREENING_UNAVAILABLE:
            price_amount = self.tariff_engine.price(w, d)
            self.quote_store.updateQuote(quote_id, "statusHeldUnscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # Accept row (DT-S)
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(w, d)
            self.quote_store.updateQuote(quote_id, "statusQuoted", price_amount)
            self.notification_service.sendQuoteDocument(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # Refuse row (DT-S note 2): notified, no pricing
        if risk_index >= REFUSE_MIN:
            self.quote_store.updateQuote(quote_id, "statusRefusedScreening")
            self.notification_service.sendRefusalNotice(shipper_id, quote_id)
            return {"status": "refused", "quote_id": quote_id}

        # Review row (DT-S note 1): no pricing, no notification
        self.quote_store.updateQuote(quote_id, "statusReviewHold")
        return {"status": "review_hold", "quote_id": quote_id}


# --- Module-level end-to-end entry point ---

def _get(request, *keys, default=None):
    for k in keys:
        if k in request:
            return request[k]
    return default


def handle(request: dict) -> dict:
    # Determine store availability
    store_status = _get(
        request, "store_result", "store_status",
        "quote_store_result", "quote_store_status",
    )
    store_available = True
    if store_status is not None:
        if str(store_status).lower() in ("error", "unavailable", "down"):
            store_available = False

    # Determine screening outcome
    screening_outcome = _get(
        request, "screening_result", "screening_status",
        "screening_service_result", "screening_service_status",
        "risk_index", "risk",
    )

    tariff_engine = TariffEngine()
    quote_store = QuoteStore(available=store_available)
    screening_service = ScreeningService(outcome=screening_outcome)
    notification_service = NotificationService()

    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)

    shipper_id = _get(request, "shipper_id", "shipperId", default="unknown")
    weight_kg = _get(request, "weight_kg", "weightKg", "weight")
    distance_km = _get(request, "distance_km", "distanceKm", "distance")
    declared_value = _get(request, "declared_value", "declaredValue", "value")

    # Existence flag handling for shipper
    shipper_exists = _get(request, "shipper_exists", "shipper_found", default=True)
    if shipper_exists is False:
        return {"status": "rejected", "reason": "shipper_not_found"}

    return api.requestQuote(shipper_id, weight_kg, distance_km, declared_value)