SCREENING_UNAVAILABLE = "screeningUnavailableError"
STORE_UNAVAILABLE = "storeUnavailableError"

# Screening decision thresholds (DT-S)
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

# Validation bounds (DT-V)
WEIGHT_MIN = 0.0
WEIGHT_MAX = 30000.0
DISTANCE_MIN = 0.0
DISTANCE_MAX = 5000.0
VALUE_MIN = 0.0
VALUE_MAX = 10_000_000.0


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, outcome=None):
        self._outcome = outcome

    def screen(self, shipper_id):
        # Returns a single value: a numeric risk index, or an error sentinel.
        outcome = self._outcome
        if outcome is None:
            return 10
        if isinstance(outcome, (int, float)):
            return outcome
        text = str(outcome).strip().lower()
        if text in ("error", "unavailable", "down", "timeout"):
            return SCREENING_UNAVAILABLE
        if text in ("approved", "accept", "accepted", "clear", "active", "assessed"):
            return 10
        if text in ("review", "hold", "manual"):
            return 50
        if text in ("declined", "refuse", "refused", "denied", "blocked"):
            return 90
        try:
            return float(text)
        except ValueError:
            return 10


class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    BASE_FEE = 25.0
    PER_KG = 0.15
    PER_KM = 0.40

    def price(self, weight_kg, distance_km):
        # Returns a single value: the price amount.
        amount = self.BASE_FEE + self.PER_KG * weight_kg + self.PER_KM * distance_km
        return round(amount, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self._available = available
        self._records = {}
        self._counter = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        # Returns a single value: a quoteId, or an error sentinel.
        if not self._available:
            return STORE_UNAVAILABLE
        self._counter += 1
        quote_id = "Q%04d" % self._counter
        self._records[quote_id] = {
            "shipperId": shipper_id,
            "weightKg": weight_kg,
            "distanceKm": distance_km,
            "declaredValue": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        # Returns a single value: a confirmation (the updated quote id).
        record = self._records.get(quote_id)
        if record is not None:
            record["status"] = status
            if price_amount is not None:
                record["price"] = price_amount
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        # Fire-and-forget; returns a single value.
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        # Fire-and-forget; returns a single value.
        return "sent"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
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
        if not (WEIGHT_MIN < w <= WEIGHT_MAX):
            return False
        if not (DISTANCE_MIN < d <= DISTANCE_MAX):
            return False
        if not (VALUE_MIN < v <= VALUE_MAX):
            return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Step 2: validate
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejectedInvalidRequest"}

        # Step 2: store draft
        quote_id = self.quote_store.store_draft(
            shipper_id, weight_kg, distance_km, declared_value
        )
        if quote_id == STORE_UNAVAILABLE:
            # DT-S note 3: nothing else runs
            return {"status": "storeUnavailableError"}

        # Step 3: screening
        risk_index = self.screening_service.screen(shipper_id)

        # Step 4d: screening failed
        if risk_index == SCREENING_UNAVAILABLE:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "heldUnscreened", price_amount)
            return {
                "status": "heldUnscreenedResponse",
                "quoteId": quote_id,
                "price": price_amount,
            }

        # Step 4a: accept
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount
            )
            return {
                "status": "quotedResponse",
                "quoteId": quote_id,
                "price": price_amount,
            }

        # Step 4b: review
        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "reviewHold")
            return {"status": "reviewHoldResponse", "quoteId": quote_id}

        # Step 4c: refuse
        if risk_index >= REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refusedScreening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refusedScreeningResponse", "quoteId": quote_id}

        # Fallback (gap between bands) — treat as review hold
        self.quote_store.update_quote(quote_id, "reviewHold")
        return {"status": "reviewHoldResponse", "quoteId": quote_id}


def _store_available(request):
    if request.get("quote_store_result") in ("error", "unavailable"):
        return False
    if request.get("quote_store_status") in ("error", "unavailable"):
        return False
    if request.get("store_result") in ("error", "unavailable"):
        return False
    if request.get("quote_store_exists") is False:
        return False
    if request.get("store_exists") is False:
        return False
    return True


def _screening_outcome(request):
    for key in ("screening_result", "screening_status", "screening_service_result",
                "screening_service_status"):
        if key in request:
            return request[key]
    if "risk_index" in request:
        return request["risk_index"]
    return None


def handle(request: dict) -> dict:
    try:
        shipper_id = request.get("shipper_id", request.get("shipperId"))
        weight_kg = request.get("weight_kg", request.get("weightKg"))
        distance_km = request.get("distance_km", request.get("distanceKm"))
        declared_value = request.get("declared_value", request.get("declaredValue"))

        quote_store = QuoteStore(available=_store_available(request))
        screening_service = ScreeningService(outcome=_screening_outcome(request))
        tariff_engine = TariffEngine()
        notification_service = NotificationService()

        api = QuoteApi(quote_store, screening_service, tariff_engine, notification_service)
        return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    except Exception as exc:  # pragma: no cover
        return {"status": "error: %s" % exc}