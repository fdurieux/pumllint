import math


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class NotificationError(Exception):
    pass


class Shipper:
    def __init__(self, shipper_id="unknown"):
        self.shipper_id = shipper_id

    def request_quote(self, api, payload):
        return api.request_quote(payload)


class TariffEngine:
    """Computes freight price per DT-P."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km  # P1
        if weight_kg > 1244:  # P2 heavy surcharge (flat)
            result += 316.00
        if distance_km >= 4912:  # P3 long-haul multiplier, after P2
            result *= 1.19
        return round(result, 2)  # P4


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, store_ok=True):
        self._store_ok = store_ok
        self._records = {}
        self._counter = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._store_ok:
            raise StoreUnavailableError("store_unavailable")
        self._counter += 1
        quote_id = "Q-{:06d}".format(self._counter)
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
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
    """External denied-party screening provider returning a risk index."""

    def __init__(self, risk_index=0, available=True):
        self._risk_index = risk_index
        self._available = available

    def screen(self, shipper_id):
        if not self._available:
            raise ScreeningUnavailableError("screening_unavailable")
        return int(self._risk_index)


class NotificationService:
    """External messaging provider delivering quote docs and refusal notices."""

    def __init__(self, deliverable=True):
        self._deliverable = deliverable

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        if not self._deliverable:
            raise NotificationError("delivery_failed")
        return "delivered"

    def send_refusal_notice(self, shipper_id, quote_id):
        if not self._deliverable:
            raise NotificationError("delivery_failed")
        return "delivered"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening/pricing."""

    def __init__(self, store, screening, tariff, notification):
        self.store = store
        self.screening = screening
        self.tariff = tariff
        self.notification = notification

    def _validate(self, payload):
        shipper_id = payload.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False
        weight = payload.get("weight_kg")
        if not self._is_number(weight) or not (3 <= weight <= 19400):
            return False
        distance = payload.get("distance_km")
        if not self._is_number(distance) or not (25 <= distance <= 7150):
            return False
        value = payload.get("declared_value")
        if not self._is_number(value) or not (50 <= value <= 83000):
            return False
        return True

    @staticmethod
    def _is_number(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def request_quote(self, payload):
        # Step 1: validate (DT-V)
        if not self._validate(payload):
            return {"status": "rejected: invalid_request"}

        shipper_id = payload["shipper_id"]
        weight_kg = payload["weight_kg"]
        distance_km = payload["distance_km"]
        declared_value = payload["declared_value"]

        # Step 2: store draft
        try:
            quote_id = self.store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening.screen(shipper_id)
        except ScreeningUnavailableError:
            # outage: price anyway, hold, no notification
            price_amount = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4-6: apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "quoted", price_amount)
            self._notify_quote(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.store.update_quote(quote_id, "refused_screening")
            self._notify_refusal(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}

    def _notify_quote(self, shipper_id, quote_id, price_amount):
        # fire-and-forget: failures never change the outcome
        try:
            self.notification.send_quote_document(shipper_id, quote_id, price_amount)
        except NotificationError:
            pass

    def _notify_refusal(self, shipper_id, quote_id):
        try:
            self.notification.send_refusal_notice(shipper_id, quote_id)
        except NotificationError:
            pass


def _parse_screening(request):
    """Return (available, risk_index) from request scenario keys."""
    raw = request.get("screening_result", request.get("screening_status"))
    if raw is None:
        raw = request.get("risk_index")
    # outage detection
    if isinstance(raw, str):
        low = raw.strip().lower()
        if low in ("error", "unavailable", "down", "outage", "timeout"):
            return False, 0
        try:
            return True, int(float(low))
        except ValueError:
            return True, 0
    if isinstance(raw, bool):
        return True, 0
    if isinstance(raw, (int, float)):
        return True, int(raw)
    # default: screening succeeds with clean index
    return True, 0


def _parse_store(request):
    raw = request.get("store_result", request.get("store_status"))
    if raw is None:
        raw = request.get("quote_store_result", request.get("quote_store_status"))
    if isinstance(raw, str):
        low = raw.strip().lower()
        if low in ("error", "unavailable", "down", "fail", "failed"):
            return False
    if request.get("store_exists") is False:
        return False
    return True


def _parse_notification(request):
    raw = request.get("notification_result", request.get("notification_status"))
    if isinstance(raw, str):
        low = raw.strip().lower()
        if low in ("error", "unavailable", "fail", "failed", "undelivered"):
            return False
    return True


def handle(request: dict) -> dict:
    if not isinstance(request, dict):
        return {"status": "error: invalid_request"}

    store_ok = _parse_store(request)
    screen_available, risk_index = _parse_screening(request)
    notif_ok = _parse_notification(request)

    store = QuoteStore(store_ok=store_ok)
    screening = ScreeningService(risk_index=risk_index, available=screen_available)
    tariff = TariffEngine()
    notification = NotificationService(deliverable=notif_ok)

    api = QuoteApi(store, screening, tariff, notification)

    payload = {
        "shipper_id": request.get("shipper_id"),
        "weight_kg": request.get("weight_kg"),
        "distance_km": request.get("distance_km"),
        "declared_value": request.get("declared_value"),
    }

    return api.request_quote(payload)