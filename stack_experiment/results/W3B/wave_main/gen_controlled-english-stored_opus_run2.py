SCREEN_ACCEPT_MAX = 30
SCREEN_REVIEW_MIN = 31
SCREEN_REVIEW_MAX = 69
SCREEN_REFUSE_MIN = 70

WEIGHT_MIN = 1
WEIGHT_MAX = 26000
DISTANCE_MIN = 1
DISTANCE_MAX = 3000
VALUE_MIN = 1
VALUE_MAX = 10_000_000

SCREENING_UNAVAILABLE = "screening_unavailable"
STORE_UNAVAILABLE = "store_unavailable"


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, outcome="approved"):
        self.outcome = outcome

    def screen(self, shipper_id):
        outcome = self.outcome
        if isinstance(outcome, (int, float)):
            return outcome
        word = str(outcome).lower()
        if word in ("error", "unavailable", "down", "screening_unavailable"):
            return SCREENING_UNAVAILABLE
        if word in ("approved", "accept", "accepted", "clear", "active"):
            return 10
        if word in ("review", "hold", "manual", "assessed"):
            return 50
        if word in ("declined", "refused", "refuse", "denied", "lapsed"):
            return 90
        # default: treat as accept
        return 10


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, outcome="sent"):
        self.outcome = outcome

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        # fire-and-forget; failures never change the response
        return "queued"

    def sendRefusalNotice(self, shipper_id, quote_id):
        # fire-and-forget; failures never change the response
        return "queued"


class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG_KM = 0.0004

    def price(self, weight_kg, distance_km):
        return round(self.BASE_FEE + self.RATE_PER_KG_KM * weight_kg * distance_km, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self.available = available
        self._seq = 0
        self.records = {}

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self.available:
            return STORE_UNAVAILABLE
        self._seq += 1
        quote_id = "Q%04d" % self._seq
        self.records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def updateQuote(self, quote_id, status, price_amount=None):
        rec = self.records.get(quote_id)
        if rec is not None:
            rec["status"] = status
            if price_amount is not None:
                rec["price"] = price_amount
        return "updated:" + str(quote_id)


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, store, screening, tariff, notification):
        self.store = store
        self.screening = screening
        self.tariff = tariff
        self.notification = notification

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
        # Step 2: validation (DT-V)
        if not shipper_id or not self._valid(weight_kg, distance_km, declared_value):
            return {"status": "rejectedInvalidRequest"}

        # Step 2/3: store draft
        quote_id = self.store.storeDraft(shipper_id, weight_kg, distance_km, declared_value)
        if quote_id == STORE_UNAVAILABLE:
            # Nothing else runs (DT-S note 3)
            return {"status": "storeUnavailableError"}

        # Step 3: screening
        risk_index = self.screening.screen(shipper_id)

        # Step 4d: screening outage
        if risk_index == SCREENING_UNAVAILABLE:
            price_amount = self.tariff.price(weight_kg, distance_km)
            self.store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "heldUnscreenedResponse",
                "quoteId": quote_id,
                "price": price_amount,
            }

        # Step 4a: accept
        if risk_index <= SCREEN_ACCEPT_MAX:
            price_amount = self.tariff.price(weight_kg, distance_km)
            self.store.updateQuote(quote_id, "quoted", price_amount)
            self.notification.sendQuoteDocument(shipper_id, quote_id, price_amount)
            return {
                "status": "quotedResponse",
                "quoteId": quote_id,
                "price": price_amount,
            }

        # Step 4b: review hold
        if SCREEN_REVIEW_MIN <= risk_index <= SCREEN_REVIEW_MAX:
            self.store.updateQuote(quote_id, "review_hold")
            return {"status": "reviewHoldResponse", "quoteId": quote_id}

        # Step 4c: refuse
        if risk_index >= SCREEN_REFUSE_MIN:
            self.store.updateQuote(quote_id, "refused_screening")
            self.notification.sendRefusalNotice(shipper_id, quote_id)
            return {"status": "refusedScreeningResponse", "quoteId": quote_id}

        # Fallback (should not normally reach)
        return {"status": "error: unclassified_risk"}


def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = request.get("shipper_id") or request.get("shipperId")
    shipper_exists = request.get("shipper_exists", request.get("shipper_found", True))
    if not shipper_exists:
        shipper_id = None

    weight_kg = request.get("weight_kg", request.get("weightKg", 0))
    distance_km = request.get("distance_km", request.get("distanceKm", 0))
    declared_value = request.get("declared_value", request.get("declaredValue", 0))

    # Store availability
    store_outcome = request.get("store_result", request.get("store_status", "stored"))
    store_available = str(store_outcome).lower() not in ("error", "unavailable", "down")

    # Screening outcome
    screening_outcome = request.get(
        "screening_result", request.get("screening_status", "approved")
    )

    # Notification outcome
    notification_outcome = request.get(
        "notification_result", request.get("notification_status", "sent")
    )

    store = QuoteStore(available=store_available)
    screening = ScreeningService(outcome=screening_outcome)
    tariff = TariffEngine()
    notification = NotificationService(outcome=notification_outcome)

    api = QuoteApi(store, screening, tariff, notification)

    try:
        return api.requestQuote(shipper_id, weight_kg, distance_km, declared_value)
    except Exception as exc:  # pragma: no cover
        return {"status": "error: " + str(exc)}