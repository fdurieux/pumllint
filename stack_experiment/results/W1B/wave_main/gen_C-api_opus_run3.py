from typing import Any


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id: str, request: dict) -> int:
        status = request.get("screening_service_status") or request.get("screening_status")
        result = request.get("screening_service_result", request.get("screening_result"))
        if status in ("error", "unavailable", "down") or result in ("error", "unavailable", "down"):
            raise ScreeningUnavailableError("screening service unavailable")
        if result is not None:
            try:
                return int(result)
            except (TypeError, ValueError):
                pass
        return 0


class TariffEngine:
    """Computes the freight price per DT-P."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        base = 0.87 * weight_kg + 1.13 * distance_km
        total = base
        if weight_kg > 1244:
            total += 316.00
        if distance_km >= 4912:
            total *= 1.19
        return round(total, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._counter = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, request: dict) -> str:
        status = request.get("quote_store_status") or request.get("store_status")
        result = request.get("quote_store_result", request.get("store_result"))
        if status in ("error", "unavailable", "down") or result in ("error", "unavailable", "down"):
            raise StoreUnavailableError("store unavailable")
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

    def update_quote(self, quote_id: str, status: str, price: float = None) -> str:
        rec = self._records.get(quote_id)
        if rec is not None:
            rec["status"] = status
            if price is not None:
                rec["price"] = price
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price) -> str:
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id) -> str:
        return "sent"


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class InvalidRequestError(Exception):
    pass


# DT-S symbolic bounds
ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine=None, quote_store=None,
                 screening_service=None, notification_service=None):
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    def _validate(self, request: dict) -> None:
        shipper_id = request.get("shipper_id")
        if not shipper_id:
            raise InvalidRequestError("shipper_id")
        try:
            weight = float(request["weight_kg"])
            distance = float(request["distance_km"])
            value = float(request["declared_value"])
        except (KeyError, TypeError, ValueError):
            raise InvalidRequestError("missing_or_nonnumeric")
        if not (3 <= weight <= 19400):
            raise InvalidRequestError("weight_kg")
        if not (25 <= distance <= 7150):
            raise InvalidRequestError("distance_km")
        if not (50 <= value <= 83000):
            raise InvalidRequestError("declared_value")

    def request_quote(self, request: dict) -> dict:
        # Step 1: validate
        try:
            self._validate(request)
        except InvalidRequestError:
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, request)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id, request)
        except ScreeningUnavailableError:
            # screening outage: price anyway, hold, no notify
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4-7: apply screening decision
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
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


def handle(request: dict) -> dict:
    api = QuoteApi()
    return api.request_quote(request)