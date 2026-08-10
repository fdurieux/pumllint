import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class QuoteRequest:
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningService:
    def screen(self, shipper_id: str) -> int:
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
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        return self.quotes[quote_id]


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def __init__(self, tariff_engine: TariffEngine, quote_store: QuoteStore, 
                 screening_service: ScreeningService, notification_service: NotificationService):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service
    
    def validate_request(self, request: QuoteRequest) -> None:
        if not request.shipper_id or len(request.shipper_id) == 0:
            raise ValidationError("shipper_id is required and non-empty")
        
        if not (3 <= request.weight_kg <= 19400):
            raise ValidationError(f"weight_kg must be between 3 and 19400, got {request.weight_kg}")
        
        if not (25 <= request.distance_km <= 7150):
            raise ValidationError(f"distance_km must be between 25 and 7150, got {request.distance_km}")
        
        if not (50 <= request.declared_value <= 83000):
            raise ValidationError(f"declared_value must be between 50 and 83000, got {request.declared_value}")
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        request = QuoteRequest(shipper_id, weight_kg, distance_km, declared_value)
        
        try:
            self.validate_request(request)
        except ValidationError:
            return {"status": "rejected: invalid_request"}
        
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError:
            return {"status": "error: store_unavailable"}
        
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_available = True
        except Exception:
            screening_available = False
            risk_index = None
        
        if not screening_available:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }
        
        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                pass
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        
        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }
        
        return {"status": "error: unknown"}


_tariff_engine = TariffEngine()
_quote_store = QuoteStore()
_screening_service = ScreeningService()
_notification_service = NotificationService()
_quote_api = QuoteAPI(_tariff_engine, _quote_store, _screening_service, _notification_service)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)
    
    screening_result = request.get("screening_result")
    screening_status = request.get("screening_status")
    notification_status = request.get("notification_status")
    store_status = request.get("store_status")
    
    if store_status == "error":
        _quote_store.store_draft = lambda *args, **kwargs: (_ for _ in ()).throw(StorageError("unavailable"))
    
    if screening_status == "unavailable" or screening_status == "error":
        original_screen = _screening_service.screen
        _screening_service.screen = lambda *args, **kwargs: (_ for _ in ()).throw(Exception("screening unavailable"))
    elif screening_result is not None:
        _screening_service.screen = lambda *args, **kwargs: screening_result
    else:
        _screening_service.screen = lambda *args, **kwargs: 0
    
    if notification_status == "error" or notification_status == "failed":
        original_send_doc = _notification_service.send_quote_document
        original_send_ref = _notification_service.send_refusal_notice
        _notification_service.send_quote_document = lambda *args, **kwargs: (_ for _ in ()).throw(Exception("notification failed"))
        _notification_service.send_refusal_notice = lambda *args, **kwargs: (_ for _ in ()).throw(Exception("notification failed"))
    
    response = _quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    
    _quote_store.store_draft = QuoteStore.store_draft.__get__(_quote_store, QuoteStore)
    _screening_service.screen = ScreeningService.screen.__get__(_screening_service, ScreeningService)
    _notification_service.send_quote_document = NotificationService.send_quote_document.__get__(_notification_service, NotificationService)
    _notification_service.send_refusal_notice = NotificationService.send_refusal_notice.__get__(_notification_service, NotificationService)
    
    return response