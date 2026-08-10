import json
import uuid
from dataclasses import dataclass, asdict
from typing import Optional
from enum import Enum


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


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningService:
    def screen(self, shipper_id: str) -> Optional[int]:
        return None

    def get_risk_index(self, shipper_id: str) -> Optional[int]:
        return self.screen(shipper_id)


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        if weight_kg > 1244:
            base += 316.00
        
        if distance_km >= 4912:
            base *= 1.19
        
        return round(base, 2)


class QuoteStore:
    def __init__(self):
        self.quotes = {}

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        quote_id = str(uuid.uuid4())
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT,
            price=None,
        )
        self.quotes[quote_id] = quote
        return quote_id

    def update_quote(
        self, quote_id: str, status: QuoteStatus, price: Optional[float] = None
    ) -> Quote:
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price is not None:
            quote.price = price
        return quote

    def get_quote(self, quote_id: str) -> Optional[Quote]:
        return self.quotes.get(quote_id)


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> bool:
        return True

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> bool:
        return True


class QuoteAPI:
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def __init__(
        self,
        quote_store: QuoteStore,
        tariff_engine: TariffEngine,
        screening_service: ScreeningService,
        notification_service: NotificationService,
    ):
        self.quote_store = quote_store
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate_request(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> None:
        if not shipper_id or shipper_id.strip() == "":
            raise ValidationError("shipper_id must be present and non-empty")
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            raise ValidationError("weight_kg must be a number between 3 and 19400")
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            raise ValidationError("distance_km must be a number between 25 and 7150")
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            raise ValidationError("declared_value must be a number between 50 and 83000")

    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError:
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError:
            return {"status": "error: store_unavailable"}

        risk_index = self.screening_service.get_risk_index(shipper_id)
        
        if risk_index is None:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }

        return {"status": "error: store_unavailable"}


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)

    screening_result = request.get("screening_service_result")
    notification_status = request.get("notification_service_status")
    storage_status = request.get("quote_store_status")

    class TestScreeningService(ScreeningService):
        def get_risk_index(self, shipper_id: str) -> Optional[int]:
            if screening_result == "unavailable":
                return None
            if isinstance(screening_result, int):
                return screening_result
            return None

    class TestNotificationService(NotificationService):
        def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> bool:
            if notification_status == "error":
                return False
            return True

        def send_refusal_notice(self, shipper_id: str, quote_id: str) -> bool:
            if notification_status == "error":
                return False
            return True

    class TestQuoteStore(QuoteStore):
        def store_draft(
            self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
        ) -> str:
            if storage_status == "unavailable":
                raise StorageError("storage unavailable")
            return super().store_draft(shipper_id, weight_kg, distance_km, declared_value)

    quote_store = TestQuoteStore()
    tariff_engine = TariffEngine()
    screening_service = TestScreeningService()
    notification_service = TestNotificationService()

    api = QuoteAPI(quote_store, tariff_engine, screening_service, notification_service)

    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)