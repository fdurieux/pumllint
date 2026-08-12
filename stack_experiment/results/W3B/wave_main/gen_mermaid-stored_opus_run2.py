class ScreeningError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ValidationError(Exception):
    pass


# --- Decision table thresholds (DT-S) ---
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

# --- Validation bounds (DT-V) ---
WEIGHT_MIN, WEIGHT_MAX = 1, 30000
DISTANCE_MIN, DISTANCE_MAX = 1, 5000
VALUE_MIN = 1


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, outcome=None):
        self._outcome = outcome

    def screen(self, shipper_id):
        outcome = self._outcome
        if outcome is None:
            return 0
        if isinstance(outcome, (int, float)):
            return outcome
        word = str(outcome).lower()
        if word in ("error", "unavailable", "down", "timeout"):
            raise ScreeningError("screening service unavailable")
        if word in ("approved", "active", "clear", "accept"):
            return 0
        if word in ("assessed", "review", "hold"):
            return 50
        if word in ("declined", "refused", "denied", "refuse"):
            return 90
        # default: try to treat as number
        try:
            return float(word)
        except ValueError:
            return 0


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        return "queued"

    def sendRefusalNotice(self, shipper_id, quote_id):
        return "queued"


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff rules."""

    BASE_RATE = 25.0
    PER_KG = 0.15
    PER_KM = 0.40

    def price(self, weight_kg, distance_km):
        return round(self.BASE_RATE + self.PER_KG * weight_kg + self.PER_KM * distance_km, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self._available = available
        self._records = {}
        self._seq = 0

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._available:
            raise StoreUnavailableError("quote store unavailable")
        self._seq += 1
        quote_id = "Q-%04d" % self._seq
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
        if not self._available:
            raise StoreUnavailableError("quote store unavailable")
        rec = self._records.get(quote_id)
        if rec is None:
            rec = {}
            self._records[quote_id] = rec
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        return quote_id


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            raise ValidationError("missing shipper id")
        if not isinstance(weight_kg, (int, float)) or not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            raise ValidationError("weight out of bounds")
        if not isinstance(distance_km, (int, float)) or not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            raise ValidationError("distance out of bounds")
        if not isinstance(declared_value, (int, float)) or declared_value < VALUE_MIN:
            raise ValidationError("declared value out of bounds")

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Validation (DT-V)
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as exc:
            return {"status": "rejected", "reason": str(exc)}

        # Store draft
        try:
            quote_id = self.quote_store.storeDraft(shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError as exc:
            return {"status": "error: store_unavailable", "reason": str(exc)}

        # Screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            # DT-S note 5: outage does not fail the quote — price and hold
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # Decision table DT-S
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price_amount)
            self.notification_service.sendQuoteDocument(shipper_id, quote_id, price_amount)
            return {
                "status": "confirmed",
                "quote_id": quote_id,
                "price": price_amount,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.updateQuote(quote_id, "refused_screening")
            self.notification_service.sendRefusalNotice(shipper_id, quote_id)
            return {"status": "refused", "quote_id": quote_id}


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", request.get("shipperId"))

    weight_kg = request.get("weight_kg", request.get("weightKg"))
    distance_km = request.get("distance_km", request.get("distanceKm"))
    declared_value = request.get("declared_value", request.get("declaredValue"))

    # Store availability
    store_status = request.get("store_result", request.get("store_status", "stored"))
    store_available = str(store_status).lower() not in ("error", "unavailable", "down")

    # Screening outcome
    screening_outcome = request.get("screening_result", request.get("screening_status"))

    tariff_engine = TariffEngine()
    quote_store = QuoteStore(available=store_available)
    screening_service = ScreeningService(outcome=screening_outcome)
    notification_service = NotificationService()

    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)

    return api.requestQuote(shipper_id, weight_kg, distance_km, declared_value)