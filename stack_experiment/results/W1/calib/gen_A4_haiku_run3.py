import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


class ScreeningService:
    def screen(self, shipper_id: str, screening_result: Optional[int] = None, screening_status: Optional[str] = None) -> int:
        if screening_status == "unavailable":
            raise ScreeningUnavailableError("Screening service unavailable")
        if screening_result is not None:
            return screening_result
        return 0


class ScreeningUnavailableError(Exception):
    pass


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base = Decimal("0.87") * Decimal(str(weight_kg)) + Decimal("1.13") * Decimal(str(distance_km))
        
        if weight_kg > 1244:
            base += Decimal("316.00")
        
        if distance_km >= 4912:
            base *= Decimal("1.19")
        
        result = base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(result)


class QuoteStore:
    def __init__(self):
        self.quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float, store_status: Optional[str] = None) -> str:
        if store_status == "unavailable":
            raise StoreUnavailableError("Quote store unavailable")
        
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
            raise ValueError(f"Quote {quote_id} not found")
        
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        
        return self.quotes[quote_id]


class StoreUnavailableError(Exception):
    pass


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float, notification_status: Optional[str] = None) -> str:
        if notification_status == "failed":
            raise NotificationFailedError("Notification delivery failed")
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str, notification_status: Optional[str] = None) -> str:
        if notification_status == "failed":
            raise NotificationFailedError("Notification delivery failed")
        return "sent"


class NotificationFailedError(Exception):
    pass


class QuoteAPI:
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def __init__(self, screening_service: ScreeningService, tariff_engine: TariffEngine, quote_store: QuoteStore, notification_service: NotificationService):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service
    
    def validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        if not shipper_id or shipper_id == "":
            return False
        if not (3 <= weight_kg <= 19400):
            return False
        if not (25 <= distance_km <= 7150):
            return False
        if not (50 <= declared_value <= 83000):
            return False
        return True
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float, screening_result: Optional[int] = None, screening_status: Optional[str] = None, store_status: Optional[str] = None, notification_status: Optional[str] = None) -> dict:
        if not self.validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}
        
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value, store_status)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}
        
        screening_unavailable = False
        try:
            risk_index = self.screening_service.screen(shipper_id, screening_result, screening_status)
        except ScreeningUnavailableError:
            screening_unavailable = True
            risk_index = None
        
        if screening_unavailable:
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
                self.notification_service.send_quote_document(shipper_id, quote_id, price, notification_status)
            except NotificationFailedError:
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
                self.notification_service.send_refusal_notice(shipper_id, quote_id, notification_status)
            except NotificationFailedError:
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
    
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    screening_result = request.get("screening_result")
    screening_status = request.get("screening_status")
    store_status = request.get("store_status")
    notification_status = request.get("notification_status")
    
    response = quote_api.request_quote(
        shipper_id,
        weight_kg,
        distance_km,
        declared_value,
        screening_result=screening_result,
        screening_status=screening_status,
        store_status=store_status,
        notification_status=notification_status
    )
    
    return response