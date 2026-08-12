import uuid


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, risk_override=None, status=None):
        if status in ("error", "unavailable", "screeningUnavailableError"):
            return "screeningUnavailableError"
        if risk_override is not None:
            return risk_override
        return 10


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        return "sent"

    def sendRefusalNotice(self, shipper_id, quote_id):
        return "sent"


class TariffEngine:
    """Computes the freight price from weight and distance per published tariff."""

    BASE_FEE = 25.0
    RATE_PER_KG_KM = 0.0005

    def price(self, weight_kg, distance_km):
        return round(self.BASE_FEE + self.RATE_PER_KG_KM * weight_kg * distance_km, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value, status=None):
        if status in ("error", "unavailable", "storeUnavailableError"):
            return "storeUnavailableError"
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
            return "updateFailed"
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        return "updatedQuote"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    # DT-V validation bounds
    MIN_WEIGHT = 1
    MAX_WEIGHT = 26000
    MIN_DISTANCE = 1
    MAX_DISTANCE = 5000
    MIN_VALUE = 1
    MAX_VALUE = 10_000_000

    # DT-S screening thresholds
    ACCEPT_MAX = 30
    REVIEW_MIN = 31
    REVIEW_MAX = 70
    REFUSE_MIN = 71

    def __init__(self, store=None, screening=None, tariff=None, notification=None):
        self.store = store or QuoteStore()
        self.screening = screening or ScreeningService()
        self.tariff = tariff or TariffEngine()
        self.notification = notification or NotificationService()

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            return False
        for value, lo, hi in (
            (weight_kg, self.MIN_WEIGHT, self.MAX_WEIGHT),
            (distance_km, self.MIN_DISTANCE, self.MAX_DISTANCE),
            (declared_value, self.MIN_VALUE, self.MAX_VALUE),
        ):
            if value is None:
                return False
            try:
                v = float(value)
            except (TypeError, ValueError):
                return False
            if v < lo or v > hi:
                return False
        return True

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value,
                     store_status=None, screening_status=None, risk_index=None):
        # Step 2: validation (DT-V)
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejectedInvalidRequest"}

        # Step 2/3: store draft
        quote_id = self.store.storeDraft(
            shipper_id, weight_kg, distance_km, declared_value, status=store_status
        )
        if quote_id == "storeUnavailableError":
            return {"status": "storeUnavailableError"}

        # Step 3: screening
        risk = self.screening.screen(
            shipper_id, risk_override=risk_index, status=screening_status
        )

        # Step 4d: screening failure
        if risk == "screeningUnavailableError":
            price_amount = self.tariff.price(weight_kg, distance_km)
            self.store.updateQuote(quote_id, "statusHeldUnscreened", price_amount)
            return {
                "status": "heldUnscreenedResponse",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # Step 4a: accept
        if risk <= self.ACCEPT_MAX:
            price_amount = self.tariff.price(weight_kg, distance_km)
            self.store.updateQuote(quote_id, "statusQuoted", price_amount)
            self.notification.sendQuoteDocument(shipper_id, quote_id, price_amount)
            return {
                "status": "quotedResponse",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # Step 4b: review hold
        if self.REVIEW_MIN <= risk <= self.REVIEW_MAX:
            self.store.updateQuote(quote_id, "statusReviewHold")
            return {"status": "reviewHoldResponse", "quote_id": quote_id}

        # Step 4c: refuse
        if risk >= self.REFUSE_MIN:
            self.store.updateQuote(quote_id, "statusRefusedScreening")
            self.notification.sendRefusalNotice(shipper_id, quote_id)
            return {"status": "refusedScreeningResponse", "quote_id": quote_id}

        # Fallback
        return {"status": "error: unclassified_risk"}


def _coerce_number(value):
    if value is None:
        return None
    try:
        if isinstance(value, str):
            return float(value)
        return value
    except (TypeError, ValueError):
        return value


def handle(request: dict) -> dict:
    api = QuoteApi()

    shipper_id = request.get("shipper_id") or request.get("shipperId")
    if request.get("shipper_exists") is False or request.get("shipper_found") is False:
        shipper_id = None

    weight_kg = _coerce_number(request.get("weight_kg", request.get("weightKg")))
    distance_km = _coerce_number(request.get("distance_km", request.get("distanceKm")))
    declared_value = _coerce_number(
        request.get("declared_value", request.get("declaredValue"))
    )

    store_status = request.get("store_result", request.get("store_status"))

    screening_status = request.get("screening_result", request.get("screening_status"))
    risk_index = None
    if screening_status is not None:
        if isinstance(screening_status, (int, float)) and not isinstance(
            screening_status, bool
        ):
            risk_index = screening_status
            screening_status = None
        elif isinstance(screening_status, str):
            try:
                risk_index = float(screening_status)
                screening_status = None
            except ValueError:
                pass

    try:
        return api.requestQuote(
            shipper_id,
            weight_kg,
            distance_km,
            declared_value,
            store_status=store_status,
            screening_status=screening_status,
            risk_index=risk_index,
        )
    except Exception as exc:  # noqa: BLE001
        return {"status": f"error: {exc}"}