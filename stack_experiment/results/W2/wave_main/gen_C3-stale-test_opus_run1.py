import math


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class ScreeningUnavailableError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class NotificationError(Exception):
    pass


class InvalidRequestError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, request=None):
        self._request = request or {}

    def screen(self, shipper_id):
        status = str(self._request.get("screening_status",
                     self._request.get("screening_result", ""))).lower()
        if status in ("error", "unavailable", "outage", "down"):
            raise ScreeningUnavailableError("screening service unavailable")
        for key in ("screening_result", "risk_index", "screening_score"):
            if key in self._request:
                val = self._request[key]
                try:
                    return int(val)
                except (TypeError, ValueError):
                    pass
        return 0


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

    def __init__(self, request=None):
        self._request = request or {}
        self._counter = 0
        self._records = {}

    def _store_failing(self):
        status = str(self._request.get("store_status",
                     self._request.get("store_result", ""))).lower()
        return status in ("error", "unavailable", "down", "fail", "failed")

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if self._store_failing():
            raise StoreUnavailableError("store unavailable")
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


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, request=None):
        self._request = request or {}

    def _delivery_failing(self):
        status = str(self._request.get("notification_status",
                     self._request.get("notification_result", ""))).lower()
        return status in ("error", "unavailable", "fail", "failed", "down")

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        if self._delivery_failing():
            raise NotificationError("delivery failed")
        return "delivered"

    def send_refusal_notice(self, shipper_id, quote_id):
        if self._delivery_failing():
            raise NotificationError("delivery failed")
        return "delivered"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or not shipper_id:
            return False
        if not self._is_number(weight_kg) or not (3 <= weight_kg <= 19400):
            return False
        if not self._is_number(distance_km) or not (25 <= distance_km <= 7150):
            return False
        if not self._is_number(declared_value) or not (50 <= declared_value <= 83000):
            return False
        return True

    @staticmethod
    def _is_number(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Step 1: validate
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

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
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4-6: apply screening decision
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            try:
                self.notification_service.send_quote_document(
                    shipper_id, quote_id, price_amount)
            except NotificationError:
                pass
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}

        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        else:  # risk_index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except NotificationError:
                pass
            return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    request = request or {}
    quote_store = QuoteStore(request)
    screening_service = ScreeningService(request)
    tariff_engine = TariffEngine()
    notification_service = NotificationService(request)
    api = QuoteApi(quote_store, screening_service, tariff_engine, notification_service)

    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)