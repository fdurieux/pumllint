from dataclasses import dataclass
from typing import Optional
from enum import Enum


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


class PricingError(Exception):
    pass


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price_amount: Optional[float] = None


class ScreeningService:
    def screen(self, shipper_id: str) -> float:
        return 45.0


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base_rate = 0.5
        distance_multiplier = 1.0 + (distance_km / 1000.0) * 0.1
        return weight_kg * base_rate * distance_multiplier


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class QuoteStore:
    def __init__(self):
        self.quotes = {}
        self.next_id = 1

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        quote_id = f"Q{self.next_id:06d}"
        self.next_id += 1
        self.quotes[quote_id] = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT
        )
        return quote_id

    def update_quote(self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None) -> Quote:
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote


class QuoteAPI:
    ACCEPT_MAX = 50
    REVIEW_MIN = 51
    REVIEW_MAX = 75
    REFUSE_MIN = 76

    WEIGHT_MIN = 100.0
    WEIGHT_MAX = 24000.0
    DISTANCE_MIN = 10.0
    DISTANCE_MAX = 3000.0
    VALUE_MIN = 1.0
    VALUE_MAX = 1000000.0

    def __init__(self, screening_service: ScreeningService, tariff_engine: TariffEngine,
                 quote_store: QuoteStore, notification_service: NotificationService):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service

    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        if not shipper_id or len(shipper_id.strip()) == 0:
            return False
        if weight_kg < self.WEIGHT_MIN or weight_kg > self.WEIGHT_MAX:
            return False
        if distance_km < self.DISTANCE_MIN or distance_km > self.DISTANCE_MAX:
            return False
        if declared_value < self.VALUE_MIN or declared_value > self.VALUE_MAX:
            return False
        return True

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected_invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception as e:
            return {"status": "store_unavailable_error", "error": str(e)}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception as e:
            risk_index = None

        if risk_index is None:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
                return {
                    "status": "held_unscreened_response",
                    "quote_id": quote_id,
                    "price_amount": price_amount
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        if risk_index <= self.ACCEPT_MAX:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
                try:
                    self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
                except Exception:
                    pass
                return {
                    "status": "quoted_response",
                    "quote_id": quote_id,
                    "price_amount": price_amount
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {
                    "status": "review_hold_response",
                    "quote_id": quote_id
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        elif risk_index >= self.REFUSE_MIN:
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
                try:
                    self.notification_service.send_refusal_notice(shipper_id, quote_id)
                except Exception:
                    pass
                return {
                    "status": "refused_screening_response",
                    "quote_id": quote_id
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        return {"status": "error", "error": "Unexpected screening result"}


def handle(request: dict) -> dict:
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    quote_api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)

    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0.0)
    distance_km = request.get("distance_km", 0.0)
    declared_value = request.get("declared_value", 0.0)

    if "screening_service_result" in request:
        screening_result = request["screening_service_result"]
        if isinstance(screening_result, (int, float)):
            screening_service.screen = lambda sid: float(screening_result)
        elif screening_result == "error":
            screening_service.screen = lambda sid: (_ for _ in ()).throw(ScreeningError("Service unavailable"))

    if "tariff_engine_result" in request:
        tariff_result = request["tariff_engine_result"]
        if isinstance(tariff_result, (int, float)):
            tariff_engine.price = lambda w, d: float(tariff_result)
        elif tariff_result == "error":
            tariff_engine.price = lambda w, d: (_ for _ in ()).throw(PricingError("Service unavailable"))

    if "quote_store_result" in request:
        store_result = request["quote_store_result"]
        if store_result == "error":
            original_store_draft = quote_store.store_draft
            quote_store.store_draft = lambda sid, w, d, v: (_ for _ in ()).throw(StorageError("Storage unavailable"))

    result = quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)

    return result