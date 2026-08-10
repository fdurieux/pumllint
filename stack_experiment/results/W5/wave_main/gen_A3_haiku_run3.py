import uuid
import json
from typing import Any
from enum import Enum


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


class ScreeningService:
    def __init__(self):
        pass
    
    def screen(self, shipper_id: str) -> int:
        return 0


class TariffEngine:
    def __init__(self):
        pass
    
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
            "id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": QuoteStatus.DRAFT.value,
            "price": None
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: float = None) -> dict:
        if quote_id not in self.quotes:
            raise StorageError("quote not found")
        
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        
        return self.quotes[quote_id]


class NotificationService:
    def __init__(self):
        pass
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def __init__(self, screening_service: ScreeningService, tariff_engine: TariffEngine, 
                 quote_store: QuoteStore, notification_service: NotificationService):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service
    
    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> None:
        if not shipper_id or shipper_id.strip() == "":
            raise ValidationError("shipper_id is required and non-empty")
        
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            raise ValidationError("weight_kg must be between 3 and 19400")
        
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            raise ValidationError("distance_km must be between 25 and 7150")
        
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            raise ValidationError("declared_value must be between 50 and 83000")
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError:
            return {
                "status": "rejected: invalid_request"
            }
        
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError:
            return {
                "status": "error: store_unavailable"
            }
        
        risk_index = self.screening_service.screen(shipper_id)
        
        if risk_index is None:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED.value, price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }
        
        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED.value, price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD.value)
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        
        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING.value)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }


screening_service = ScreeningService()
tariff_engine = TariffEngine()
quote_store = QuoteStore()
notification_service = NotificationService()
quote_api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    if "screening_service_result" in request:
        screening_result = request["screening_service_result"]
        if screening_result == "error" or screening_result == "unavailable":
            original_screen = screening_service.screen
            screening_service.screen = lambda shipper_id: None
        else:
            risk_index_value = request.get("screening_service_result")
            if isinstance(risk_index_value, int):
                screening_service.screen = lambda shipper_id: risk_index_value
            elif risk_index_value == "error":
                screening_service.screen = lambda shipper_id: None
    
    if "quote_store_result" in request:
        store_result = request["quote_store_result"]
        if store_result == "error" or store_result == "unavailable":
            original_store = quote_store.store_draft
            def failing_store(*args, **kwargs):
                raise StorageError("store unavailable")
            quote_store.store_draft = failing_store
    
    result = quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    
    return result