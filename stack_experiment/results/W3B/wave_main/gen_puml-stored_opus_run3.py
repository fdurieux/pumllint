class ScreeningUnavailableError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class InvalidRequestError(Exception):
    pass


# Screening thresholds (decision table DT-S)
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70

# Validation bounds (decision table DT-V)
WEIGHT_MIN = 1
WEIGHT_MAX = 26000
DISTANCE_MIN = 1
DISTANCE_MAX = 5000
VALUE_MIN = 0
VALUE_MAX = 10_000_000


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
        text = str(outcome).strip().lower()
        if text in ("error", "unavailable", "timeout", "down"):
            raise ScreeningUnavailableError("screening service unavailable")
        if text in ("approved", "accept", "clear", "active"):
            return 10
        if text in ("review", "hold", "assessed"):
            return 50
        if text in ("declined", "refuse", "denied", "blocked"):
            return 90
        try:
            return float(text)
        except ValueError:
            return 0


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff rules."""

    BASE_RATE = 25.0
    PER_KG = 0.15
    PER_KM = 0.40

    def price(self, weight_kg, distance_km):
        amount = self.BASE_RATE + (weight_kg * self.PER_KG) + (distance_km * self.PER_KM)
        return round(amount, 2)


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
            "shipperId": shipper_id,
            "weightKg": weight_kg,
            "distanceKm": distance_km,
            "declaredValue": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def updateQuote(self, quote_id, status, price=None):
        if not self._available:
            raise StoreUnavailableError("quote store unavailable")
        record = self._records.get(quote_id, {})
        record["status"] = status
        if price is not None:
            record["price"] = price
        self._records[quote_id] = record
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        return "delivered"

    def sendRefusalNotice(self, shipper_id, quote_id):
        return "delivered"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            raise InvalidRequestError("missing shipperId")
        if not isinstance(weight_kg, (int, float)) or not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            raise InvalidRequestError("weight out of bounds")
        if not isinstance(distance_km, (int, float)) or not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            raise InvalidRequestError("distance out of bounds")
        if not isinstance(declared_value, (int, float)) or not (VALUE_MIN <= declared_value <= VALUE_MAX):
            raise InvalidRequestError("declared value out of bounds")

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Validation (DT-V)
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except InvalidRequestError as exc:
            return {"status": "rejected: invalid_request", "reason": str(exc)}

        # Store draft
        try:
            quote_id = self.quote_store.storeDraft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError as exc:
            # DT-S note 3: nothing else runs on storage failure
            return {"status": "error: store_unavailable", "reason": str(exc)}

        # Screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: screening outage does not fail the quote
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quoteId": quote_id,
                "price": price_amount,
            }

        # Accept row
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price_amount)
            self.notification_service.sendQuoteDocument(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quoteId": quote_id,
                "price": price_amount,
                "riskIndex": risk_index,
            }

        # Refuse row
        if risk_index >= REFUSE_MIN:
            self.quote_store.updateQuote(quote_id, "refused_screening")
            self.notification_service.sendRefusalNotice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quoteId": quote_id,
                "riskIndex": risk_index,
            }

        # Review row (REVIEW_MIN <= riskIndex <= REVIEW_MAX)
        self.quote_store.updateQuote(quote_id, "review_hold")
        return {
            "status": "review_hold",
            "quoteId": quote_id,
            "riskIndex": risk_index,
        }


def _first(request, *keys, default=None):
    for key in keys:
        if key in request and request[key] is not None:
            return request[key]
    return default


def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = _first(request, "shipper_id", "shipperId", default="")
    weight_kg = _first(request, "weight_kg", "weightKg", "weight", default=0)
    distance_km = _first(request, "distance_km", "distanceKm", "distance", default=0)
    declared_value = _first(
        request, "declared_value", "declaredValue", "value", default=0
    )

    # Existence flags — a missing/unknown shipper is an invalid request.
    if request.get("shipper_exists") is False or request.get("shipper_found") is False:
        shipper_id = ""

    # Store availability
    store_result = _first(request, "store_result", "store_status", "quote_store_result")
    store_available = True
    if store_result is not None:
        store_available = str(store_result).strip().lower() in ("stored", "ok", "available", "success")

    # Screening outcome
    screening_outcome = _first(
        request, "screening_result", "screening_status", "screening_service_result"
    )

    screening_service = ScreeningService(outcome=screening_outcome)
    tariff_engine = TariffEngine()
    quote_store = QuoteStore(available=store_available)
    notification_service = NotificationService()

    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)

    return api.requestQuote(shipper_id, weight_kg, distance_km, declared_value)