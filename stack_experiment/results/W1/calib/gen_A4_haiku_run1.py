import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class QuoteRequest:
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float


@dataclass
class ValidationError(Exception):
    pass


@dataclass
class StoreUnavailableError(Exception):
    pass


class ScreeningService:
    def screen(self, shipper_id: str, screening_result: Optional[int] = None, screening_status: Optional[str] = None) -> int:
        if screening_status == "unavailable":
            raise Exception("screening_unavailable")
        if screening_result is not None:
            return screening_result
        return 0


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
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float, store_status: Optional[str] = None) -> str:
        if store_status == "unavailable":
            raise StoreUnavailableError("store_unavailable")
        
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        if quote_id in self.quotes:
            self.quotes[quote_id]["status"] = status
            if price is not None:
                self.quotes[quote_id]["price"] = price
            return self.quotes[quote_id]
        return {}


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float, notification_status: Optional[str] = None) -> str:
        if notification_status == "error":
            raise Exception("notification_error")
        return "quote_document_sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str, notification_status: Optional[str] = None) -> str:
        if notification_status == "error":
            raise Exception("notification_error")
        return "refusal_notice_sent"


class QuoteAPI:
    def __init__(self, screening_service: ScreeningService, tariff_engine: TariffEngine, 
                 quote_store: QuoteStore, notification_service: NotificationService):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service
    
    def validate_request(self, req: QuoteRequest) -> bool:
        if not req.shipper_id or req.shipper_id.strip() == "":
            return False
        if not isinstance(req.weight_kg, (int, float)) or req.weight_kg < 3 or req.weight_kg > 19400:
            return False
        if not isinstance(req.distance_km, (int, float)) or req.distance_km < 25 or req.distance_km > 7150:
            return False
        if not isinstance(req.declared_value, (int, float)) or req.declared_value < 50 or req.declared_value > 83000:
            return False
        return True
    
    def request_quote(self, req: QuoteRequest, screening_result: Optional[int] = None, 
                     screening_status: Optional[str] = None, store_status: Optional[str] = None,
                     notification_status: Optional[str] = None) -> dict:
        if not self.validate_request(req):
            return {"status": "rejected: invalid_request"}
        
        try:
            quote_id = self.quote_store.store_draft(req.shipper_id, req.weight_kg, req.distance_km, 
                                                     req.declared_value, store_status)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}
        
        risk_index = None
        screening_failed = False
        
        try:
            risk_index = self.screening_service.screen(req.shipper_id, screening_result, screening_status)
        except Exception as e:
            if "screening_unavailable" in str(e):
                screening_failed = True
        
        if screening_failed:
            price = self.tariff_engine.price(req.weight_kg, req.distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }
        
        ACCEPT_MAX = 41
        REVIEW_MIN = 42
        REVIEW_MAX = 66
        REFUSE_MIN = 67
        
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(req.weight_kg, req.distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            try:
                self.notification_service.send_quote_document(req.shipper_id, quote_id, price, notification_status)
            except Exception:
                pass
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        elif risk_index >= REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            try:
                self.notification_service.send_refusal_notice(req.shipper_id, quote_id, notification_status)
            except Exception:
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }


def handle(request: dict) -> dict:
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    quote_api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)
    
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)
    
    req = QuoteRequest(shipper_id, weight_kg, distance_km, declared_value)
    
    screening_result = request.get("screening_result")
    screening_status = request.get("screening_status")
    store_status = request.get("store_status")
    notification_status = request.get("notification_status")
    
    response = quote_api.request_quote(req, screening_result, screening_status, store_status, notification_status)
    
    return response