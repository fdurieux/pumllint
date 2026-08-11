from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


class ValidationError(Exception):
    pass


class StorageUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
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
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class QuoteStore:
    def __init__(self):
        self.quotes: dict[str, Quote] = {}
        self.available = True

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if not self.available:
            raise StorageUnavailableError("Quote store unavailable")
        
        quote_id = str(uuid4())
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
        if not self.available:
            raise StorageUnavailableError("Quote store unavailable")
        
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        quote.updated_at = datetime.utcnow()
        return quote


class ScreeningService:
    def __init__(self):
        self.available = True
        self.default_result = None

    def screen(self, shipper_id: str) -> float:
        if not self.available:
            raise ScreeningUnavailableError("Screening service unavailable")
        
        if self.default_result is not None:
            return self.default_result
        
        return 50.0


class TariffEngine:
    PRICE_PER_KG = 0.50
    PRICE_PER_KM = 2.00
    BASE_PRICE = 100.00

    def __init__(self):
        self.available = True
        self.default_result = None

    def price(self, weight_kg: float, distance_km: float) -> float:
        if not self.available:
            raise Exception("Tariff engine unavailable")
        
        if self.default_result is not None:
            return self.default_result
        
        return self.BASE_PRICE + (weight_kg * self.PRICE_PER_KG) + (distance_km * self.PRICE_PER_KM)


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
    ACCEPT_MAX = 40.0
    REVIEW_MIN = 41.0
    REVIEW_MAX = 70.0
    REFUSE_MIN = 71.0

    def __init__(self, quote_store: QuoteStore, screening_service: ScreeningService,
                 tariff_engine: TariffEngine, notification_service: NotificationService):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {
                "status": "rejected_invalid_request",
                "reason": "Request validation failed"
            }

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageUnavailableError:
            return {
                "status": "store_unavailable_error",
                "reason": "Quote store is unavailable"
            }

        screening_failed = False
        risk_index = None

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            screening_failed = True

        if screening_failed:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "reason": "Screening service unavailable"
            }

        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount
            }

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "reason": "Shipper requires manual compliance review"
            }

        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
                "reason": "Shipper screening failed"
            }

        return {
            "status": "error",
            "reason": "Unexpected screening result"
        }

    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        if not shipper_id or not isinstance(shipper_id, str):
            return False
        if weight_kg <= 0 or weight_kg > 50000:
            return False
        if distance_km <= 0 or distance_km > 10000:
            return False
        if declared_value < 0 or declared_value > 1000000:
            return False
        return True


def handle(request: dict) -> dict:
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    quote_api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)

    if "store_available" in request and not request["store_available"]:
        quote_store.available = False

    if "screening_available" in request and not request["screening_available"]:
        screening_service.available = False

    if "screening_result" in request:
        screening_service.default_result = request["screening_result"]

    if "tariff_result" in request:
        tariff_engine.default_result = request["tariff_result"]

    if "notification_available" in request and not request["notification_available"]:
        notification_service.available = False

    shipper_id = request.get("shipper_id", "shipper_001")
    weight_kg = request.get("weight_kg", 100.0)
    distance_km = request.get("distance_km", 500.0)
    declared_value = request.get("declared_value", 10000.0)

    try:
        result = quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
        return result
    except Exception as e:
        return {
            "status": f"error: {str(e)}"
        }