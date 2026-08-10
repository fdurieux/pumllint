import json
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
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
    price_amount: Optional[float] = None


class QuoteStore:
    def __init__(self):
        self.quotes = {}
        self.quote_counter = 0
        self.available = True

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        if not self.available:
            raise StorageError("store_unavailable")
        
        self.quote_counter += 1
        quote_id = f"Q{self.quote_counter:06d}"
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT,
        )
        self.quotes[quote_id] = quote
        return quote_id

    def update_quote(self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None) -> Quote:
        if not self.available:
            raise StorageError("store_unavailable")
        
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote


class TariffEngine:
    WEIGHT_UNIT_PRICE = 0.85
    DISTANCE_UNIT_PRICE = 0.90
    BASE_FEE = 150.0
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        weight_charge = weight_kg * self.WEIGHT_UNIT_PRICE
        distance_charge = distance_km * self.DISTANCE_UNIT_PRICE
        total = self.BASE_FEE + weight_charge + distance_charge
        return round(total, 2)


class ScreeningService:
    ACCEPT_MAX = 30
    REVIEW_MIN = 31
    REVIEW_MAX = 75
    REFUSE_MIN = 76
    
    def __init__(self):
        self.available = True

    def screen(self, shipper_id: str) -> float:
        if not self.available:
            raise ScreeningError("screening_unavailable")
        return 0.0


class NotificationService:
    def __init__(self):
        self.available = True
        self.sent_notifications = []

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        if not self.available:
            raise Exception("notification_failed")
        self.sent_notifications.append({
            "type": "quote_document",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
            "price": price_amount,
        })
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if not self.available:
            raise Exception("notification_failed")
        self.sent_notifications.append({
            "type": "refusal_notice",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
        })
        return "sent"


class QuoteAPI:
    MIN_WEIGHT_KG = 10
    MAX_WEIGHT_KG = 25000
    MIN_DISTANCE_KM = 50
    MAX_DISTANCE_KM = 5000
    MIN_DECLARED_VALUE = 100
    MAX_DECLARED_VALUE = 1000000

    def __init__(
        self,
        quote_store: QuoteStore,
        tariff_engine: TariffEngine,
        screening_service: ScreeningService,
        notification_service: NotificationService,
    ):
        self.quote_store = quote_store
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate_request(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> None:
        if not shipper_id or not isinstance(shipper_id, str):
            raise ValidationError("invalid_shipper_id")
        if weight_kg < self.MIN_WEIGHT_KG or weight_kg > self.MAX_WEIGHT_KG:
            raise ValidationError("invalid_weight")
        if distance_km < self.MIN_DISTANCE_KM or distance_km > self.MAX_DISTANCE_KM:
            raise ValidationError("invalid_distance")
        if declared_value < self.MIN_DECLARED_VALUE or declared_value > self.MAX_DECLARED_VALUE:
            raise ValidationError("invalid_declared_value")

    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": f"rejected: {str(e)}"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError:
            return {"status": "error: store_unavailable"}

        risk_index = None
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            risk_index = None

        if risk_index is not None:
            if risk_index <= self.screening_service.ACCEPT_MAX:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
                
                try:
                    self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
                except Exception:
                    pass
                
                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price": price_amount,
                }
            
            elif risk_index <= self.screening_service.REVIEW_MAX:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {
                    "status": "review_hold",
                    "quote_id": quote_id,
                }
            
            else:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
                
                try:
                    self.notification_service.send_refusal_notice(shipper_id, quote_id)
                except Exception:
                    pass
                
                return {
                    "status": "refused_screening",
                    "quote_id": quote_id,
                }
        else:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
            
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }


quote_store = QuoteStore()
tariff_engine = TariffEngine()
screening_service = ScreeningService()
notification_service = NotificationService()
quote_api = QuoteAPI(quote_store, tariff_engine, screening_service, notification_service)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)
    
    screening_result = request.get("screening_result")
    if screening_result is not None:
        if screening_result == "error" or screening_result == "unavailable":
            screening_service.available = False
        else:
            screening_service.available = True
            original_screen = screening_service.screen
            screening_service.screen = lambda shipper_id: float(screening_result) if isinstance(screening_result, (int, float)) else 0.0
    
    notification_result = request.get("notification_result")
    if notification_result is not None:
        if notification_result == "error" or notification_result == "failed":
            notification_service.available = False
        else:
            notification_service.available = True
    
    store_result = request.get("store_result")
    if store_result is not None:
        if store_result == "error" or store_result == "unavailable":
            quote_store.available = False
        else:
            quote_store.available = True
    
    result = quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    
    screening_service.available = True
    notification_service.available = True
    quote_store.available = True
    if screening_result is not None and screening_result not in ["error", "unavailable"]:
        screening_service.screen = original_screen
    
    return result