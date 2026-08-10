ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

WEIGHT_MIN, WEIGHT_MAX = 1, 26000
DISTANCE_MIN, DISTANCE_MAX = 1, 5000
VALUE_MIN, VALUE_MAX = 1, 1_000_000


class ValidationError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, risk_index=10, available=True):
        self._risk_index = risk_index
        self._available = available

    def screen(self, shipper_id):
        if not self._available:
            raise ScreeningUnavailableError("screening service unavailable")
        return self._risk_index


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, available=True):
        self._available = available

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        # fire-and-forget: failure never changes the response
        if not self._available:
            return "delivery_failed"
        return "quote_document_sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        if not self._available:
            return "delivery_failed"
        return "refusal_notice_sent"


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff rules."""

    BASE_FEE = 25.0
    PER_KG = 0.15
    PER_KM = 0.40

    def price(self, weight_kg, distance_km):
        return round(self.BASE_FEE + self.PER_KG * weight_kg + self.PER_KM * distance_km, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self._available = available
        self._records = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
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

    def update_quote(self, quote_id, status, price_amount=None):
        if not self._available:
            raise StoreUnavailableError("quote store unavailable")
        rec = self._records.get(quote_id, {})
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        self._records[quote_id] = rec
        return quote_id


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            raise ValidationError("missing shipper id")
        if not isinstance(weight_kg, (int, float)) or not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            raise ValidationError("weight out of bounds")
        if not isinstance(distance_km, (int, float)) or not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            raise ValidationError("distance out of bounds")
        if not isinstance(declared_value, (int, float)) or not (VALUE_MIN <= declared_value <= VALUE_MAX):
            raise ValidationError("declared value out of bounds")

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Validation (DT-V)
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as exc:
            return {"status": "error: invalid_request", "reason": str(exc)}

        # Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError as exc:
            # On storage failure nothing else runs (DT-S note 3)
            return {"status": "error: store_unavailable", "reason": str(exc)}

        # Screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage does NOT fail the quote (DT-S note 5)
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # Decision table DT-S
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {
                "status": "confirmed",
                "quote_id": quote_id,
                "price": price_amount,
                "risk_index": risk_index,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # Review hold: no pricing, no notification (DT-S note 1)
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }
        else:  # risk_index >= REFUSE_MIN
            # Refusal IS notified; pricing never runs (DT-S note 2)
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "rejected",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }


def _get(request, *keys, default=None):
    for k in keys:
        if k in request:
            return request[k]
    return default


def _resolve_risk_index(request):
    """Determine (available, risk_index) from request screening signals."""
    status = _get(request, "screening_status", "screening_result")
    if isinstance(status, (int, float)):
        return True, status
    if isinstance(status, str):
        word = status.lower()
        if word in ("error", "unavailable", "down", "timeout"):
            return False, None
        if word in ("approved", "accept", "accepted", "clear", "active"):
            return True, 10
        if word in ("review", "hold", "assessed", "manual"):
            return True, 50
        if word in ("declined", "refuse", "refused", "denied", "blocked"):
            return True, 90
    if "screening_score" in request:
        return True, request["screening_score"]
    return True, 10


def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = _get(request, "shipper_id", "shipperId")
    if _get(request, "shipper_found", "shipper_exists", default=True) is False:
        shipper_id = None

    weight_kg = _get(request, "weight_kg", "weightKg", default=None)
    distance_km = _get(request, "distance_km", "distanceKm", default=None)
    declared_value = _get(request, "declared_value", "declaredValue", default=None)

    store_signal = _get(request, "store_status", "store_result")
    store_available = True
    if isinstance(store_signal, str) and store_signal.lower() in (
        "error", "unavailable", "down", "timeout",
    ):
        store_available = False

    screening_available, risk_index = _resolve_risk_index(request)

    notif_signal = _get(request, "notification_status", "notification_result")
    notif_available = not (
        isinstance(notif_signal, str)
        and notif_signal.lower() in ("error", "unavailable", "down", "timeout")
    )

    quote_store = QuoteStore(available=store_available)
    screening_service = ScreeningService(
        risk_index=risk_index if risk_index is not None else 10,
        available=screening_available,
    )
    tariff_engine = TariffEngine()
    notification_service = NotificationService(available=notif_available)

    api = QuoteApi(quote_store, screening_service, tariff_engine, notification_service)

    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)