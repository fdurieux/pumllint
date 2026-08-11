import math


ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

WEIGHT_MIN = 1
WEIGHT_MAX = 30000
DISTANCE_MIN = 1
DISTANCE_MAX = 5000
VALUE_MIN = 1
VALUE_MAX = 10_000_000


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, risk_hint=None):
        if risk_hint is None:
            return 10
        if isinstance(risk_hint, str):
            mapping = {
                "approved": 10,
                "accept": 10,
                "low": 10,
                "review": 50,
                "hold": 50,
                "declined": 90,
                "refuse": 90,
                "high": 90,
            }
            if risk_hint == "error":
                raise ScreeningUnavailableError("screening service unavailable")
            return mapping.get(risk_hint, 10)
        return risk_hint


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff."""

    BASE = 25.0
    PER_KG = 0.15
    PER_KM = 0.40

    def price(self, weight_kg, distance_km):
        amount = self.BASE + self.PER_KG * weight_kg + self.PER_KM * distance_km
        return round(amount, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, available=True):
        if not available:
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

    def update_quote(self, quote_id, status, price_amount=None):
        rec = self._records.get(quote_id)
        if rec is None:
            raise StoreUnavailableError("unknown quote")
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class ValidationError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            raise ValidationError("missing shipper")
        for name, val, lo, hi in (
            ("weight", weight_kg, WEIGHT_MIN, WEIGHT_MAX),
            ("distance", distance_km, DISTANCE_MIN, DISTANCE_MAX),
            ("value", declared_value, VALUE_MIN, VALUE_MAX),
        ):
            if not isinstance(val, (int, float)):
                raise ValidationError("invalid %s" % name)
            if val < lo or val > hi:
                raise ValidationError("out of bounds %s" % name)

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value,
                      store_available=True, risk_hint=None):
        # Step 2: validation
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": "rejectedInvalidRequest", "reason": str(e)}

        # Step 2/3: store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, available=store_available
            )
        except StoreUnavailableError:
            return {"status": "storeUnavailableError"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id, risk_hint)
        except ScreeningUnavailableError:
            # Case d: screening outage — priced, stored on hold, not notified
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {"status": "heldUnscreenedResponse", "quote_id": quote_id,
                    "price": price_amount}

        # Step 4: apply screening decision
        if risk_index <= ACCEPT_MAX:
            # Case a: accept
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {"status": "quotedResponse", "quote_id": quote_id, "price": price_amount}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # Case b: review hold
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "reviewHoldResponse", "quote_id": quote_id}
        else:
            # Case c: refuse (risk_index >= REFUSE_MIN)
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refusedScreeningResponse", "quote_id": quote_id}


_STATUS_MAP = {
    "quotedResponse": "confirmed",
    "reviewHoldResponse": "review",
    "refusedScreeningResponse": "rejected",
    "heldUnscreenedResponse": "held",
    "rejectedInvalidRequest": "error: invalid_request",
    "storeUnavailableError": "error: store_unavailable",
}


def _risk_hint_from_request(request):
    for key in ("screening_result", "screening_status", "screening_score"):
        if key in request and request[key] is not None:
            val = request[key]
            if isinstance(val, (int, float)):
                return val
            try:
                return int(val)
            except (ValueError, TypeError):
                return str(val)
    return None


def handle(request: dict) -> dict:
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    api = QuoteApi(quote_store, screening_service, tariff_engine, notification_service)

    shipper_id = request.get("shipper_id", request.get("shipperId", "shipper-1"))
    weight_kg = request.get("weight_kg", request.get("weightKg", 100))
    distance_km = request.get("distance_km", request.get("distanceKm", 100))
    declared_value = request.get("declared_value", request.get("declaredValue", 1000))

    store_available = True
    if request.get("store_status") == "error" or request.get("store_result") == "error":
        store_available = False
    if request.get("quote_store_status") == "error":
        store_available = False
    if request.get("store_available") is False:
        store_available = False

    risk_hint = _risk_hint_from_request(request)

    result = api.request_quote(
        shipper_id, weight_kg, distance_km, declared_value,
        store_available=store_available, risk_hint=risk_hint,
    )

    out = dict(result)
    out["status"] = _STATUS_MAP.get(result["status"], result["status"])
    out["outcome"] = result["status"]
    return out