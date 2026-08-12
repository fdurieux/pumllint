import math


ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70

WEIGHT_MIN = 1
WEIGHT_MAX = 30000
DISTANCE_MIN = 1
DISTANCE_MAX = 5000
VALUE_MIN = 0
VALUE_MAX = 10_000_000

BASE_PRICE = 25.0
RATE_PER_KG = 0.15
RATE_PER_KM = 0.85


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class InvalidRequestError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, status=None, result=None):
        if status == "error":
            raise ScreeningUnavailableError("screening_unavailable")
        if result is not None:
            return int(result)
        # plausible default risk index
        return 10


class TariffEngine:
    """Computes the freight price from weight and distance."""

    def price(self, weight_kg, distance_km):
        amount = BASE_PRICE + weight_kg * RATE_PER_KG + distance_km * RATE_PER_KM
        return round(amount, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._counter = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, status=None):
        if status == "error":
            raise StoreUnavailableError("store_unavailable")
        self._counter += 1
        quote_id = "Q%05d" % self._counter
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
        record = self._records.get(quote_id)
        if record is None:
            raise StoreUnavailableError("store_unavailable")
        record["status"] = status
        if price is not None:
            record["price"] = price
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price, status=None):
        if status == "error":
            return "delivery_failed"
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id, status=None):
        if status == "error":
            return "delivery_failed"
        return "sent"


class QuoteAPI:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or not shipper_id.strip():
            raise InvalidRequestError("invalid_request")
        for value in (weight_kg, distance_km, declared_value):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise InvalidRequestError("invalid_request")
        if not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            raise InvalidRequestError("invalid_request")
        if not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            raise InvalidRequestError("invalid_request")
        if not (VALUE_MIN <= declared_value <= VALUE_MAX):
            raise InvalidRequestError("invalid_request")

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value,
                      store_status=None, screening_status=None, screening_result=None,
                      notification_status=None):
        # 1. Validate
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except InvalidRequestError:
            return {"status": "rejected: invalid_request"}

        # 2. Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, status=store_status)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # 3. Screening
        try:
            risk_index = self.screening_service.screen(
                shipper_id, status=screening_status, result=screening_result)
        except ScreeningUnavailableError:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4-7. Apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price, status=notification_status)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(
                shipper_id, quote_id, status=notification_status)
            return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)

    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    store_status = request.get("store_result", request.get("store_status"))
    screening_status = request.get("screening_status")
    screening_result = request.get("screening_result")
    notification_status = request.get("notification_result", request.get("notification_status"))

    # A numeric screening_result is a risk index; a word status like "error" is an outage.
    if isinstance(screening_result, str):
        if screening_result.lower() in ("error", "unavailable"):
            screening_status = "error"
            screening_result = None
        else:
            try:
                screening_result = int(screening_result)
            except (TypeError, ValueError):
                screening_result = None

    if isinstance(store_status, str) and store_status.lower() in ("stored", "ok", "active"):
        store_status = None

    return api.request_quote(
        shipper_id, weight_kg, distance_km, declared_value,
        store_status=store_status,
        screening_status=screening_status,
        screening_result=screening_result,
        notification_status=notification_status,
    )