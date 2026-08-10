import numbers


class StoreUnavailable(Exception):
    """Raised when the quote store cannot persist a record."""
    pass


class ScreeningUnavailable(Exception):
    """Raised when the external screening provider is unavailable."""
    pass


def _lookup(request, *names):
    for n in names:
        if n in request and request[n] is not None:
            return request[n]
    return None


class Shipper:
    """Person: a logistics customer requesting a price quote."""

    def __init__(self, shipper_id=None):
        self.shipper_id = shipper_id

    def request_quote(self, quote_api, request):
        # Rel(shipper, quote_api): requests freight quotes from
        return quote_api.request_quote(request)


class QuoteStore:
    """ContainerDb: stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._seq = 0

    def store_draft(self, request):
        val = self._hint(request, "store", "quote_store")
        if val is not None and str(val).lower() in (
            "error", "unavailable", "down", "fail", "failed",
        ):
            raise StoreUnavailable()
        self._seq += 1
        quote_id = "Q-{}".format(self._seq)
        self._records[quote_id] = {
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price=None):
        rec = self._records.get(quote_id)
        if rec is not None:
            rec["status"] = status
            if price is not None:
                rec["price"] = price
        return "updated:{}:{}".format(quote_id, status)

    @staticmethod
    def _hint(request, *prefixes):
        for p in prefixes:
            for suffix in ("_result", "_status"):
                key = p + suffix
                if key in request:
                    return request[key]
        return None


class TariffEngine:
    """Container: computes the freight price from weight and distance."""

    BASE_FEE = 25.0
    RATE_PER_KG_KM = 0.0005

    def price(self, weight_kg, distance_km):
        amount = self.BASE_FEE + float(weight_kg) * float(distance_km) * self.RATE_PER_KG_KM
        return round(amount, 2)


class ScreeningService:
    """System_Ext: external denied-party screening provider."""

    def screen(self, shipper_id, request):
        val = self._hint(request)
        if val is None:
            return 0  # default: low risk / clear
        if isinstance(val, bool):
            val = 100 if val else 0
        if isinstance(val, numbers.Number):
            return val
        s = str(val).strip().lower()
        if s in ("error", "unavailable", "down", "timeout", "outage"):
            raise ScreeningUnavailable()
        if s in ("approved", "active", "clear", "accept", "ok", "pass"):
            return 0
        if s in ("review", "hold", "manual", "assessed", "pending"):
            return 50
        if s in ("declined", "refused", "denied", "reject", "blocked"):
            return 100
        try:
            return float(s)
        except ValueError:
            return 0

    @staticmethod
    def _hint(request):
        for p in ("screening", "screening_service"):
            for suffix in ("_result", "_status"):
                key = p + suffix
                if key in request:
                    return request[key]
        return None


class NotificationService:
    """System_Ext: external messaging provider (fire-and-forget)."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "quote_document_sent:{}".format(quote_id)

    def send_refusal_notice(self, shipper_id, quote_id):
        return "refusal_notice_sent:{}".format(quote_id)


class QuoteApi:
    """Container: orchestrates validation, screening, pricing, notification."""

    # DT-S screening thresholds
    ACCEPT_MAX = 30
    REVIEW_MIN = 31
    REVIEW_MAX = 69
    REFUSE_MIN = 70

    # DT-V validation bounds
    MIN_WEIGHT_KG = 1
    MAX_WEIGHT_KG = 30000
    MIN_DISTANCE_KM = 1
    MAX_DISTANCE_KM = 5000
    MIN_DECLARED_VALUE = 1

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _shipper_id(self, request):
        return _lookup(
            request, "shipperId", "shipper_id", "shipper", "shipperID", "customerId",
        )

    def _weight(self, request):
        return _lookup(request, "weightKg", "weight_kg", "weight")

    def _distance(self, request):
        return _lookup(request, "distanceKm", "distance_km", "distance")

    def _value(self, request):
        return _lookup(request, "declaredValue", "declared_value", "value")

    def request_quote(self, request):
        invalid_reason = self._validate(request)
        if invalid_reason is not None:
            return {"status": "rejected", "reason": invalid_reason}

        # Store the draft first.
        try:
            quote_id = self.quote_store.store_draft(request)
        except StoreUnavailable:
            # DT-S note 3: nothing else runs on storage failure.
            return {"status": "error: store_unavailable"}

        shipper_id = self._shipper_id(request)
        weight_kg = self._weight(request)
        distance_km = self._distance(request)

        # Screening.
        try:
            risk_index = self.screening_service.screen(shipper_id, request)
        except ScreeningUnavailable:
            # DT-S note 5: priced, stored on hold, not notified.
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        if risk_index <= self.ACCEPT_MAX:
            # Accept row: price, store quoted, notify (fire-and-forget).
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {
                "status": "confirmed",
                "quote_id": quote_id,
                "price": price_amount,
            }
        elif risk_index <= self.REVIEW_MAX:
            # Review row (DT-S note 1): no pricing, no notification.
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:
            # Refuse row (DT-S note 2): refusal notified, no pricing.
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused", "quote_id": quote_id}

    def _validate(self, request):
        # Existence flags.
        for key in ("shipper_exists", "shipper_found"):
            if key in request and not request[key]:
                return "unknown_shipper"

        if not self._shipper_id(request):
            return "missing_shipper"

        weight = self._weight(request)
        distance = self._distance(request)
        value = self._value(request)

        if not self._is_number(weight):
            return "invalid_weight"
        if not (self.MIN_WEIGHT_KG <= weight <= self.MAX_WEIGHT_KG):
            return "invalid_weight"

        if not self._is_number(distance):
            return "invalid_distance"
        if not (self.MIN_DISTANCE_KM <= distance <= self.MAX_DISTANCE_KM):
            return "invalid_distance"

        if not self._is_number(value):
            return "invalid_declared_value"
        if value < self.MIN_DECLARED_VALUE:
            return "invalid_declared_value"

        return None

    @staticmethod
    def _is_number(x):
        return isinstance(x, numbers.Number) and not isinstance(x, bool)


def handle(request: dict) -> dict:
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    quote_api = QuoteApi(quote_store, screening_service, tariff_engine, notification_service)
    shipper = Shipper(
        _lookup(request, "shipperId", "shipper_id", "shipper", "shipperID", "customerId")
    )
    try:
        return shipper.request_quote(quote_api, request)
    except Exception as exc:  # pragma: no cover - defensive catch-all
        return {"status": "error: {}".format(exc.__class__.__name__.lower())}