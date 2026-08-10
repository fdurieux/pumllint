import numbers

# Symbolic thresholds (DT-S)
ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

# DT-V validation bounds
WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


def _is_number(x):
    return isinstance(x, numbers.Number) and not isinstance(x, bool)


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, risk_index=0, available=True):
        self._risk_index = risk_index
        self._available = available

    def screen(self, shipper_id):
        if not self._available:
            raise ScreeningUnavailableError("screening_unavailable")
        return int(self._risk_index)


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, healthy=True):
        self._healthy = healthy

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        # Fire-and-forget: failures never propagate.
        return "delivered" if self._healthy else "delivery_failed"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "delivered" if self._healthy else "delivery_failed"


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

    def price(self, weight_kg, distance_km):
        base = 0.87 * weight_kg + 1.13 * distance_km  # P1
        if weight_kg > 1244:  # P2 heavy surcharge (flat)
            base += 316.00
        if distance_km >= 4912:  # P3 long-haul multiplier (after P2)
            base *= 1.19
        return round(base, 2)  # P4


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self._available = available
        self._records = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._available:
            raise StoreUnavailableError("store_unavailable")
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
        if rec is not None:
            rec["status"] = status
            if price_amount is not None:
                rec["price"] = price_amount
        return quote_id


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    def __init__(self, quote_store, screening_service, tariff_engine,
                 notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id or not isinstance(shipper_id, str):
            return False
        if not _is_number(weight_kg) or not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            return False
        if not _is_number(distance_km) or not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            return False
        if not _is_number(declared_value) or not (VALUE_MIN <= declared_value <= VALUE_MAX):
            return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # 1. Validate (DT-V)
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # 2. Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # 3. Screen
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage: price anyway, hold, do not notify (DT-S note 5)
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # 4/5/6. Apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def _parse_screening(request):
    """Return (risk_index, available) from request keys."""
    outage_words = {"error", "unavailable", "down", "timeout", "outage", "failed"}
    for key in ("screening_result", "screening_status", "risk_index",
                "screening", "screening_service_result",
                "screening_service_status"):
        if key in request:
            v = request[key]
            if _is_number(v):
                return int(v), True
            if isinstance(v, str):
                s = v.strip().lower()
                if s in outage_words:
                    return 0, False
                if s.lstrip("-").isdigit():
                    return int(s), True
                # words like "approved"/"assessed"/"active" -> accept band
                if s in ("approved", "assessed", "active", "clear", "ok"):
                    return 0, True
                if s in ("declined", "refused"):
                    return REFUSE_MIN, True
                if s == "review":
                    return REVIEW_MIN, True
    return 0, True


def _parse_store(request):
    """Return True if store is available."""
    fail_words = {"error", "unavailable", "down", "fail", "failed", "outage"}
    for key in ("store_result", "store_status", "quote_store_result",
                "quote_store_status", "store"):
        if key in request:
            v = request[key]
            if isinstance(v, str) and v.strip().lower() in fail_words:
                return False
    for key in ("store_exists", "quote_store_exists", "store_found",
                "quote_store_found"):
        if key in request and request[key] in (False, "false", "no", 0):
            return False
    return True


def _parse_notification(request):
    """Return True if notification provider is healthy."""
    fail_words = {"error", "unavailable", "down", "fail", "failed"}
    for key in ("notification_result", "notification_status",
                "notification_service_result", "notification_service_status",
                "notification"):
        if key in request:
            v = request[key]
            if isinstance(v, str) and v.strip().lower() in fail_words:
                return False
    return True


def handle(request: dict) -> dict:
    request = request or {}

    risk_index, screening_available = _parse_screening(request)
    store_available = _parse_store(request)
    notification_healthy = _parse_notification(request)

    quote_store = QuoteStore(available=store_available)
    screening_service = ScreeningService(risk_index=risk_index,
                                          available=screening_available)
    tariff_engine = TariffEngine()
    notification_service = NotificationService(healthy=notification_healthy)

    api = QuoteApi(quote_store, screening_service, tariff_engine,
                   notification_service)

    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    try:
        return api.request_quote(shipper_id, weight_kg, distance_km,
                                 declared_value)
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error: %s" % (exc,)}