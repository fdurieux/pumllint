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


class StoreUnavailable(Exception):
    pass


class ScreeningUnavailable(Exception):
    pass


class InvalidRequest(Exception):
    pass


class TariffEngine:
    """Computes the freight price per DT-P."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km  # P1
        if weight_kg > HEAVY_THRESHOLD:  # P2
            result += HEAVY_SURCHARGE
        if distance_km >= LONGHAUL_THRESHOLD:  # P3 (after P2)
            result *= LONGHAUL_MULTIPLIER
        return round(result, 2)  # P4


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
        quote_id = "Q-%05d" % self._counter
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
            raise StoreUnavailable("quote_not_found")
        rec["status"] = status
        if price is not None:
            rec["price"] = price
        return rec


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, available=True, risk_index=0):
        self._available = available
        self._risk_index = risk_index

    def screen(self, shipper_id):
        if not self._available:
            raise ScreeningUnavailable("screening_unavailable")
        return self._risk_index


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, healthy=True):
        self._healthy = healthy
        self.sent = []

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return self._deliver("quote_document", shipper_id, quote_id)

    def send_refusal_notice(self, shipper_id, quote_id):
        return self._deliver("refusal_notice", shipper_id, quote_id)

    def _deliver(self, kind, shipper_id, quote_id):
        # Fire-and-forget: a delivery failure is the provider's retry problem.
        if not self._healthy:
            return False
        self.sent.append((kind, shipper_id, quote_id))
        return True


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, quote_store, tariff_engine, screening_service, notification_service):
        self.quote_store = quote_store
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, req):
        shipper_id = req.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            raise InvalidRequest("shipper_id")
        weight = req.get("weight_kg")
        if not _is_number(weight) or not (WEIGHT_MIN <= weight <= WEIGHT_MAX):
            raise InvalidRequest("weight_kg")
        distance = req.get("distance_km")
        if not _is_number(distance) or not (DISTANCE_MIN <= distance <= DISTANCE_MAX):
            raise InvalidRequest("distance_km")
        value = req.get("declared_value")
        if not _is_number(value) or not (VALUE_MIN <= value <= VALUE_MAX):
            raise InvalidRequest("declared_value")

    def request_quote(self, req):
        # Step 1: validate (DT-V)
        try:
            self._validate(req)
        except InvalidRequest:
            return {"status": "rejected: invalid_request"}

        shipper_id = req["shipper_id"]
        weight = req["weight_kg"]
        distance = req["distance_km"]
        value = req["declared_value"]

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight, distance, value)
        except StoreUnavailable:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailable:
            # Screening outage: price anyway, hold, no notification (DT-S note 5)
            price = self.tariff_engine.price(weight, distance)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4-6: apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight, distance)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _truthy_word(value, words):
    return isinstance(value, str) and value.strip().lower() in words


def handle(request: dict) -> dict:
    """Run one end-to-end quotation flow."""
    request = dict(request or {})

    # --- Configure Quote Store availability ---
    store_available = True
    for key in ("store_status", "store_result", "quote_store_status", "quote_store_result"):
        if key in request:
            if _truthy_word(request[key], {"error", "unavailable", "down", "fail", "failed"}):
                store_available = False
            break
    if request.get("store_exists") is False or request.get("quote_store_exists") is False:
        store_available = False

    # --- Configure Screening Service ---
    screening_available = True
    risk_index = 0

    screening_val = None
    for key in ("screening_result", "screening_status", "screening"):
        if key in request:
            screening_val = request[key]
            break

    if screening_val is not None:
        if _is_number(screening_val):
            risk_index = int(screening_val)
        elif _truthy_word(screening_val, {"error", "unavailable", "down", "outage", "fail", "failed"}):
            screening_available = False
        elif _truthy_word(screening_val, {"declined", "refused", "denied"}):
            risk_index = REFUSE_MIN
        elif _truthy_word(screening_val, {"review", "hold"}):
            risk_index = REVIEW_MIN
        elif _truthy_word(screening_val, {"approved", "accepted", "active", "clear", "assessed"}):
            risk_index = 0

    # explicit numeric risk index overrides
    for key in ("risk_index", "riskIndex", "screening_score", "score"):
        if key in request and _is_number(request[key]):
            risk_index = int(request[key])
    if request.get("screening_exists") is False:
        screening_available = False

    # --- Configure Notification Service ---
    notification_healthy = True
    for key in ("notification_status", "notification_result", "notification"):
        if key in request:
            if _truthy_word(request[key], {"error", "unavailable", "down", "fail", "failed", "undelivered"}):
                notification_healthy = False
            break

    store = QuoteStore(available=store_available)
    tariff = TariffEngine()
    screening = ScreeningService(available=screening_available, risk_index=risk_index)
    notification = NotificationService(healthy=notification_healthy)

    api = QuoteApi(store, tariff, screening, notification)
    return api.request_quote(request)