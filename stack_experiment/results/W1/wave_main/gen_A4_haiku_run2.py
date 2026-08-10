import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationError(Exception):
    message: str


@dataclass
class StorageError(Exception):
    message: str


@dataclass
class ScreeningError(Exception):
    message: str


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str, screening_result: Optional[int] = None, screening_status: Optional[str] = None) -> int:
        if screening_status == "unavailable":
            raise ScreeningError("Screening service unavailable")
        if screening_result is not None:
            return screening_result
        return 0


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules (DT-P)."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        if weight_kg > 1244:
            base += 316.00
        
        if distance_km >= 4912:
            base *= 1.19
        
        return round(base, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""
    
    def __init__(self):
        self.quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, 
                   declared_value: float, store_status: Optional[str] = None) -> str:
        if store_status == "unavailable":
            raise StorageError("Store unavailable")
        
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
    """External messaging provider for quote documents and refusal notices."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float, 
                           notification_status: Optional[str] = None) -> str:
        if notification_status == "failed":
            return "delivery_failed"
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str, 
                           notification_status: Optional[str] = None) -> str:
        if notification_status == "failed":
            return "delivery_failed"
        return "sent"


class QuoteAPI:
    """Orchestrates the quotation flow: validation, screening, pricing, notification."""
    
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def __init__(self, screening_service: ScreeningService, tariff_engine: TariffEngine,
                 quote_store: QuoteStore, notification_service: NotificationService):
        self.screening = screening_service
        self.tariff = tariff_engine
        self.store = quote_store
        self.notification = notification_service
    
    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, 
                         declared_value: float) -> None:
        """Validate request per DT-V."""
        if not shipper_id or shipper_id == "":
            raise ValidationError("shipper_id is required and must be non-empty")
        
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            raise ValidationError(f"weight_kg must be a number between 3 and 19400, got {weight_kg}")
        
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            raise ValidationError(f"distance_km must be a number between 25 and 7150, got {distance_km}")
        
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            raise ValidationError(f"declared_value must be a number between 50 and 83000, got {declared_value}")
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, 
                     declared_value: float, screening_result: Optional[int] = None,
                     screening_status: Optional[str] = None, store_status: Optional[str] = None,
                     notification_status: Optional[str] = None) -> dict:
        """Main quotation flow."""
        
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": "rejected: invalid_request"}
        
        try:
            quote_id = self.store.store_draft(shipper_id, weight_kg, distance_km, 
                                             declared_value, store_status=store_status)
        except StorageError:
            return {"status": "error: store_unavailable"}
        
        screening_failed = False
        risk_index = None
        
        try:
            risk_index = self.screening.screen(shipper_id, screening_result=screening_result,
                                               screening_status=screening_status)
        except ScreeningError:
            screening_failed = True
        
        if screening_failed:
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "held_unscreened", price=price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }
        
        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "quoted", price=price)
            self.notification.send_quote_document(shipper_id, quote_id, price, 
                                                 notification_status=notification_status)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        
        else:
            self.store.update_quote(quote_id, "refused_screening")
            self.notification.send_refusal_notice(shipper_id, quote_id, 
                                                 notification_status=notification_status)
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }


_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_quote_store = QuoteStore()
_notification_service = NotificationService()
_quote_api = QuoteAPI(_screening_service, _tariff_engine, _quote_store, _notification_service)


def handle(request: dict) -> dict:
    """End-to-end quotation flow handler."""
    
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    screening_result = request.get("screening_result")
    screening_status = request.get("screening_status")
    store_status = request.get("store_status")
    notification_status = request.get("notification_status")
    
    return _quote_api.request_quote(
        shipper_id,
        weight_kg,
        distance_km,
        declared_value,
        screening_result=screening_result,
        screening_status=screening_status,
        store_status=store_status,
        notification_status=notification_status
    )