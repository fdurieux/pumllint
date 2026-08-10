import math


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000


class InvalidRequestError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, config=None):
        self._config = config or {}

    def screen(self, shipper_id):
        raw = self._config.get("screening_status", self._config.get("screening_result"))
        if raw is None:
            raw = self._config.get("risk_index")
        if isinstance(raw, str):
            low = raw.strip().lower()
            if low in ("error", "unavailable", "down", "timeout"):
                raise ScreeningUnavailableError("screening_unavailable")
            try:
                return int(float(low))
            except ValueError:
                return 0
        if isinstance(raw, bool):
            return 0
        if isinstance(raw, (int, float)):
            return int(raw)
        return 0


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

    def __init__(self, config=None):
        self._config = config or {}
        self._seq = 0
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        status = self._config.get("store_status", self._config.get("store_result"))
        if isinstance(status, str) and status.strip().lower() in (
            "error",
            "unavailable",
            "down",
        ):
            raise StoreUnavailableError("store_unavailable")
        self._seq += 1
        quote_id = "Q-{:06d}".format(self._seq)
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

    def __init__(self, config=None):
        self._config = config or {}

    def _delivers(self):
        status = self._config.get(
            "notification_status", self._config.get("notification_result")
        )
        if isinstance(status, str) and status.strip().lower() in (
            "error",
            "failed",
            "fail",
            "unavailable",
        ):
            return "failed"
        return "delivered"

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return self._delivers()

    def send_refusal_notice(self, shipper_id, quote_id):
        return self._delivers()


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or not shipper_id.strip():
            raise InvalidRequestError("V1")
        if not self._is_number(weight_kg) or not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            raise InvalidRequestError("V2")
        if not self._is_number(distance_km) or not (
            DISTANCE_MIN <= distance_km <= DISTANCE_MAX
        ):
            raise InvalidRequestError("V3")
        if not self._is_number(declared_value) or not (
            VALUE_MIN <= declared_value <= VALUE_MAX
        ):
            raise InvalidRequestError("V4")

    @staticmethod
    def _is_number(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Step 1: validate
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except InvalidRequestError:
            return {"status": "rejected: invalid_request"}

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
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
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount
            )
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    request = request or {}
    tariff_engine = TariffEngine()
    quote_store = QuoteStore(request)
    screening_service = ScreeningService(request)
    notification_service = NotificationService(request)
    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)

    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)