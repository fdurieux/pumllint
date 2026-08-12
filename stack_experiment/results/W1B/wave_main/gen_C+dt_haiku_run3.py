import json
from dataclasses import dataclass
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: str
    price_amount: Optional[float] = None


class ScreeningService:
    def screen(self, shipper_id: str) -> int:
        return 35


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        if weight_kg > 1244:
            base += 316.00
        
        if distance_km >= 4912:
            base *= 1.19
        
        result = Decimal(str(base)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return float(result)


class QuoteStore:
    def __init__(self):
        self.quotes = {}
        self.next_id = 1

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        quote_id = f"Q{self.next_id:06d}"
        self.next_id += 1
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status="draft"
        )
        self.quotes[quote_id] = quote
        return quote_id

    def update_quote(self, quote_id: str, status: str, price_amount: Optional[float] = None) -> Quote:
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote


class QuoteAPI:
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

    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, 
                         declared_value: float) -> tuple[bool, Optional[str]]:
        if not shipper_id or shipper_id == "":
            return False, "shipper_id missing or empty"
        
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False, "weight_kg out of range [3, 19400]"
        
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False, "distance_km out of range [25, 7150]"
        
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False, "declared_value out of range [50, 83000]"
        
        return True, None

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, 
                     declared_value: float) -> dict:
        valid, error = self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if not valid:
            return {"status": "rejected: invalid_request", "reason": error}
        
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception as e:
            return {"status": "error: store_unavailable", "reason": str(e)}
        
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception:
            risk_index = None
        
        if risk_index is None:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True
            }
        
        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            except Exception:
                pass
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount
            }
        
        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        
        if risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }
        
        return {"status": "error: unknown_screening_outcome"}


_quote_store = QuoteStore()
_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_notification_service = NotificationService()
_quote_api = QuoteAPI(_quote_store, _screening_service, _tariff_engine, _notification_service)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)
    
    screening_result = request.get("screening_result")
    if screening_result is not None:
        original_screen = _screening_service.screen
        if isinstance(screening_result, int):
            _screening_service.screen = lambda shipper_id: screening_result
        elif screening_result == "error":
            _screening_service.screen = lambda shipper_id: (_ for _ in ()).throw(Exception("screening unavailable"))
        
        result = _quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
        _screening_service.screen = original_screen
        return result
    
    if request.get("store_result") == "error":
        original_store = _quote_store.store_draft
        _quote_store.store_draft = lambda *args: (_ for _ in ()).throw(Exception("store unavailable"))
        result = _quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
        _quote_store.store_draft = original_store
        return result
    
    return _quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)