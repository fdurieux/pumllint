import math


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000

HEAVY_THRESHOLD = 1244
HEAVY_SURCHARGE = 316.00
LONGHAUL_THRESHOLD = 4912
LONGHAUL_MULTIPLIER = 1.19

ERROR_WORDS = {"error", "unavailable", "down", "outage", "fail", "failure"}


class ScreeningUnavailable(Exception):
    pass


class StoreUnavailable(Exception):
    pass


class ValidationError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, context=None):
        context = context or {}
        status = str(context.get("screening_status", "")).lower()
        result = context.get("screening_result", context.get("risk_index"))
        if status in ERROR_WORDS or (isinstance(result, str) and result.lower() in ERROR_WORDS):
            raise ScreeningUnavailable("screening service unavailable")
        if isinstance(result, bool):
            result = None
        if isinstance(result, (int, float)):
            return int(result)
        if isinstance(result, str):
            word = result.lower()
            if word in ("approved", "accept", "clear", "clean"):
                return 10
            if word in ("review", "hold"):
                return 50
            if word in ("declined", "refuse", "refused", "denied"):
                return 90
        return 10


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount, context=None):
        return self._deliver(context)

    def sendRefusalNotice(self, shipper_id, quote_id, context=None):
        return self._deliver(context)

    def _deliver(self, context):
        context = context or {}
        status = str(context.get("notification_status", context.get("notification_result", ""))).lower()
        if status in ERROR_WORDS:
            raise RuntimeError("notification delivery failed")
        return "delivered"


class TariffEngine:
    """Computes the freight price per the published tariff rules (DT-P)."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > HEAVY_THRESHOLD:
            result += HEAVY_SURCHARGE
        if distance_km >= LONGHAUL_THRESHOLD:
            result *= LONGHAUL_MULTIPLIER
        return round(result, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._counter = 0

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value, context=None):
        context = context or {}
        status = str(context.get("store_status", context.get("store_result", ""))).lower()
        if status in ERROR_WORDS:
            raise StoreUnavailable("quote store unavailable")
        self._counter += 1
        quote_id = "Q-{:06d}".format(self._counter)
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def updateQuote(self, quote_id, status, price=None):
        record = self._records.get(quote_id)
        if record is None:
            record = {"status": None, "price": None}
            self._records[quote_id] = record
        record["status"] = status
        if price is not None:
            record["price"] = price
        return quote_id


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            raise ValidationError("shipper_id")
        weight = request.get("weight_kg")
        if not self._is_number(weight) or not (WEIGHT_MIN <= weight <= WEIGHT_MAX):
            raise ValidationError("weight_kg")
        distance = request.get("distance_km")
        if not self._is_number(distance) or not (DISTANCE_MIN <= distance <= DISTANCE_MAX):
            raise ValidationError("distance_km")
        value = request.get("declared_value")
        if not self._is_number(value) or not (VALUE_MIN <= value <= VALUE_MAX):
            raise ValidationError("declared_value")

    @staticmethod
    def _is_number(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def requestQuote(self, request):
        # Step 1: validate
        try:
            self._validate(request)
        except ValidationError:
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]

        # Step 2: store draft
        try:
            quote_id = self.quote_store.storeDraft(
                shipper_id, weight_kg, distance_km, declared_value, request
            )
        except StoreUnavailable:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id, request)
        except ScreeningUnavailable:
            # Screening outage: price anyway, hold, no notification
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4/5/6: screening decision
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price_amount)
            self._notify(
                self.notification_service.sendQuoteDocument,
                shipper_id, quote_id, price_amount, request,
            )
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # risk_index >= REFUSE_MIN
        self.quote_store.updateQuote(quote_id, "refused_screening")
        self._notify_refusal(shipper_id, quote_id, request)
        return {"status": "refused_screening", "quote_id": quote_id}

    def _notify(self, fn, shipper_id, quote_id, price_amount, request):
        try:
            fn(shipper_id, quote_id, price_amount, request)
        except Exception:
            pass  # fire-and-forget

    def _notify_refusal(self, shipper_id, quote_id, request):
        try:
            self.notification_service.sendRefusalNotice(shipper_id, quote_id, request)
        except Exception:
            pass  # fire-and-forget


def handle(request: dict) -> dict:
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)
    return api.requestQuote(request or {})