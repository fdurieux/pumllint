import json
from typing import Any
from dataclasses import dataclass
from enum import Enum


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


class TariffError(Exception):
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
    price_amount: float = None


class QuoteStore:
    """PostgreSQL 16 quote store."""
    
    def __init__(self):
        self.quotes = {}
        self.next_id = 1
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its ID."""
        if not hasattr(self, '_available'):
            self._available = True
        
        if not self._available:
            raise StorageError("Quote store unavailable")
        
        quote_id = f"Q{self.next_id:06d}"
        self.next_id += 1
        
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
    
    def update_quote(self, quote_id: str, status: QuoteStatus, price_amount: float = None) -> Quote:
        """Update a quote status and optionally its price."""
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str) -> float:
        """Return shipper risk index (0-100)."""
        return 0.0


class TariffEngine:
    """Tariff computation engine."""
    
    _BASE_PRICE = 500.0
    _WEIGHT_RATE = 1.2
    _DISTANCE_RATE = 0.85
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute freight price from weight and distance."""
        return self._BASE_PRICE + (weight_kg * self._WEIGHT_RATE) + (distance_km * self._DISTANCE_RATE)


class NotificationService:
    """External messaging provider."""
    
    def __init__(self):
        self._available = True
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        """Send quote document. Returns confirmation or raises error."""
        if not self._available:
            raise Exception("Notification service unavailable")
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Send refusal notice. Returns confirmation or raises error."""
        if not self._available:
            raise Exception("Notification service unavailable")
        return "sent"


class QuoteAPI:
    """Quote API - orchestrates the quotation flow."""
    
    ACCEPT_MAX = 20
    REVIEW_MIN = 21
    REVIEW_MAX = 60
    REFUSE_MIN = 61
    
    def __init__(self, quote_store: QuoteStore, screening_service: ScreeningService, 
                 tariff_engine: TariffEngine, notification_service: NotificationService):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service
    
    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> None:
        """Validate quote request per decision table DT-V."""
        if not shipper_id or len(shipper_id.strip()) == 0:
            raise ValidationError("shipper_id required")
        if weight_kg is None or weight_kg < 100:
            raise ValidationError("weight_kg must be >= 100")
        if distance_km is None or distance_km <= 0:
            raise ValidationError("distance_km must be > 0")
        if declared_value is None or declared_value < 0:
            raise ValidationError("declared_value must be >= 0")
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        """Main quotation flow."""
        
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {
                "status": "rejected: invalid_request",
                "error": str(e)
            }
        
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError as e:
            return {
                "status": "error: store_unavailable",
                "error": str(e)
            }
        
        screening_failed = False
        risk_index = None
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception as e:
            screening_failed = True
        
        if screening_failed:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
            except Exception as e:
                return {
                    "status": "error: tariff_error",
                    "error": str(e)
                }
            
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True
            }
        
        if risk_index <= self.ACCEPT_MAX:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
            except Exception as e:
                return {
                    "status": "error: tariff_error",
                    "error": str(e)
                }
            
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
            
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            except Exception:
                pass
            
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount
            }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        
        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass
            
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }
        
        return {
            "status": "error: unknown_screening_state",
            "risk_index": risk_index
        }


def handle(request: dict) -> dict:
    """
    Handle a quote request end-to-end.
    
    request keys:
    - shipper_id: string
    - weight_kg: float
    - distance_km: float
    - declared_value: float
    - quote_store_available: bool (optional, default True)
    - screening_result: float (optional, risk index)
    - screening_status: string (optional, "error" means unavailable)
    - notification_status: string (optional, "error" means unavailable)
    """
    
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    
    if request.get("quote_store_available") is False:
        quote_store._available = False
    
    if request.get("screening_status") == "error":
        screening_service.screen = lambda shipper_id: (_ for _ in ()).throw(ScreeningError("Service unavailable"))
    elif "screening_result" in request:
        screening_service.screen = lambda shipper_id: request["screening_result"]
    
    if request.get("notification_status") == "error":
        notification_service._available = False
    
    api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)
    
    result = api.request_quote(
        shipper_id=request.get("shipper_id", ""),
        weight_kg=request.get("weight_kg"),
        distance_km=request.get("distance_km"),
        declared_value=request.get("declared_value")
    )
    
    return result