import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QuoteRequest:
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float


@dataclass
class ValidationResult:
    valid: bool
    error: Optional[str] = None


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: str
    price: Optional[float] = None


class ScreeningService:
    def screen(self, shipper_id: str, screening_result: Optional[int] = None, screening_status: Optional[str] = None) -> int:
        if screening_status == "unavailable":
            raise Exception("Screening service unavailable")
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
        self.quotes: dict[str, Quote] = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float, store_status: Optional[str] = None) -> str:
        if store_status == "unavailable":
            raise Exception("Store unavailable")
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status="draft"
        )
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> Quote:
        quote = self.quotes[quote_id]
        quote.status = status
        if price is not None:
            quote.price = price
        return quote


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float, notification_status: Optional[str] = None) -> bool:
        if notification_status == "error":
            raise Exception("Notification delivery failed")
        return True
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str, notification_status: Optional[str] = None) -> bool:
        if notification_status == "error":
            raise Exception("Notification delivery failed")
        return True


class QuoteAPI:
    def __init__(self):
        self.screening_service = ScreeningService()
        self.tariff_engine = TariffEngine()
        self.quote_store = QuoteStore()
        self.notification_service = NotificationService()
    
    def validate_request(self, req: QuoteRequest) -> ValidationResult:
        if not req.shipper_id or len(req.shipper_id) == 0:
            return ValidationResult(False, "shipper_id is required and non-empty")
        
        if not isinstance(req.weight_kg, (int, float)) or req.weight_kg < 3 or req.weight_kg > 19400:
            return ValidationResult(False, "weight_kg must be between 3 and 19400")
        
        if not isinstance(req.distance_km, (int, float)) or req.distance_km < 25 or req.distance_km > 7150:
            return ValidationResult(False, "distance_km must be between 25 and 7150")
        
        if not isinstance(req.declared_value, (int, float)) or req.declared_value < 50 or req.declared_value > 83000:
            return ValidationResult(False, "declared_value must be between 50 and 83000")
        
        return ValidationResult(True)
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float,
                     screening_result: Optional[int] = None, screening_status: Optional[str] = None,
                     store_status: Optional[str] = None, notification_status: Optional[str] = None) -> dict:
        
        req = QuoteRequest(shipper_id, weight_kg, distance_km, declared_value)
        
        validation = self.validate_request(req)
        if not validation.valid:
            return {"status": "rejected: invalid_request"}
        
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value, store_status)
        except Exception:
            return {"status": "error: store_unavailable"}
        
        risk_index = None
        screening_failed = False
        try:
            risk_index = self.screening_service.screen(shipper_id, screening_result, screening_status)
        except Exception:
            screening_failed = True
        
        if screening_failed:
            price = self.tariff_engine.price(weight_kg, distance_km)
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
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price, notification_status)
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
                self.notification_service.send_refusal_notice(shipper_id, quote_id, notification_status)
            except Exception:
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }


_api = QuoteAPI()


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)
    
    screening_result = request.get("screening_result")
    screening_status = request.get("screening_status")
    store_status = request.get("store_status")
    notification_status = request.get("notification_status")
    
    return _api.request_quote(
        shipper_id, weight_kg, distance_km, declared_value,
        screening_result, screening_status, store_status, notification_status
    )