import math


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class NotificationError(Exception):
    pass


# ---- DT-V bounds ----
WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000

# ---- DT-S bands ----
ACCEPT_MAX = 41
REVIEW_MIN, REVIEW_MAX = 42, 66
REFUSE_MIN = 67


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, request=None):
        self._request = request or {}

    def screen(self, shipper_id):
        raw = self._request.get("screening_result",
                                self._request.get("screening_status"))
        if raw is None:
            raw = self._request.get("risk_index", 0)
        if isinstance(raw, str):
            word = raw.strip().lower()
            if word in ("error", "unavailable", "down", "outage", "timeout"):
                raise ScreeningUnavailableError("screening unavailable")
            try:
                return int(float(word))
            except ValueError:
                return 0
        return int(raw)


class TariffEngine:
    """Computes the freight price per DT-P."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km          # P1
        if weight_kg > 1244:                                    # P2
            result += 316.00
        if distance_km >= 4912:                                 # P3
            result *= 1.19
        return round(result, 2)                                 # P4


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, request=None):
        self._request = request or {}
        self._counter = 0
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        status = str(self._request.get("store_result",
                     self._request.get("store_status", "stored"))).lower()
        if status in ("error", "unavailable", "down", "fail", "failed"):
            raise StoreUnavailableError("store unavailable")
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


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, request=None):
        self._request = request or {}

    def _failing(self):
        status = str(self._request.get("notification_result",
                     self._request.get("notification_status", "delivered"))).lower()
        return status in ("error", "fail", "failed", "undelivered", "unavailable")

    def send_quote_document(self, shipper_id, quote_id, price):
        if self._failing():
            raise NotificationError("delivery failed")
        return "delivered"

    def send_refusal_notice(self, shipper_id, quote_id):
        if self._failing():
            raise NotificationError("delivery failed")
        return "delivered"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service,
                 notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    @staticmethod
    def _is_number(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def _validate(self, req):
        shipper_id = req.get("shipper_id")
        if not isinstance(shipper_id, str) or not shipper_id.strip():
            return False
        w = req.get("weight_kg")
        if not self._is_number(w) or not (WEIGHT_MIN <= w <= WEIGHT_MAX):
            return False
        d = req.get("distance_km")
        if not self._is_number(d) or not (DISTANCE_MIN <= d <= DISTANCE_MAX):
            return False
        v = req.get("declared_value")
        if not self._is_number(v) or not (VALUE_MIN <= v <= VALUE_MAX):
            return False
        return True

    def request_quote(self, req):
        # Step 1: validation (DT-V)
        if not self._validate(req):
            return {"status": "rejected: invalid_request"}

        shipper_id = req["shipper_id"]
        weight_kg = req["weight_kg"]
        distance_km = req["distance_km"]
        declared_value = req["declared_value"]

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: price anyway, hold, do not notify
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4-6: apply DT-S
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self._notify_quote(shipper_id, quote_id, price)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            self._notify_refusal(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}

    def _notify_quote(self, shipper_id, quote_id, price):
        try:
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price)
        except NotificationError:
            pass  # fire-and-forget (DT-S note 4)

    def _notify_refusal(self, shipper_id, quote_id):
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except NotificationError:
            pass  # fire-and-forget (DT-S note 4)


def handle(request: dict) -> dict:
    request = request or {}
    tariff_engine = TariffEngine()
    quote_store = QuoteStore(request)
    screening_service = ScreeningService(request)
    notification_service = NotificationService(request)
    api = QuoteApi(tariff_engine, quote_store, screening_service,
                   notification_service)
    return api.request_quote(request)