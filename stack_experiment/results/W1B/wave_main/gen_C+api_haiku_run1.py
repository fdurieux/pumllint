from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price: Optional[float] = None


class QuoteStore:
    def __init__(self):
        self.quotes = {}
        self._counter = 0

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if not hasattr(self, '_available') or self._available is False:
            raise StorageError("store_unavailable")
        self._counter += 1
        quote_id = f"Q{self._counter:06d}"
        self.quotes[quote_id] = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT
        )
        return quote_id

    def update_quote(self, quote_id: str, status: QuoteStatus, price: Optional[float] = None) -> Quote:
        if quote_id not in self.quotes:
            raise StorageError(f"quote_not_found: {quote_id}")
        quote = self.quotes[quote_id]
        quote.status = status
        if price is not None:
            quote.price = price
        return quote


class TariffEngine:
    def __init__(self):
        self._base_rate_per_kg_km = 0.05
        self._minimum_charge = 50.0

    def price(self, weight_kg: float, distance_km: float) -> float:
        if not hasattr(self, '_available') or self._available is False:
            raise ScreeningError("pricing_unavailable")
        price = weight_kg * distance_km * self._base_rate_per_kg_km
        return max(price, self._minimum_charge)


class ScreeningService:
    def screen(self, shipper_id: str) -> float:
        if not hasattr(self, '_available') or self._available is False:
            raise ScreeningError("screening_unavailable")
        if hasattr(self, '_risk_index'):
            return self._risk_index
        return 25.0


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        if not hasattr(self, '_available') or self._available is False:
            return "notification_failed"
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if not hasattr(self, '_available') or self._available is False:
            return "notification_failed"
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 30.0
    REVIEW_MIN = 30.0
    REVIEW_MAX = 70.0
    REFUSE_MIN = 70.0

    def __init__(self, tariff_engine: TariffEngine, quote_store: QuoteStore,
                 screening_service: ScreeningService, notification_service: NotificationService):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        if not shipper_id or len(shipper_id) < 1:
            return False
        if weight_kg < 3 or weight_kg > 19400:
            return False
        if distance_km < 25 or distance_km > 7150:
            return False
        if declared_value < 50 or declared_value > 83000:
            return False
        return True

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {
                "status": "rejected: invalid_request"
            }

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError:
            return {
                "status": "error: store_unavailable"
            }

        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_available = True
        except ScreeningError:
            risk_index = None
            screening_available = False

        if screening_available:
            if risk_index <= self.ACCEPT_MAX:
                try:
                    price = self.tariff_engine.price(weight_kg, distance_km)
                except ScreeningError:
                    return {
                        "status": "error: pricing_unavailable",
                        "quote_id": quote_id
                    }
                self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price)
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price": price
                }
            elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {
                    "status": "review_hold",
                    "quote_id": quote_id
                }
            elif risk_index >= self.REFUSE_MIN:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
                return {
                    "status": "refused_screening",
                    "quote_id": quote_id
                }
        else:
            try:
                price = self.tariff_engine.price(weight_kg, distance_km)
            except ScreeningError:
                return {
                    "status": "error: pricing_unavailable",
                    "quote_id": quote_id
                }
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }

        return {
            "status": "error: unknown_state",
            "quote_id": quote_id
        }


_quote_api: Optional[QuoteAPI] = None


def _get_api() -> QuoteAPI:
    global _quote_api
    if _quote_api is None:
        quote_store = QuoteStore()
        tariff_engine = TariffEngine()
        screening_service = ScreeningService()
        notification_service = NotificationService()
        _quote_api = QuoteAPI(tariff_engine, quote_store, screening_service, notification_service)
    return _quote_api


def handle(request: dict) -> dict:
    api = _get_api()

    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    if "quote_store_available" in request:
        api.quote_store._available = request["quote_store_available"]

    if "screening_service_result" in request:
        result = request["screening_service_result"]
        if isinstance(result, (int, float)):
            api.screening_service._risk_index = result
        elif result == "unavailable":
            api.screening_service._available = False

    if "tariff_engine_available" in request:
        api.tariff_engine._available = request["tariff_engine_available"]

    if "notification_service_available" in request:
        api.notification_service._available = request["notification_service_available"]

    response = api.request_quote(shipper_id, weight_kg, distance_km, declared_value)

    return response