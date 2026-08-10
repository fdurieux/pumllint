import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


class ScreeningService:
    def __init__(self):
        self.unavailable = False
        self.risk_index = None

    def screen(self, shipper_id: str) -> int:
        if self.unavailable:
            raise ValueError("screening_unavailable")
        return self.risk_index


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
        self.unavailable = False
        self.quotes = {}

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if self.unavailable:
            raise ValueError("store_unavailable")
        
        quote_id = str(uuid.uuid4())
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

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        if quote_id not in self.quotes:
            raise ValueError("quote_not_found")
        
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        
        return self.quotes[quote_id]


class NotificationService:
    def __init__(self):
        self.fail_delivery = False
        self.sent_notifications = []

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        if self.fail_delivery:
            raise ValueError("delivery_failed")
        
        self.sent_notifications.append({
            "type": "quote_document",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
            "price": price,
        })
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if self.fail_delivery:
            raise ValueError("delivery_failed")
        
        self.sent_notifications.append({
            "type": "refusal_notice",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
        })
        return "sent"


class QuoteAPI:
    def __init__(self, screening_service: ScreeningService, tariff_engine: TariffEngine,
                 quote_store: QuoteStore, notification_service: NotificationService):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service

    def validate_request(self, shipper_id: str, weight_kg: float, distance_km: float,
                        declared_value: float) -> bool:
        if not shipper_id or len(str(shipper_id).strip()) == 0:
            return False
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False
        return True

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float,
                     declared_value: float) -> dict:
        if not self.validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}
        
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except ValueError as e:
            if str(e) == "store_unavailable":
                return {"status": "error: store_unavailable"}
            raise
        
        risk_index = None
        screening_failed = False
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ValueError as e:
            if str(e) == "screening_unavailable":
                screening_failed = True
            else:
                raise
        
        if screening_failed:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }
        
        ACCEPT_MAX = 41
        REVIEW_MIN = 42
        REVIEW_MAX = 66
        REFUSE_MIN = 67
        
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except ValueError:
                pass
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        elif risk_index >= REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except ValueError:
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }


_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_quote_store = QuoteStore()
_notification_service = NotificationService()
_quote_api = QuoteAPI(_screening_service, _tariff_engine, _quote_store, _notification_service)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    if "store_unavailable" in request and request["store_unavailable"]:
        _quote_store.unavailable = True
    else:
        _quote_store.unavailable = False
    
    if "screening_unavailable" in request and request["screening_unavailable"]:
        _screening_service.unavailable = True
    else:
        _screening_service.unavailable = False
    
    if "screening_result" in request:
        _screening_service.risk_index = request["screening_result"]
    
    if "notification_failure" in request and request["notification_failure"]:
        _notification_service.fail_delivery = True
    else:
        _notification_service.fail_delivery = False
    
    result = _quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    
    _quote_store.unavailable = False
    _screening_service.unavailable = False
    _notification_service.fail_delivery = False
    
    return result