from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime
import uuid


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


class PricingError(Exception):
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
    price_amount: Optional[float] = None
    risk_index: Optional[float] = None
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow().isoformat()


class QuoteStore:
    def __init__(self):
        self.quotes = {}
        self.storage_available = True

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if not self.storage_available:
            raise StorageError("Quote storage unavailable")
        
        quote_id = str(uuid.uuid4())
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT
        )
        self.quotes[quote_id] = quote
        return quote_id

    def update_quote(self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None) -> Quote:
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        quote.updated_at = datetime.utcnow().isoformat()
        return quote

    def get_quote(self, quote_id: str) -> Optional[Quote]:
        return self.quotes.get(quote_id)


class ScreeningService:
    def __init__(self):
        self.available = True
        self.result = None

    def screen(self, shipper_id: str) -> float:
        if not self.available:
            raise ScreeningError("Screening service unavailable")
        
        if self.result is not None:
            return self.result
        return 0.0


class TariffEngine:
    def __init__(self):
        self.base_rate_per_ton_km = 2.5
        self.available = True

    def price(self, weight_kg: float, distance_km: float) -> float:
        if not self.available:
            raise PricingError("Tariff engine unavailable")
        
        weight_tons = weight_kg / 1000.0
        total_ton_km = weight_tons * distance_km
        return total_ton_km * self.base_rate_per_ton_km


class NotificationService:
    def __init__(self):
        self.available = True

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        if not self.available:
            return "notification_failed"
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if not self.available:
            return "notification_failed"
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 30.0
    REVIEW_MIN = 30.0
    REVIEW_MAX = 70.0
    REFUSE_MIN = 70.0

    MIN_WEIGHT_KG = 100.0
    MAX_WEIGHT_KG = 25000.0
    MIN_DISTANCE_KM = 10.0
    MAX_DISTANCE_KM = 3000.0
    MIN_DECLARED_VALUE = 100.0

    def __init__(self, quote_store: QuoteStore, screening_service: ScreeningService,
                 tariff_engine: TariffEngine, notification_service: NotificationService):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> None:
        if not shipper_id or len(shipper_id.strip()) == 0:
            raise ValidationError("Shipper ID is required")
        
        if weight_kg < self.MIN_WEIGHT_KG or weight_kg > self.MAX_WEIGHT_KG:
            raise ValidationError(f"Weight must be between {self.MIN_WEIGHT_KG} and {self.MAX_WEIGHT_KG} kg")
        
        if distance_km < self.MIN_DISTANCE_KM or distance_km > self.MAX_DISTANCE_KM:
            raise ValidationError(f"Distance must be between {self.MIN_DISTANCE_KM} and {self.MAX_DISTANCE_KM} km")
        
        if declared_value < self.MIN_DECLARED_VALUE:
            raise ValidationError(f"Declared value must be at least {self.MIN_DECLARED_VALUE}")

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": f"rejected_invalid_request: {str(e)}"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError as e:
            return {"status": f"error: store_unavailable"}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            risk_index = None

        if risk_index is not None:
            if risk_index <= self.ACCEPT_MAX:
                try:
                    price_amount = self.tariff_engine.price(weight_kg, distance_km)
                except PricingError:
                    return {"status": "error: pricing_unavailable"}

                self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
                self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price_amount": price_amount
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
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
            except PricingError:
                return {"status": "error: pricing_unavailable"}

            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price_amount": price_amount
            }


_quote_store = QuoteStore()
_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_notification_service = NotificationService()
_quote_api = QuoteAPI(_quote_store, _screening_service, _tariff_engine, _notification_service)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0.0)
    distance_km = request.get("distance_km", 0.0)
    declared_value = request.get("declared_value", 0.0)

    if "quote_store_available" in request:
        _quote_store.storage_available = request["quote_store_available"]

    if "screening_service_available" in request:
        _screening_service.available = request["screening_service_available"]

    if "screening_service_result" in request:
        _screening_service.result = request["screening_service_result"]

    if "tariff_engine_available" in request:
        _tariff_engine.available = request["tariff_engine_available"]

    if "notification_service_available" in request:
        _notification_service.available = request["notification_service_available"]

    return _quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)