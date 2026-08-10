def _to_number(value):
    try:
        if isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


class ScreeningUnavailable(Exception):
    pass


class StoreUnavailable(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, risk_index=0, available=True):
        self._risk_index = risk_index
        self._available = available

    def screen(self, shipper_id):
        if not self._available:
            raise ScreeningUnavailable("screening_unavailable")
        return int(self._risk_index)


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, available=True):
        self._available = available

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        # fire-and-forget; a delivery failure never changes the response
        return self._available

    def send_refusal_notice(self, shipper_id, quote_id):
        # fire-and-forget; a delivery failure never changes the response
        return self._available


class TariffEngine:
    """Computes the freight price per DT-P."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            result += 316.00
        if distance_km >= 4912:
            result *= 1.19
        return round(result, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self._available = available
        self._records = {}
        self._counter = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._available:
            raise StoreUnavailable("store_unavailable")
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

    def update_quote(self, quote_id, status, price_amount=None):
        record = self._records.get(quote_id, {})
        record["status"] = status
        if price_amount is not None:
            record["price"] = price_amount
        self._records[quote_id] = record
        return quote_id


# DT-S symbolic bounds
ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

# DT-V validation bounds
WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False
        w = _to_number(weight_kg)
        d = _to_number(distance_km)
        v = _to_number(declared_value)
        if w is None or not (WEIGHT_MIN <= w <= WEIGHT_MAX):
            return False
        if d is None or not (DISTANCE_MIN <= d <= DISTANCE_MAX):
            return False
        if v is None or not (VALUE_MIN <= v <= VALUE_MAX):
            return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # 1. Validate (DT-V)
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        weight_kg = _to_number(weight_kg)
        distance_km = _to_number(distance_km)
        declared_value = _to_number(declared_value)

        # 2. Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailable:
            return {"status": "error: store_unavailable"}

        # 3. Screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailable:
            # Screening outage: price anyway, hold, do not notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
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
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def _resolve_risk_and_availability(request):
    """Interpret request screening keys into (risk_index, available)."""
    for key in ("screening_result", "screening_status"):
        if key in request:
            val = request[key]
            if isinstance(val, str):
                low = val.strip().lower()
                if low in ("error", "unavailable", "outage", "down", "timeout"):
                    return (0, False)
                num = _to_number(val)
                if num is not None:
                    return (int(num), True)
                # a status word other than outage -> treat as accept-band
                return (0, True)
            num = _to_number(val)
            if num is not None:
                return (int(num), True)
    # default: assume accept band
    return (0, True)


def _resolve_store_availability(request):
    for key in ("store_result", "store_status", "quote_store_result", "quote_store_status"):
        if key in request:
            val = request[key]
            if isinstance(val, str):
                low = val.strip().lower()
                if low in ("error", "unavailable", "down", "fail", "failed"):
                    return False
    if request.get("store_exists") is False or request.get("store_found") is False:
        return False
    return True


def _resolve_notification_availability(request):
    for key in ("notification_result", "notification_status"):
        if key in request:
            val = request[key]
            if isinstance(val, str):
                low = val.strip().lower()
                if low in ("error", "unavailable", "down", "fail", "failed"):
                    return False
    return True


def handle(request: dict) -> dict:
    request = request or {}

    risk_index, screening_available = _resolve_risk_and_availability(request)
    store_available = _resolve_store_availability(request)
    notification_available = _resolve_notification_availability(request)

    tariff_engine = TariffEngine()
    quote_store = QuoteStore(available=store_available)
    screening_service = ScreeningService(
        risk_index=risk_index, available=screening_available
    )
    notification_service = NotificationService(available=notification_available)

    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)

    return api.request_quote(
        request.get("shipper_id"),
        request.get("weight_kg"),
        request.get("distance_km"),
        request.get("declared_value"),
    )