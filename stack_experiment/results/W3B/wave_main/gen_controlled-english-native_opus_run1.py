CONFIG = {
    "WEIGHT_MIN": 1,
    "WEIGHT_MAX": 26000,
    "DISTANCE_MIN": 1,
    "DISTANCE_MAX": 5000,
    "VALUE_MIN": 0,
    "VALUE_MAX": 10_000_000,
    "ACCEPT_MAX": 30,
    "REVIEW_MIN": 31,
    "REVIEW_MAX": 70,
    "REFUSE_MIN": 71,
}

SCREENING_UNAVAILABLE = "screeningUnavailableError"
STORE_UNAVAILABLE = "storeUnavailableError"


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, request=None):
        self._request = request or {}

    def screen(self, shipper_id):
        val = self._request.get("screening_result",
                                self._request.get("screening_status"))
        if val is None:
            return 10
        if isinstance(val, (int, float)):
            return val
        word = str(val).lower()
        if word in ("error", "unavailable", "down", "timeout"):
            return SCREENING_UNAVAILABLE
        if word in ("approved", "active", "accept", "clear", "ok"):
            return 10
        if word in ("review", "hold", "manual"):
            return 50
        if word in ("declined", "refuse", "refused", "denied", "blocked"):
            return 90
        try:
            return float(word)
        except ValueError:
            return 10


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        return "sent"

    def sendRefusalNotice(self, shipper_id, quote_id):
        return "sent"


class TariffEngine:
    """Computes the freight price from weight and distance per the published tariff."""

    BASE = 25.0
    PER_KG = 0.15
    PER_KM = 0.40

    def price(self, weight_kg, distance_km):
        return round(self.BASE + self.PER_KG * weight_kg + self.PER_KM * distance_km, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, request=None):
        self._request = request or {}
        self._seq = 0
        self._records = {}

    def _store_available(self):
        val = self._request.get("store_result",
                                self._request.get("store_status"))
        if val is None:
            return True
        word = str(val).lower()
        return word not in ("error", "unavailable", "down", "fail", "failed")

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._store_available():
            return STORE_UNAVAILABLE
        self._seq += 1
        quote_id = "Q{:06d}".format(self._seq)
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
        return "updated:" + str(quote_id)


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    STATUS_QUOTED = "quoted"
    STATUS_REVIEW_HOLD = "reviewHold"
    STATUS_REFUSED_SCREENING = "refusedScreening"
    STATUS_HELD_UNSCREENED = "heldUnscreened"

    def __init__(self, tariff_engine, quote_store, screening_service,
                 notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
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
        if not (CONFIG["WEIGHT_MIN"] <= w <= CONFIG["WEIGHT_MAX"]):
            return False
        if not (CONFIG["DISTANCE_MIN"] <= d <= CONFIG["DISTANCE_MAX"]):
            return False
        if not (CONFIG["VALUE_MIN"] <= v <= CONFIG["VALUE_MAX"]):
            return False
        return True

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Step 2: validation
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected", "reason": "invalid_request"}

        # Step 2/3: store draft
        quote_id = self.quote_store.storeDraft(shipper_id, weight_kg,
                                               distance_km, declared_value)
        if quote_id == STORE_UNAVAILABLE:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        risk_index = self.screening_service.screen(shipper_id)

        # Step 4d: screening unavailable
        if risk_index == SCREENING_UNAVAILABLE:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, self.STATUS_HELD_UNSCREENED,
                                         price_amount)
            return {"status": "held_unscreened", "quote_id": quote_id,
                    "price": price_amount}

        # Step 4a: accept
        if risk_index <= CONFIG["ACCEPT_MAX"]:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, self.STATUS_QUOTED,
                                         price_amount)
            self._notify_quote(shipper_id, quote_id, price_amount)
            return {"status": "confirmed", "quote_id": quote_id,
                    "price": price_amount, "risk_index": risk_index}

        # Step 4b: review
        if CONFIG["REVIEW_MIN"] <= risk_index <= CONFIG["REVIEW_MAX"]:
            self.quote_store.updateQuote(quote_id, self.STATUS_REVIEW_HOLD)
            return {"status": "review", "quote_id": quote_id,
                    "risk_index": risk_index}

        # Step 4c: refuse
        if risk_index >= CONFIG["REFUSE_MIN"]:
            self.quote_store.updateQuote(quote_id, self.STATUS_REFUSED_SCREENING)
            self._notify_refusal(shipper_id, quote_id)
            return {"status": "refused", "quote_id": quote_id,
                    "risk_index": risk_index}

        # Fallback (gap between bands): treat as review hold
        self.quote_store.updateQuote(quote_id, self.STATUS_REVIEW_HOLD)
        return {"status": "review", "quote_id": quote_id,
                "risk_index": risk_index}

    def _notify_quote(self, shipper_id, quote_id, price_amount):
        # fire-and-forget: delivery failure never changes the response
        try:
            self.notification_service.sendQuoteDocument(shipper_id, quote_id,
                                                        price_amount)
        except Exception:
            pass

    def _notify_refusal(self, shipper_id, quote_id):
        try:
            self.notification_service.sendRefusalNotice(shipper_id, quote_id)
        except Exception:
            pass


class Shipper:
    """A logistics customer requesting a price quote."""

    def __init__(self, quote_api):
        self.quote_api = quote_api

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value):
        return self.quote_api.requestQuote(shipper_id, weight_kg,
                                           distance_km, declared_value)


def handle(request: dict) -> dict:
    request = request or {}

    screening_service = ScreeningService(request)
    notification_service = NotificationService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore(request)
    quote_api = QuoteApi(tariff_engine, quote_store, screening_service,
                         notification_service)
    shipper = Shipper(quote_api)

    shipper_id = request.get("shipper_id", request.get("shipperId"))
    if request.get("shipper_exists") is False or request.get("shipper_found") is False:
        return {"status": "rejected", "reason": "unknown_shipper"}

    weight_kg = request.get("weight_kg", request.get("weightKg", 0))
    distance_km = request.get("distance_km", request.get("distanceKm", 0))
    declared_value = request.get("declared_value",
                                 request.get("declaredValue", 0))

    try:
        return shipper.requestQuote(shipper_id, weight_kg, distance_km,
                                    declared_value)
    except Exception as exc:
        return {"status": "error: " + str(exc)}