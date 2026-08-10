SCREENING_ACCEPT_MAX = 30
SCREENING_REVIEW_MIN = 31
SCREENING_REVIEW_MAX = 70
SCREENING_REFUSE_MIN = 71

WEIGHT_MIN = 10
WEIGHT_MAX = 30000
DISTANCE_MIN = 1
DISTANCE_MAX = 5000
VALUE_MIN = 1
VALUE_MAX = 10_000_000


class ValidationError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, outcome=None):
        self.outcome = outcome

    def screen(self, shipper_id):
        o = self.outcome
        if o is None:
            return 10.0
        if isinstance(o, (int, float)):
            return float(o)
        word = str(o).strip().lower()
        if word in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailableError("screening service unavailable")
        if word in ("approved", "active", "clear", "accept"):
            return 10.0
        if word in ("review", "assessed", "hold"):
            return 50.0
        if word in ("declined", "denied", "refuse", "blocked"):
            return 90.0
        try:
            return float(word)
        except ValueError:
            return 10.0


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG = 0.15
    RATE_PER_KM = 0.40

    def price(self, weight_kg, distance_km):
        return round(
            self.BASE_FEE
            + self.RATE_PER_KG * float(weight_kg)
            + self.RATE_PER_KM * float(distance_km),
            2,
        )


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self.available = available
        self._seq = 0
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self.available:
            raise StoreUnavailableError("quote store unavailable")
        self._seq += 1
        quote_id = "Q%05d" % self._seq
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price=None):
        rec = self._records.get(quote_id)
        if rec is None:
            rec = {}
            self._records[quote_id] = rec
        rec["status"] = status
        if price is not None:
            rec["price"] = price
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return True

    def send_refusal_notice(self, shipper_id, quote_id):
        return True


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value, shipper_exists):
        if not shipper_id:
            raise ValidationError("missing shipper id")
        if not shipper_exists:
            raise ValidationError("shipper not found")
        for name, val in (
            ("weight", weight_kg),
            ("distance", distance_km),
            ("declared_value", declared_value),
        ):
            if val is None:
                raise ValidationError("missing %s" % name)
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValidationError("non-numeric %s" % name)
        if not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            raise ValidationError("weight out of bounds")
        if not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            raise ValidationError("distance out of bounds")
        if not (VALUE_MIN <= declared_value <= VALUE_MAX):
            raise ValidationError("declared value out of bounds")

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value, shipper_exists=True):
        # Validation (DT-V)
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value, shipper_exists)
        except ValidationError as e:
            return {"status": "rejected: invalid request", "reason": str(e)}

        # Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError as e:
            return {"status": "error: store unavailable", "reason": str(e)}

        # Screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: outage does not fail the quote — price, hold, no notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # DT-S accept
        if risk_index <= SCREENING_ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
                "risk_index": risk_index,
            }

        # DT-S review
        if SCREENING_REVIEW_MIN <= risk_index <= SCREENING_REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }

        # DT-S refuse (risk_index >= REFUSE_MIN)
        self.quote_store.update_quote(quote_id, "refused_screening")
        self.notification_service.send_refusal_notice(shipper_id, quote_id)
        return {
            "status": "refused",
            "quote_id": quote_id,
            "risk_index": risk_index,
        }


def _first(request, *keys, default=None):
    for k in keys:
        if k in request and request[k] is not None:
            return request[k]
    return default


def _is_available(value):
    if value is None:
        return True
    word = str(value).strip().lower()
    return word not in ("error", "unavailable", "down", "fail", "failed")


def _bool_flag(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    word = str(value).strip().lower()
    if word in ("false", "no", "0", "missing", "notfound", "not_found", "absent"):
        return False
    return True


def handle(request: dict) -> dict:
    shipper_id = _first(request, "shipper_id", "shipperId", "shipper", default=None)
    weight_kg = _first(request, "weight_kg", "weightKg", "weight", default=None)
    distance_km = _first(request, "distance_km", "distanceKm", "distance", default=None)
    declared_value = _first(
        request, "declared_value", "declaredValue", "value", default=None
    )

    shipper_exists = _bool_flag(
        _first(request, "shipper_exists", "shipper_found", "shipperExists", default=None),
        default=True,
    )

    store_status = _first(
        request, "store_result", "store_status", "quote_store_result",
        "quote_store_status", default=None,
    )
    store = QuoteStore(available=_is_available(store_status))

    screening_outcome = _first(
        request, "screening_result", "screening_status",
        "screening_service_result", "screening_service_status", default=None,
    )
    screening = ScreeningService(outcome=screening_outcome)

    tariff = TariffEngine()
    notification = NotificationService()

    api = QuoteApi(store, screening, tariff, notification)

    try:
        return api.request_quote(
            shipper_id, weight_kg, distance_km, declared_value, shipper_exists
        )
    except Exception as e:  # defensive catch-all
        return {"status": "error: %s" % str(e)}