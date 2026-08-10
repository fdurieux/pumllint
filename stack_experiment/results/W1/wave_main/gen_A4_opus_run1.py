import numbers

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

_ERROR_WORDS = {"error", "unavailable", "down", "fail", "failed", "timeout"}


class StoreUnavailable(Exception):
    pass


class ScreeningUnavailable(Exception):
    pass


class TariffEngine:
    """Computes the freight price per DT-P."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > HEAVY_THRESHOLD:
            result += HEAVY_SURCHARGE
        if distance_km >= LONGHAUL_THRESHOLD:
            result *= LONGHAUL_MULTIPLIER
        return round(result, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, fail=False):
        self.fail = fail
        self._counter = 0
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if self.fail:
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

    def update_quote(self, quote_id, status, price=None):
        rec = self._records.get(quote_id, {})
        rec["status"] = status
        if price is not None:
            rec["price"] = price
        self._records[quote_id] = rec
        return quote_id


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, risk_index=0, unavailable=False):
        self.risk_index = risk_index
        self.unavailable = unavailable

    def screen(self, shipper_id):
        if self.unavailable:
            raise ScreeningUnavailable("screening_unavailable")
        return self.risk_index


class NotificationService:
    """External messaging provider; fire-and-forget."""

    def __init__(self, fail=False):
        self.fail = fail

    def send_quote_document(self, shipper_id, quote_id, price):
        if self.fail:
            return "delivery_failed"
        return "delivered"

    def send_refusal_notice(self, shipper_id, quote_id):
        if self.fail:
            return "delivery_failed"
        return "delivered"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _valid(self, req):
        shipper_id = req.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False
        for key, lo, hi in (
            ("weight_kg", WEIGHT_MIN, WEIGHT_MAX),
            ("distance_km", DISTANCE_MIN, DISTANCE_MAX),
            ("declared_value", VALUE_MIN, VALUE_MAX),
        ):
            val = req.get(key)
            if isinstance(val, bool) or not isinstance(val, numbers.Number):
                return False
            if val < lo or val > hi:
                return False
        return True

    def request_quote(self, req):
        # Step 1: validate (DT-V)
        if not self._valid(req):
            return {"status": "rejected: invalid_request"}

        shipper_id = req["shipper_id"]
        weight_kg = req["weight_kg"]
        distance_km = req["distance_km"]
        declared_value = req["declared_value"]

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailable:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailable:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4-7: apply DT-S
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def _is_error_word(value):
    return isinstance(value, str) and value.strip().lower() in _ERROR_WORDS


def _store_fails(request):
    for key in ("store_result", "store_status", "quote_store_result", "quote_store_status"):
        if _is_error_word(request.get(key)):
            return True
    if request.get("store_exists") is False or request.get("store_found") is False:
        return True
    return False


def _resolve_screening(request):
    """Return (risk_index, unavailable)."""
    for key in ("screening_result", "screening_status", "screening_service_result",
                "screening_service_status"):
        val = request.get(key)
        if _is_error_word(val):
            return 0, True
    if request.get("screening_exists") is False or request.get("screening_found") is False:
        return 0, True

    # numeric risk index
    for key in ("risk_index", "screening_result", "screening_status", "score"):
        val = request.get(key)
        if isinstance(val, bool):
            continue
        if isinstance(val, numbers.Number):
            return int(val), False
        if isinstance(val, str):
            try:
                return int(float(val)), False
            except ValueError:
                pass

    # word-based mapping
    for key in ("screening_result", "screening_status"):
        val = request.get(key)
        if isinstance(val, str):
            w = val.strip().lower()
            if w in ("approved", "accept", "accepted", "clear", "pass"):
                return 0, False
            if w in ("review", "hold", "manual"):
                return 50, False
            if w in ("declined", "refused", "refuse", "denied", "blocked"):
                return 90, False

    return 0, False


def _notification_fails(request):
    for key in ("notification_result", "notification_status",
                "notification_service_result", "notification_service_status"):
        if _is_error_word(request.get(key)):
            return True
    return False


def handle(request: dict) -> dict:
    if request is None:
        request = {}

    store_fail = _store_fails(request)
    risk_index, screening_unavailable = _resolve_screening(request)
    notification_fail = _notification_fails(request)

    tariff_engine = TariffEngine()
    quote_store = QuoteStore(fail=store_fail)
    screening_service = ScreeningService(
        risk_index=risk_index, unavailable=screening_unavailable
    )
    notification_service = NotificationService(fail=notification_fail)

    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)

    return api.request_quote(request)