import math


ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70

WEIGHT_MIN, WEIGHT_MAX = 1, 26000
DISTANCE_MIN, DISTANCE_MAX = 1, 3000
VALUE_MIN, VALUE_MAX = 1, 1_000_000


class ValidationError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, context=None):
        self.context = context or {}

    def screen(self, shipper_id):
        raw = self.context.get("screening_result",
                               self.context.get("screening_status", "approved"))
        if isinstance(raw, (int, float)):
            return float(raw)
        word = str(raw).strip().lower()
        if word in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailableError("screening service unavailable")
        if word in ("approved", "accept", "clear", "active", "low"):
            return 10.0
        if word in ("review", "hold", "assessed", "medium"):
            return 50.0
        if word in ("declined", "refuse", "refused", "denied", "high"):
            return 90.0
        try:
            return float(word)
        except ValueError:
            return 10.0


class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    BASE_FEE = 25.0
    PER_KG = 0.15
    PER_KM = 0.40

    def price(self, weight_kg, distance_km):
        return round(self.BASE_FEE
                     + self.PER_KG * float(weight_kg)
                     + self.PER_KM * float(distance_km), 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, context=None):
        self.context = context or {}
        self._seq = 0
        self._records = {}

    def _available(self):
        raw = str(self.context.get("store_result",
                                   self.context.get("store_status", "stored"))).strip().lower()
        return raw not in ("error", "unavailable", "down", "fail", "failure")

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._available():
            raise StoreUnavailableError("quote store unavailable")
        self._seq += 1
        quote_id = "Q%04d" % self._seq
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "Draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price=None):
        rec = self._records.get(quote_id, {})
        rec["status"] = status
        if price is not None:
            rec["price"] = price
        self._records[quote_id] = rec
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, request, weight_kg, distance_km, declared_value):
        shipper_exists = request.get("shipper_exists",
                                     request.get("shipper_found", True))
        if not shipper_exists:
            raise ValidationError("unknown shipper")
        for name, val in (("weight", weight_kg),
                          ("distance", distance_km),
                          ("declared_value", declared_value)):
            if val is None or not isinstance(val, (int, float)):
                raise ValidationError("missing %s" % name)
        if not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            raise ValidationError("weight out of bounds")
        if not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            raise ValidationError("distance out of bounds")
        if not (VALUE_MIN <= declared_value <= VALUE_MAX):
            raise ValidationError("declared value out of bounds")

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value, request):
        # Validation per DT-V
        try:
            self._validate(request, weight_kg, distance_km, declared_value)
        except ValidationError as exc:
            return {"status": "rejected", "reason": str(exc)}

        # Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError as exc:
            # DT-S note 3: nothing else runs
            return {"status": "error: store_unavailable", "reason": str(exc)}

        # Screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: priced, stored on hold, not notified
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "HeldUnscreened", price_amount)
            return {"status": "held_unscreened",
                    "quote_id": quote_id,
                    "price": price_amount}

        # Decision per DT-S
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "Quoted", price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount)  # fire-and-forget
            return {"status": "quoted",
                    "quote_id": quote_id,
                    "price": price_amount,
                    "risk_index": risk_index}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # DT-S note 1: no pricing, no notification
            self.quote_store.update_quote(quote_id, "ReviewHold")
            return {"status": "review_hold",
                    "quote_id": quote_id,
                    "risk_index": risk_index}
        else:  # risk_index >= REFUSE_MIN
            # DT-S note 2: refusal IS notified, pricing never runs
            self.quote_store.update_quote(quote_id, "RefusedScreening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused",
                    "quote_id": quote_id,
                    "risk_index": risk_index}


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "unknown")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    tariff_engine = TariffEngine()
    quote_store = QuoteStore(context=request)
    screening_service = ScreeningService(context=request)
    notification_service = NotificationService()

    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)

    try:
        return api.request_quote(shipper_id, weight_kg, distance_km,
                                 declared_value, request)
    except Exception as exc:  # pragma: no cover
        return {"status": "error: %s" % exc}