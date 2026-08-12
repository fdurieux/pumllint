import uuid
from typing import Optional
from datetime import datetime


class QuoteStore:
    """PostgreSQL 16 quote store."""
    
    def __init__(self):
        self.quotes = {}
        self.available = True
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if not self.available:
            raise Exception("store_unavailable")
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "quote_id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
            "created_at": datetime.now().isoformat(),
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        if not self.available:
            raise Exception("store_unavailable")
        if quote_id not in self.quotes:
            raise Exception("quote_not_found")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        return self.quotes[quote_id]


class ScreeningService:
    """External denied-party screening provider."""
    
    def __init__(self):
        self.available = True
        self.risk_index_override = None
    
    def screen(self, shipper_id: str) -> int:
        if not self.available:
            raise Exception("screening_unavailable")
        if self.risk_index_override is not None:
            return self.risk_index_override
        return 25


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        if weight_kg > 1244:
            base += 316.00
        
        if distance_km >= 4912:
            base *= 1.19
        
        return round(base, 2)


class NotificationService:
    """External messaging provider for quotes and refusals."""
    
    def __init__(self):
        self.available = True
        self.deliveries = []
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        if not self.available:
            raise Exception("notification_unavailable")
        self.deliveries.append({
            "type": "quote_document",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
            "price": price,
        })
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if not self.available:
            raise Exception("notification_unavailable")
        self.deliveries.append({
            "type": "refusal_notice",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
        })
        return "sent"


class QuoteAPI:
    """Orchestrates quote requests through validation, screening, pricing, and notification."""
    
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def __init__(self, quote_store: QuoteStore, screening_service: ScreeningService,
                 tariff_engine: TariffEngine, notification_service: NotificationService):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service
    
    def validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        if not shipper_id or shipper_id == "":
            return False
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False
        return True
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        if not self.validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}
        
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception as e:
            if str(e) == "store_unavailable":
                return {"status": "error: store_unavailable"}
            raise
        
        screening_available = True
        risk_index = None
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception as e:
            if str(e) == "screening_unavailable":
                screening_available = False
            else:
                raise
        
        if screening_available:
            if risk_index <= self.ACCEPT_MAX:
                price = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, "quoted", price)
                try:
                    self.notification_service.send_quote_document(shipper_id, quote_id, price)
                except:
                    pass
                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price": price,
                }
            elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
                self.quote_store.update_quote(quote_id, "review_hold")
                return {
                    "status": "review_hold",
                    "quote_id": quote_id,
                }
            elif risk_index >= self.REFUSE_MIN:
                self.quote_store.update_quote(quote_id, "refused_screening")
                try:
                    self.notification_service.send_refusal_notice(shipper_id, quote_id)
                except:
                    pass
                return {
                    "status": "refused_screening",
                    "quote_id": quote_id,
                }
        else:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }


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
        screening_service.risk_index_override = request["screening_result"]
    
    if "notification_available" in request and not request["notification_available"]:
        notification_service.available = False
    
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    result = quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    
    return result