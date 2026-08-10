import json
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class QuoteRequest:
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float

@dataclass
class QuoteRecord:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: str
    risk_index: Optional[int] = None
    price: Optional[float] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

class ScreeningService:
    """External denied-party screening provider."""
    
    def __init__(self):
        self.available = True
        self.risk_index_value = None
    
    def assess_shipper(self, shipper_id: str) -> int:
        """Returns the shipper risk index; higher is worse."""
        if not self.available:
            raise Exception("screening_unavailable")
        return self.risk_index_value if self.risk_index_value is not None else 0

class TariffEngine:
    """Computes freight price from weight and distance per tariff rules (DT-P)."""
    
    def compute_price(self, weight_kg: float, distance_km: float) -> float:
        """
        DT-P pricing rules:
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00
        P3: if distance_km >= 4912, multiply by 1.19 (after P2)
        P4: round to 2 decimal places
        """
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        if weight_kg > 1244:
            base += 316.00
        
        if distance_km >= 4912:
            base *= 1.19
        
        price = round(base, 2)
        return price

class QuoteStore:
    """PostgreSQL 16 quote store."""
    
    def __init__(self):
        self.quotes = {}
        self.available = True
        self._next_id = 1000
    
    def store_draft(self, request: QuoteRequest) -> str:
        """Store a draft quote; return quote_id."""
        if not self.available:
            raise Exception("store_unavailable")
        
        quote_id = f"Q{self._next_id}"
        self._next_id += 1
        
        record = QuoteRecord(
            quote_id=quote_id,
            shipper_id=request.shipper_id,
            weight_kg=request.weight_kg,
            distance_km=request.distance_km,
            declared_value=request.declared_value,
            status="draft"
        )
        self.quotes[quote_id] = record
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, 
                    risk_index: Optional[int] = None, 
                    price: Optional[float] = None) -> None:
        """Update quote status and optionally risk_index and price."""
        if quote_id in self.quotes:
            record = self.quotes[quote_id]
            record.status = status
            if risk_index is not None:
                record.risk_index = risk_index
            if price is not None:
                record.price = price

class NotificationService:
    """External messaging provider."""
    
    def __init__(self):
        self.available = True
        self.messages = []
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        """Send quote document to shipper; return confirmation."""
        if not self.available:
            raise Exception("notification_failed")
        self.messages.append({
            "type": "quote_document",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
            "price": price
        })
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Send refusal notice to shipper; return confirmation."""
        if not self.available:
            raise Exception("notification_failed")
        self.messages.append({
            "type": "refusal_notice",
            "shipper_id": shipper_id,
            "quote_id": quote_id
        })
        return "sent"

class QuoteAPI:
    """Main orchestrator for the quotation flow."""
    
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def __init__(self, screening_service: ScreeningService, 
                 tariff_engine: TariffEngine,
                 quote_store: QuoteStore,
                 notification_service: NotificationService):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service
    
    def validate_request(self, request_dict: dict) -> Optional[str]:
        """
        Validate request per DT-V.
        Return error message if invalid, None if valid.
        """
        if not isinstance(request_dict.get("shipper_id"), str) or not request_dict.get("shipper_id"):
            return "invalid_request"
        
        weight_kg = request_dict.get("weight_kg")
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return "invalid_request"
        
        distance_km = request_dict.get("distance_km")
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return "invalid_request"
        
        declared_value = request_dict.get("declared_value")
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return "invalid_request"
        
        return None
    
    def handle_request(self, request_dict: dict) -> dict:
        """Main quotation flow orchestrator."""
        
        validation_error = self.validate_request(request_dict)
        if validation_error:
            return {"status": f"rejected: {validation_error}"}
        
        request = QuoteRequest(
            shipper_id=request_dict["shipper_id"],
            weight_kg=request_dict["weight_kg"],
            distance_km=request_dict["distance_km"],
            declared_value=request_dict["declared_value"]
        )
        
        try:
            quote_id = self.quote_store.store_draft(request)
        except Exception as e:
            if str(e) == "store_unavailable":
                return {"status": "error: store_unavailable"}
            raise
        
        response = {"status": None, "quote_id": quote_id}
        
        risk_index = None
        try:
            risk_index = self.screening_service.assess_shipper(request.shipper_id)
        except Exception as e:
            if str(e) == "screening_unavailable":
                price = self.tariff_engine.compute_price(request.weight_kg, request.distance_km)
                self.quote_store.update_quote(quote_id, "held_unscreened", price=price)
                response["status"] = "held_unscreened"
                response["price"] = price
                response["hold"] = True
                return response
            raise
        
        self.quote_store.update_quote(quote_id, status="draft", risk_index=risk_index)
        
        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.compute_price(request.weight_kg, request.distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price=price)
            response["status"] = "quoted"
            response["price"] = price
            
            try:
                self.notification_service.send_quote_document(request.shipper_id, quote_id, price)
            except Exception:
                pass
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            response["status"] = "review_hold"
        
        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            response["status"] = "refused_screening"
            
            try:
                self.notification_service.send_refusal_notice(request.shipper_id, quote_id)
            except Exception:
                pass
        
        return response

_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_quote_store = QuoteStore()
_notification_service = NotificationService()
_quote_api = QuoteAPI(_screening_service, _tariff_engine, _quote_store, _notification_service)

def handle(request: dict) -> dict:
    """
    Handle one end-to-end quotation flow.
    
    request carries scenario input:
    - entity ids and amounts (shipper_id, weight_kg, distance_km, declared_value)
    - existence flags like "screening_service_available"
    - outcome keys like "screening_service_result" for risk index
    - outcome keys like "notification_service_status" for delivery outcome
    """
    
    if "screening_service_available" in request:
        _screening_service.available = request["screening_service_available"]
    if "quote_store_available" in request:
        _quote_store.available = request["quote_store_available"]
    if "notification_service_available" in request:
        _notification_service.available = request["notification_service_available"]
    
    if "screening_service_result" in request:
        _screening_service.risk_index_value = request["screening_service_result"]
    
    request_dict = {
        k: request[k] for k in ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        if k in request
    }
    
    return _quote_api.handle_request(request_dict)