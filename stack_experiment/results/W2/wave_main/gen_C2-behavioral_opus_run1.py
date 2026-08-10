import math


class ScreeningUnavailableError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


# --- Decision table constants ---
ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, risk_index=12, available=True):
        self._risk_index = risk_index
        self._available = available

    def screen(self, shipper_id):
        if not self._available:
            raise ScreeningUnavailableError("screening_unavailable")
        return int(self._risk_index)


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, delivers=True):
        self._delivers = delivers

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        if not self._delivers:
            return "delivery_failed"
        return "delivered"

    def send_refusal_notice(self, shipper_id, quote_id):
        if not self._delivers:
            return "delivery_failed"
        return "delivered"


class TariffEngine:
    """Computes the freight price per DT-P."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km  # P1
        if weight_kg > 1244:  # P2
            result += 316.00
        if distance_km >= 4912:  # P3
            result *= 1.19
        return round(result, 2)  # P4


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self._available = available
        self._records = {}
        self._counter = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._available:
            raise StoreUnavailableError("store_unavailable")
        self._counter += 1
        quote_id = "Q-%04d" % self._counter
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
        return "updated"


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
        for value, lo, hi in (
            (weight_kg, WEIGHT_MIN, WEIGHT_MAX),
            (distance_km, DISTANCE_MIN, DISTANCE_MAX),
            (declared_value, VALUE_MIN, VALUE_MAX),
        ):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return False
            if value < lo or value > hi:
                return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Step 1 — validate (DT-V)
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # Step 2 — store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3 — screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage: price anyway, hold, do not notify (DT-S note 5)
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4/5/6 — apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount
            )  # fire-and-forget
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}

        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        else:  # risk_index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(
                shipper_id, quote_id
            )  # fire-and-forget
            return {"status": "refused_screening", "quote_id": quote_id}


def _is_unavailable(word):
    if word is None:
        return False
    return str(word).strip().lower() in ("error", "unavailable", "down", "failed", "false")


def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    # Store availability
    store_available = True
    store_signal = request.get("store_status", request.get("store_result"))
    if store_signal is not None and _is_unavailable(store_signal):
        store_available = False
    if request.get("store_exists") is False or request.get("store_found") is False:
        store_available = False

    # Screening availability / risk index
    screening_available = True
    risk_index = 12
    screening_signal = request.get("screening_result", request.get("screening_status"))
    if screening_signal is not None:
        if isinstance(screening_signal, bool):
            screening_available = screening_signal
        elif isinstance(screening_signal, (int, float)):
            risk_index = int(screening_signal)
        elif _is_unavailable(screening_signal):
            screening_available = False
    if "risk_index" in request:
        try:
            risk_index = int(request["risk_index"])
        except (TypeError, ValueError):
            pass

    # Notification delivery
    notification_delivers = True
    notify_signal = request.get("notification_result", request.get("notification_status"))
    if notify_signal is not None and _is_unavailable(notify_signal):
        notification_delivers = False

    tariff_engine = TariffEngine()
    quote_store = QuoteStore(available=store_available)
    screening_service = ScreeningService(
        risk_index=risk_index, available=screening_available
    )
    notification_service = NotificationService(delivers=notification_delivers)

    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)
    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)