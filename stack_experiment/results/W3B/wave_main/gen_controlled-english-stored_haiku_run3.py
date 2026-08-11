from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


class PricingError(Exception):
    pass


class StatusEnum(str, Enum):
    QUOTED = "statusQuoted"
    REVIEW_HOLD = "statusReviewHold"
    REFUSED_SCREENING = "statusRefusedScreening"
    HELD_UNSCREENED = "statusHeldUnscreened"


@dataclass
class QuoteRecord:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: str
    price_amount: Optional[float] = None


class ScreeningService:
    """External denied-party screening provider."""
    
    def __init__(self, risk_index: Optional[float] = None, error: bool = False):
        self.risk_index = risk_index
        self.error = error
    
    def screen(self, shipper_id: str) -> float:
        if self.error:
            raise ScreeningError("screeningUnavailableError")
        return self.risk_index if self.risk_index is not None else 0.0


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    def __init__(self, price_amount: Optional[float] = None, error: bool = False):
        self.price_amount = price_amount
        self.error = error
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        if self.error:
            raise PricingError("pricingUnavailableError")
        if self.price_amount is not None:
            return self.price_amount
        base_rate = 1.0
        weight_factor = weight_kg * 0.05
        distance_factor = distance_km * 0.10
        return base_rate + weight_factor + distance_factor


class QuoteStore:
    """Stores quote requests and their lifecycle status."""
    
    def __init__(self, error: bool = False):
        self.error = error
        self.quotes = {}
        self.counter = 0
    
    def store_draft(self, shipper_id: str, weight_kg: float, 
                   distance_km: float, declared_value: float) -> str:
        if self.error:
            raise StorageError("storeUnavailableError")
        self.counter += 1
        quote_id = f"QUOTE-{self.counter}"
        record = QuoteRecord(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status="draft"
        )
        self.quotes[quote_id] = record
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, 
                    price_amount: Optional[float] = None) -> QuoteRecord:
        if quote_id not in self.quotes:
            raise StorageError("quoteNotFound")
        record = self.quotes[quote_id]
        record.status = status
        if price_amount is not None:
            record.price_amount = price_amount
        self.quotes[quote_id] = record
        return record


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""
    
    def __init__(self, error: bool = False):
        self.error = error
        self.sent_documents = []
        self.sent_refusals = []
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        if self.error:
            return "deliveryError"
        self.sent_documents.append({
            "shipper_id": shipper_id,
            "quote_id": quote_id,
            "price_amount": price_amount
        })
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if self.error:
            return "deliveryError"
        self.sent_refusals.append({
            "shipper_id": shipper_id,
            "quote_id": quote_id
        })
        return "sent"


class QuoteAPI:
    """Orchestrates the quotation flow."""
    
    ACCEPT_MAX = 30.0
    REVIEW_MIN = 30.0
    REVIEW_MAX = 70.0
    REFUSE_MIN = 70.0
    
    def __init__(self, screening_service: ScreeningService, 
                 tariff_engine: TariffEngine,
                 quote_store: QuoteStore,
                 notification_service: NotificationService):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service
    
    def _validate_request(self, shipper_id: str, weight_kg: float, 
                         distance_km: float, declared_value: float) -> bool:
        if not shipper_id:
            return False
        if weight_kg <= 0 or weight_kg > 30000:
            return False
        if distance_km <= 0 or distance_km > 5000:
            return False
        if declared_value < 0 or declared_value > 1000000:
            return False
        return True
    
    def request_quote(self, shipper_id: str, weight_kg: float, 
                     distance_km: float, declared_value: float) -> dict:
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {
                "status": "rejectedInvalidRequest",
                "message": "Invalid request parameters"
            }
        
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageError:
            return {
                "status": "storeUnavailableError",
                "message": "Quote storage unavailable"
            }
        
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            risk_index = None
        
        if risk_index is None:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, StatusEnum.HELD_UNSCREENED.value, price_amount
                )
                return {
                    "status": "heldUnscreenedResponse",
                    "quote_id": quote_id,
                    "message": "Quote held pending screening"
                }
            except PricingError:
                return {
                    "status": "pricingUnavailableError",
                    "message": "Pricing service unavailable"
                }
        
        if risk_index <= self.ACCEPT_MAX:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, StatusEnum.QUOTED.value, price_amount
                )
                self.notification_service.send_quote_document(
                    shipper_id, quote_id, price_amount
                )
                return {
                    "status": "quotedResponse",
                    "quote_id": quote_id,
                    "price_amount": price_amount
                }
            except PricingError:
                return {
                    "status": "pricingUnavailableError",
                    "message": "Pricing service unavailable"
                }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(
                quote_id, StatusEnum.REVIEW_HOLD.value
            )
            return {
                "status": "reviewHoldResponse",
                "quote_id": quote_id,
                "message": "Quote held for compliance review"
            }
        
        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(
                quote_id, StatusEnum.REFUSED_SCREENING.value
            )
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refusedScreeningResponse",
                "quote_id": quote_id,
                "message": "Quote refused due to screening outcome"
            }
        
        return {
            "status": "error",
            "message": "Unexpected screening result"
        }


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0.0)
    distance_km = request.get("distance_km", 0.0)
    declared_value = request.get("declared_value", 0.0)
    
    quote_store_error = request.get("quote_store_error", False)
    screening_service_error = request.get("screening_service_error", False)
    tariff_engine_error = request.get("tariff_engine_error", False)
    notification_service_error = request.get("notification_service_error", False)
    
    screening_result = request.get("screening_result")
    tariff_result = request.get("tariff_result")
    
    screening_service = ScreeningService(
        risk_index=screening_result,
        error=screening_service_error
    )
    tariff_engine = TariffEngine(
        price_amount=tariff_result,
        error=tariff_engine_error
    )
    quote_store = QuoteStore(error=quote_store_error)
    notification_service = NotificationService(error=notification_service_error)
    
    quote_api = QuoteAPI(
        screening_service=screening_service,
        tariff_engine=tariff_engine,
        quote_store=quote_store,
        notification_service=notification_service
    )
    
    return quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)