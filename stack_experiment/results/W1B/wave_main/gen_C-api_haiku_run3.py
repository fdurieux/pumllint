import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


class QuoteStore:
    def __init__(self):
        self.quotes = {}
        self.next_id = 1000
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if not self.quotes:
            self.next_id = 1000
        quote_id = str(self.next_id)
        self.next_id += 1
        self.quotes[quote_id] = {
            "quote_id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: float = None) -> dict:
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote["status"] = status
        if price is not None:
            quote["price"] = price
        return quote


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base = Decimal("0.87") * Decimal(str(weight_kg)) + Decimal("1.13") * Decimal(str(distance_km))
        
        if weight_kg > 1244:
            base += Decimal("316.00")
        
        if distance_km >= 4912:
            base *= Decimal("1.19")
        
        price = float(base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        return price


class ScreeningService:
    def screen(self, shipper_id: str, risk_index: int = None) -> int:
        if risk_index is not None:
            return risk_index
        return 25


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        return "quote_document_sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "refusal_notice_sent"


class QuoteAPI:
    def __init__(self, quote_store: QuoteStore, tariff_engine: TariffEngine,
                 screening_service: ScreeningService, notification_service: NotificationService):
        self.quote_store = quote_store
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service
    
    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> None:
        if not shipper_id or shipper_id == "":
            raise ValidationError("shipper_id is required and must be non-empty")
        
        try:
            wkg = float(weight_kg)
            if not (3 <= wkg <= 19400):
                raise ValidationError(f"weight_kg must be between 3 and 19400, got {wkg}")
        except (TypeError, ValueError):
            raise ValidationError(f"weight_kg must be a number")
        
        try:
            dkm = float(distance_km)
            if not (25 <= dkm <= 7150):
                raise ValidationError(f"distance_km must be between 25 and 7150, got {dkm}")
        except (TypeError, ValueError):
            raise ValidationError(f"distance_km must be a number")
        
        try:
            dval = float(declared_value)
            if not (50 <= dval <= 83000):
                raise ValidationError(f"declared_value must be between 50 and 83000, got {dval}")
        except (TypeError, ValueError):
            raise ValidationError(f"declared_value must be a number")
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float,
                      declared_value: float, screening_result: int = None,
                      store_available: bool = True, screening_available: bool = True) -> dict:
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError:
            return {"status": "rejected: invalid_request"}
        
        if not store_available:
            return {"status": "error: store_unavailable"}
        
        quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        
        if not screening_available:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }
        
        if screening_result is None:
            risk_index = self.screening_service.screen(shipper_id)
        else:
            risk_index = screening_result
        
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
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
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }


def handle(request: dict) -> dict:
    quote_store = QuoteStore()
    tariff_engine = TariffEngine()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    quote_api = QuoteAPI(quote_store, tariff_engine, screening_service, notification_service)
    
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    store_available = request.get("store_available", True)
    screening_available = request.get("screening_available", True)
    screening_result = request.get("screening_result")
    
    response = quote_api.request_quote(
        shipper_id=shipper_id,
        weight_kg=weight_kg,
        distance_km=distance_km,
        declared_value=declared_value,
        screening_result=screening_result,
        store_available=store_available,
        screening_available=screening_available
    )
    
    return response