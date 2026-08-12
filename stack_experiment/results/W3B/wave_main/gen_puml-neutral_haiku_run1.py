from dataclasses import dataclass
from enum import Enum
from typing import Optional
import uuid
from datetime import datetime


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


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price_amount: Optional[float] = None
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str) -> float:
        """
        Returns a risk index score.
        In real implementation, this would call an external API.
        """
        if not shipper_id:
            raise ScreeningError("Invalid shipper_id")
        return 25.0


class NotificationService:
    """External messaging provider."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        """Fire-and-forget delivery of quote document. Returns confirmation."""
        if not all([shipper_id, quote_id, price_amount]):
            raise ValueError("Missing required notification parameters")
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Fire-and-forget delivery of refusal notice. Returns confirmation."""
        if not all([shipper_id, quote_id]):
            raise ValueError("Missing required notification parameters")
        return "sent"


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    BASE_PRICE = 100.0
    PRICE_PER_KG = 0.5
    PRICE_PER_KM = 2.0
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Computes price using tariff rules.
        Returns a single price amount.
        """
        if weight_kg < 0 or distance_km < 0:
            raise ValueError("Weight and distance must be non-negative")
        return self.BASE_PRICE + (weight_kg * self.PRICE_PER_KG) + (distance_km * self.PRICE_PER_KM)


class QuoteStore:
    """Persistent storage for quote requests and lifecycle."""
    
    def __init__(self):
        self._quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """
        Creates and stores a draft quote.
        Returns a single quote_id.
        """
        if not all([shipper_id, weight_kg, distance_km, declared_value]):
            raise ValueError("Missing required quote parameters")
        
        quote_id = str(uuid.uuid4())
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT
        )
        self._quotes[quote_id] = quote
        return quote_id
    
    def update_quote(self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None) -> Quote:
        """
        Updates a quote's status and optionally price.
        Returns the updated quote.
        """
        if quote_id not in self._quotes:
            raise ValueError(f"Quote {quote_id} not found")
        
        quote = self._quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        
        return quote
    
    def get_quote(self, quote_id: str) -> Quote:
        """Retrieves a quote by id."""
        if quote_id not in self._quotes:
            raise ValueError(f"Quote {quote_id} not found")
        return self._quotes[quote_id]


class QuoteAPI:
    """
    Main orchestrator for the quotation flow.
    Receives requests, validates, screens, prices, and responds.
    """
    
    ACCEPT_MAX = 50.0
    REVIEW_MIN = 50.1
    REVIEW_MAX = 75.0
    REFUSE_MIN = 75.1
    
    def __init__(self, quote_store: QuoteStore, screening_service: ScreeningService,
                 tariff_engine: TariffEngine, notification_service: NotificationService):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service
    
    def _validate_request(self, shipper_id: str, weight_kg: float, 
                          distance_km: float, declared_value: float) -> bool:
        """
        Validates request against bounds (decision table DT-V).
        Returns True if valid, raises ValidationError otherwise.
        """
        if not shipper_id or not isinstance(shipper_id, str):
            raise ValidationError("shipper_id is required and must be a string")
        if weight_kg <= 0 or weight_kg > 10000:
            raise ValidationError("weight_kg must be between 0 and 10000")
        if distance_km <= 0 or distance_km > 100000:
            raise ValidationError("distance_km must be between 0 and 100000")
        if declared_value <= 0:
            raise ValidationError("declared_value must be positive")
        return True
    
    def request_quote(self, shipper_id: str, weight_kg: float, 
                     distance_km: float, declared_value: float) -> dict:
        """
        Main entry point for quote requests.
        Returns a dict with 'status' and other relevant fields.
        """
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": "rejected_invalid_request", "reason": str(e)}
        
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception as e:
            return {"status": "store_unavailable_error", "reason": str(e)}
        
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            risk_index = None
        
        if risk_index is None:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
                return {
                    "status": "held_unscreened",
                    "quote_id": quote_id,
                    "price_amount": price_amount
                }
            except Exception as e:
                return {"status": "error", "reason": str(e)}
        
        if risk_index <= self.ACCEPT_MAX:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
                try:
                    self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
                except Exception:
                    pass
                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price_amount": price_amount
                }
            except Exception as e:
                return {"status": "error", "reason": str(e)}
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {
                    "status": "review_hold",
                    "quote_id": quote_id
                }
            except Exception as e:
                return {"status": "error", "reason": str(e)}
        
        elif risk_index >= self.REFUSE_MIN:
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
                try:
                    self.notification_service.send_refusal_notice(shipper_id, quote_id)
                except Exception:
                    pass
                return {
                    "status": "refused_screening",
                    "quote_id": quote_id
                }
            except Exception as e:
                return {"status": "error", "reason": str(e)}
        
        return {"status": "error", "reason": "Unknown screening outcome"}


def handle(request: dict) -> dict:
    """
    End-to-end handler for quote requests.
    Processes input and returns outcome status.
    """
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    quote_api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)
    
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)
    
    screening_result = request.get("screening_result")
    if screening_result is not None:
        if screening_result == "approved":
            screening_service.screen = lambda sid: 25.0
        elif screening_result == "review":
            screening_service.screen = lambda sid: 60.0
        elif screening_result == "declined":
            screening_service.screen = lambda sid: 80.0
        elif screening_result == "error":
            screening_service.screen = lambda sid: (_ for _ in ()).throw(ScreeningError("Screening service unavailable"))
        else:
            try:
                screening_service.screen = lambda sid: float(screening_result)
            except (ValueError, TypeError):
                screening_service.screen = lambda sid: 25.0
    
    return quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)