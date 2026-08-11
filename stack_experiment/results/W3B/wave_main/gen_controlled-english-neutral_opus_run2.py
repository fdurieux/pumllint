from typing import Any

ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70

WEIGHT_MIN = 1
WEIGHT_MAX = 30000
DISTANCE_MIN = 1
DISTANCE_MAX = 5000
VALUE_MIN = 1
VALUE_MAX = 10_000_000


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, result: Any = None):
        self._result = result

    def screen(self, shipper_id):
        # Returns a single value: the risk index, or the string
        # "screeningUnavailableError" when the service is unavailable.
        if self._result is None:
            return 0
        if isinstance(self._result, str):
            word = self._result.strip().lower()
            if word in ("error", "unavailable", "down"):
                return "screeningUnavailableError"
            if word in ("accept", "approved", "clear"):
                return ACCEPT_MAX
            if word in ("review", "assessed", "hold"):
                return REVIEW_MIN
            if word in ("refuse", "declined", "denied"):
                return REFUSE_MIN
            try:
                return int(word)
            except ValueError:
                return 0
        return self._result


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        return "sent"

    def sendRefusalNotice(self, shipper_id, quote_id):
        return "sent"


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff."""

    BASE_RATE = 0.5
    DISTANCE_RATE = 0.1

    def price(self, weight_kg, distance_km):
        return round(weight_kg * self.BASE_RATE + distance_km * self.DISTANCE_RATE, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available: bool = True):
        self._available = available
        self._counter = 0
        self._records = {}

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value):
        # Returns a single value: quoteId, or storeUnavailableError.
        if not self._available:
            return "storeUnavailableError"
        self._counter += 1
        quote_id = "Q%04d" % self._counter
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
        rec = self._records.get(quote_id, {})
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        self._records[quote_id] = rec
        return "updated:" + status


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening
    and pricing, and returns the quotation outcome."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _valid(self, weight_kg, distance_km, declared_value):
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

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Step 2: validate.
        if not shipper_id or not self._valid(weight_kg, distance_km, declared_value):
            return {"status": "rejectedInvalidRequest"}

        # Step 2/3: store draft.
        quote_id = self.quote_store.storeDraft(
            shipper_id, weight_kg, distance_km, declared_value
        )
        if quote_id == "storeUnavailableError":
            return {"status": "storeUnavailableError"}

        # Step 3: screen.
        risk_index = self.screening_service.screen(shipper_id)

        # Step 4d: screening failure.
        if risk_index == "screeningUnavailableError":
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "statusHeldUnscreened", price_amount)
            return {
                "status": "heldUnscreenedResponse",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # Step 4a: accept.
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "statusQuoted", price_amount)
            self.notification_service.sendQuoteDocument(shipper_id, quote_id, price_amount)
            return {
                "status": "quotedResponse",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # Step 4b: review.
        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "statusReviewHold")
            return {"status": "reviewHoldResponse", "quote_id": quote_id}

        # Step 4c: refuse.
        if risk_index >= REFUSE_MIN:
            self.quote_store.updateQuote(quote_id, "statusRefusedScreening")
            self.notification_service.sendRefusalNotice(shipper_id, quote_id)
            return {"status": "refusedScreeningResponse", "quote_id": quote_id}

        # Fallback (gap between accept and review bands).
        self.quote_store.updateQuote(quote_id, "statusReviewHold")
        return {"status": "reviewHoldResponse", "quote_id": quote_id}


def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = request.get("shipper_id") or request.get("shipperId")
    shipper_exists = request.get("shipper_exists", True) and request.get(
        "shipper_found", True
    )
    if not shipper_exists:
        shipper_id = None

    weight_kg = request.get("weight_kg", request.get("weightKg"))
    distance_km = request.get("distance_km", request.get("distanceKm"))
    declared_value = request.get("declared_value", request.get("declaredValue"))

    # Store availability.
    store_result = request.get("store_result", request.get("store_status"))
    store_available = True
    if isinstance(store_result, str) and store_result.strip().lower() in (
        "error",
        "unavailable",
        "down",
    ):
        store_available = False
    if request.get("store_exists") is False:
        store_available = False

    screening_result = request.get(
        "screening_result",
        request.get("screening_status", request.get("screening_service_result")),
    )

    tariff_engine = TariffEngine()
    quote_store = QuoteStore(available=store_available)
    screening_service = ScreeningService(result=screening_result)
    notification_service = NotificationService()

    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)

    try:
        return api.requestQuote(shipper_id, weight_kg, distance_km, declared_value)
    except Exception as exc:  # pragma: no cover
        return {"status": "error: " + str(exc)}