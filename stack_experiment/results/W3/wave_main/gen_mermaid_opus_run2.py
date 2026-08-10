import math


ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70

WEIGHT_MIN, WEIGHT_MAX = 1, 26000
DISTANCE_MIN, DISTANCE_MAX = 1, 5000
VALUE_MIN, VALUE_MAX = 1, 10_000_000


class ScreeningUnavailableError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, result=None):
        self.result = result

    def screen(self, shipper_id):
        r = self.result
        if r is None:
            return 10
        if isinstance(r, bool):
            r = 10 if r else 90
        if isinstance(r, (int, float)):
            return r
        s = str(r).strip().lower()
        if s in ("error", "unavailable", "down", "timeout", "outage"):
            raise ScreeningUnavailableError("screening service unavailable")
        if s in ("approved", "accept", "accepted", "clear", "low", "active", "ok", "pass"):
            return 10
        if s in ("review", "hold", "assessed", "medium", "manual"):
            return 50
        if s in ("declined", "refuse", "refused", "denied", "high", "blocked", "deny"):
            return 90
        try:
            return float(s)
        except ValueError:
            return 10


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, result=None):
        self.result = result

    def _failing(self):
        return str(self.result).strip().lower() in ("error", "unavailable", "down", "failed")

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        if self._failing():
            return False
        return True

    def send_refusal_notice(self, shipper_id, quote_id):
        if self._failing():
            return False
        return True


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff rules."""

    BASE = 25.0
    WEIGHT_RATE = 0.05
    DISTANCE_RATE = 0.12

    def price(self, weight_kg, distance_km):
        amount = self.BASE + weight_kg * self.WEIGHT_RATE + distance_km * self.DISTANCE_RATE
        return round(amount, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, result=None):
        self.result = result
        self._counter = 1000
        self.records = {}

    def _unavailable(self):
        return str(self.result).strip().lower() in ("error", "unavailable", "down", "outage")

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if self._unavailable():
            raise StoreUnavailableError("quote store unavailable")
        self._counter += 1
        quote_id = f"Q-{self._counter}"
        self.records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        rec = self.records.get(quote_id, {})
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        self.records[quote_id] = rec
        return f"{quote_id}:{status}"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value, shipper_exists):
        if not shipper_id or not shipper_exists:
            return "unknown shipper"
        for name, val in (
            ("weight_kg", weight_kg),
            ("distance_km", distance_km),
            ("declared_value", declared_value),
        ):
            if val is None or not isinstance(val, (int, float)) or isinstance(val, bool):
                return f"invalid {name}"
        if not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            return "weight out of bounds"
        if not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            return "distance out of bounds"
        if not (VALUE_MIN <= declared_value <= VALUE_MAX):
            return "declared value out of bounds"
        return None

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value, shipper_exists=True):
        reason = self._validate(shipper_id, weight_kg, distance_km, declared_value, shipper_exists)
        if reason:
            return {"status": "rejected", "reason": reason}

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError:
            return {"status": "error: store unavailable"}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self._notify_quote(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
                "risk_index": risk_index,
            }
        elif risk_index >= REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self._notify_refusal(shipper_id, quote_id)
            return {
                "status": "refused",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }
        else:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }

    def _notify_quote(self, shipper_id, quote_id, price_amount):
        try:
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
        except Exception:
            pass

    def _notify_refusal(self, shipper_id, quote_id):
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            pass


def _first(request, *keys):
    for k in keys:
        if k in request and request[k] is not None:
            return request[k]
    return None


def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = _first(request, "shipper_id", "shipperId", "shipper")
    weight_kg = _first(request, "weight_kg", "weightKg", "weight")
    distance_km = _first(request, "distance_km", "distanceKm", "distance")
    declared_value = _first(request, "declared_value", "declaredValue", "value")

    shipper_exists = True
    for k in ("shipper_exists", "shipper_found"):
        if k in request:
            shipper_exists = bool(request[k])

    screening_cfg = _first(request, "screening_result", "screening_status", "screening_service_result")
    store_cfg = _first(request, "store_result", "store_status", "quote_store_result", "quote_store_status")
    notification_cfg = _first(
        request, "notification_result", "notification_status", "notification_service_result"
    )

    screening_service = ScreeningService(screening_cfg)
    quote_store = QuoteStore(store_cfg)
    tariff_engine = TariffEngine()
    notification_service = NotificationService(notification_cfg)

    api = QuoteApi(quote_store, screening_service, tariff_engine, notification_service)

    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value, shipper_exists)