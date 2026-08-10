import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


class ScreeningService:
    def __init__(self):
        self.unavailable = False
        self.risk_index = 0

    def screen_shipper(self, shipper_id: str) -> int:
        if self.unavailable:
            raise Exception("screening_unavailable")
        return self.risk_index


class TariffEngine:
    def compute_price(self, weight_kg: float, distance_km: float) -> float:
        base = Decimal(str(0.87 * weight_kg + 1.13 * distance_km))
        
        if weight_kg > 1244:
            base += Decimal("316.00")
        
        if distance_km >= 4912:
            base *= Decimal("1.19")
        
        price = float(base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        return price


class QuoteStore:
    def __init__(self):
        self.unavailable = False
        self.quotes = {}

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if self.unavailable:
            raise Exception("store_unavailable")
        
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft"
        }
        return quote_id

    def update_status(self, quote_id: str, status: str, price: Optional[float] = None) -> str:
        if quote_id in self.quotes:
            self.quotes[quote_id]["status"] = status
            if price is not None:
                self.quotes[quote_id]["price"] = price
        return quote_id


class NotificationService:
    def __init__(self):
        self.delivery_fails = False

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        if self.delivery_fails:
            return "delivery_failed"
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if self.delivery_fails:
            return "delivery_failed"
        return "sent"


class QuoteAPI:
    def __init__(self, screening_service: ScreeningService, tariff_engine: TariffEngine,
                 quote_store: QuoteStore, notification_service: NotificationService):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service

    def validate_request(self, request: dict) -> Optional[str]:
        shipper_id = request.get("shipper_id")
        weight_kg = request.get("weight_kg")
        distance_km = request.get("distance_km")
        declared_value = request.get("declared_value")
        
        if not shipper_id or shipper_id == "":
            return "invalid_request"
        
        if weight_kg is None or weight_kg < 3 or weight_kg > 19400:
            return "invalid_request"
        
        if distance_km is None or distance_km < 25 or distance_km > 7150:
            return "invalid_request"
        
        if declared_value is None or declared_value < 50 or declared_value > 83000:
            return "invalid_request"
        
        return None

    def request_quote(self, request: dict) -> dict:
        validation_error = self.validate_request(request)
        if validation_error:
            return {"status": f"rejected: {validation_error}"}
        
        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]
        
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception as e:
            if str(e) == "store_unavailable":
                return {"status": "error: store_unavailable"}
            raise
        
        risk_index = None
        screening_unavailable = False
        try:
            risk_index = self.screening_service.screen_shipper(shipper_id)
        except Exception as e:
            if str(e) == "screening_unavailable":
                screening_unavailable = True
            else:
                raise
        
        if screening_unavailable:
            price = self.tariff_engine.compute_price(weight_kg, distance_km)
            self.quote_store.update_status(quote_id, "held_unscreened", price)
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
            price = self.tariff_engine.compute_price(weight_kg, distance_km)
            self.quote_store.update_status(quote_id, "quoted", price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_status(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        else:
            self.quote_store.update_status(quote_id, "refused_screening")
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
    screening_service.unavailable = False
    screening_service.risk_index = 0
    quote_store.unavailable = False
    notification_service.delivery_fails = False
    
    if "screening_result" in request:
        result = request["screening_result"]
        if result == "unavailable":
            screening_service.unavailable = True
        else:
            try:
                screening_service.risk_index = int(result)
            except (ValueError, TypeError):
                screening_service.risk_index = 0
    
    if "screening_status" in request:
        status = request["screening_status"]
        if status == "unavailable":
            screening_service.unavailable = True
    
    if "store_result" in request:
        result = request["store_result"]
        if result == "unavailable":
            quote_store.unavailable = True
    
    if "store_status" in request:
        status = request["store_status"]
        if status == "unavailable":
            quote_store.unavailable = True
    
    if "notification_result" in request:
        result = request["notification_result"]
        if result == "error":
            notification_service.delivery_fails = True
    
    if "notification_status" in request:
        status = request["notification_status"]
        if status == "error":
            notification_service.delivery_fails = True
    
    quote_request = {
        "shipper_id": request.get("shipper_id", ""),
        "weight_kg": request.get("weight_kg"),
        "distance_km": request.get("distance_km"),
        "declared_value": request.get("declared_value")
    }
    
    return quote_api.request_quote(quote_request)