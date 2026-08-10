import json
import uuid
from typing import Any


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class ScreeningService:
    def __init__(self):
        self.available = True
        self.risk_index = None

    def screen(self, shipper_id: str) -> int:
        if not self.available:
            raise Exception("screening_unavailable")
        return self.risk_index


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        if weight_kg > 1244:
            base += 316.00
        
        if distance_km >= 4912:
            base *= 1.19
        
        price = round(base, 2)
        return price


class QuoteStore:
    def __init__(self):
        self.available = True
        self.quotes = {}

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if not self.available:
            raise Exception("store_unavailable")
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id: str, status: str, price: float = None) -> dict:
        if not self.available:
            raise Exception("store_unavailable")
        if quote_id not in self.quotes:
            raise Exception("quote_not_found")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        return self.quotes[quote_id]


class NotificationService:
    def __init__(self):
        self.available = True
        self.sent_documents = []
        self.sent_refusals = []

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        if not self.available:
            raise Exception("notification_unavailable")
        self.sent_documents.append({"shipper_id": shipper_id, "quote_id": quote_id, "price": price})
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if not self.available:
            raise Exception("notification_unavailable")
        self.sent_refusals.append({"shipper_id": shipper_id, "quote_id": quote_id})
        return "sent"


class QuoteAPI:
    def __init__(self):
        self.screening_service = ScreeningService()
        self.tariff_engine = TariffEngine()
        self.quote_store = QuoteStore()
        self.notification_service = NotificationService()

    def validate_request(self, request: dict) -> tuple[bool, str]:
        if "shipper_id" not in request or not request["shipper_id"]:
            return False, "shipper_id must be present and non-empty"
        
        if "weight_kg" not in request:
            return False, "weight_kg is required"
        weight_kg = request["weight_kg"]
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False, "weight_kg must be between 3 and 19400"
        
        if "distance_km" not in request:
            return False, "distance_km is required"
        distance_km = request["distance_km"]
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False, "distance_km must be between 25 and 7150"
        
        if "declared_value" not in request:
            return False, "declared_value is required"
        declared_value = request["declared_value"]
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False, "declared_value must be between 50 and 83000"
        
        return True, ""

    def request_quote(self, request: dict) -> dict:
        valid, error_msg = self.validate_request(request)
        if not valid:
            return {"status": "rejected: invalid_request"}
        
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
        
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception as e:
            if str(e) == "screening_unavailable":
                price = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, "held_unscreened", price)
                return {
                    "status": "held_unscreened",
                    "quote_id": quote_id,
                    "price": price,
                    "hold": True,
                }
            raise
        
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
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
            except Exception:
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }


_api = QuoteAPI()


def handle(request: dict) -> dict:
    valid, _ = _api.validate_request(request)
    if not valid:
        return {"status": "rejected: invalid_request"}
    
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)
    
    _api.screening_service.available = request.get("screening_service_available", True)
    _api.quote_store.available = request.get("quote_store_available", True)
    _api.notification_service.available = request.get("notification_service_available", True)
    
    if "screening_service_result" in request:
        risk_index_val = request["screening_service_result"]
        if isinstance(risk_index_val, str):
            if risk_index_val == "unavailable":
                _api.screening_service.available = False
            else:
                try:
                    _api.screening_service.risk_index = int(risk_index_val)
                except ValueError:
                    _api.screening_service.risk_index = 0
        else:
            _api.screening_service.risk_index = risk_index_val
    else:
        _api.screening_service.risk_index = 0
    
    if "quote_store_result" in request:
        if request["quote_store_result"] == "unavailable":
            _api.quote_store.available = False
    
    if "notification_service_result" in request:
        if request["notification_service_result"] == "unavailable":
            _api.notification_service.available = False
    
    response = _api.request_quote(request)
    return response