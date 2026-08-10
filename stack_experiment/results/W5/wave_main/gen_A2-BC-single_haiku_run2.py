from enum import Enum
from typing import Optional


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QuoteStatus(Enum):
    CONFIRMED = "confirmed"
    HELD_FOR_REVIEW = "held_for_review"
    REJECTED = "rejected"


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen_shipper(self, shipper_id: str) -> float:
        """Returns a shipper risk index (0.0 to 1.0)."""
        return 0.3


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    def compute_price(self, weight_kg: float, distance_km: float) -> float:
        """Returns the freight price in currency units."""
        base_rate = 0.50
        weight_factor = 0.02
        distance_factor = 0.10
        price = (weight_kg * weight_factor) + (distance_km * distance_factor)
        return max(price, base_rate * 100)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""
    
    def __init__(self):
        self.quotes = {}
        self.counter = 0
    
    def store_quote(self, shipper_id: str, weight_kg: float, distance_km: float,
                    declared_value: float, status: str) -> str:
        """Stores a quote and returns a confirmation identifier."""
        self.counter += 1
        quote_id = f"QUOTE-{self.counter:06d}"
        self.quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": status,
        }
        return quote_id
    
    def update_quote_status(self, quote_id: str, status: str) -> str:
        """Updates the status of a quote and returns the quote ID."""
        if quote_id in self.quotes:
            self.quotes[quote_id]["status"] = status
        return quote_id


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        """Sends quote document to shipper; returns delivery confirmation."""
        return f"NOTIF-{quote_id}-SENT"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str, reason: str) -> str:
        """Sends refusal notice to shipper; returns delivery confirmation."""
        return f"NOTIF-{quote_id}-REFUSED"


class QuoteAPI:
    """Main orchestrator for the quotation flow."""
    
    RISK_THRESHOLD_REVIEW = 0.6
    RISK_THRESHOLD_REJECT = 0.9
    
    def __init__(self, screening_service: ScreeningService, tariff_engine: TariffEngine,
                 quote_store: QuoteStore, notification_service: NotificationService):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service
    
    def validate_request(self, shipper_id: str, weight_kg: float, distance_km: float,
                         declared_value: float) -> None:
        """Validates the quote request; raises ValueError if invalid."""
        if not shipper_id or len(shipper_id.strip()) == 0:
            raise ValueError("shipper_id is required")
        if weight_kg <= 0:
            raise ValueError("weight_kg must be positive")
        if distance_km <= 0:
            raise ValueError("distance_km must be positive")
        if declared_value < 0:
            raise ValueError("declared_value cannot be negative")
    
    def handle_quote_request(self, shipper_id: str, weight_kg: float, distance_km: float,
                             declared_value: float) -> dict:
        """
        Main quotation flow:
        1. Validate request
        2. Store quote with initial status
        3. Screen shipper
        4. Based on risk level: compute price, send notification, return outcome
        """
        try:
            self.validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValueError as e:
            return {"status": f"error: {str(e)}"}
        
        quote_id = self.quote_store.store_quote(shipper_id, weight_kg, distance_km,
                                                 declared_value, "pending")
        
        risk_index = self.screening_service.screen_shipper(shipper_id)
        
        if risk_index >= self.RISK_THRESHOLD_REJECT:
            self.quote_store.update_quote_status(quote_id, "rejected")
            self.notification_service.send_refusal_notice(shipper_id, quote_id,
                                                          "High-risk shipper")
            return {
                "status": "rejected",
                "quote_id": quote_id,
                "reason": "High-risk shipper"
            }
        
        if risk_index >= self.RISK_THRESHOLD_REVIEW:
            self.quote_store.update_quote_status(quote_id, "held_for_review")
            return {
                "status": "held_for_review",
                "quote_id": quote_id,
                "reason": "Held for manual compliance review"
            }
        
        price = self.tariff_engine.compute_price(weight_kg, distance_km)
        self.quote_store.update_quote_status(quote_id, "confirmed")
        self.notification_service.send_quote_document(shipper_id, quote_id, price)
        
        return {
            "status": "confirmed",
            "quote_id": quote_id,
            "price": price
        }


def handle(request: dict) -> dict:
    """
    End-to-end quotation flow.
    
    Request keys:
    - shipper_id: string identifier
    - weight_kg: positive float
    - distance_km: positive float
    - declared_value: non-negative float
    - screening_service_result: (optional) override screening result as float 0.0-1.0
    - tariff_engine_result: (optional) override price computation
    - quote_store_result: (optional) override quote store behavior
    - notification_service_result: (optional) override notification behavior
    """
    
    screening_service = ScreeningService()
    if "screening_service_result" in request:
        risk_value = request["screening_service_result"]
        screening_service.screen_shipper = lambda _: risk_value
    
    tariff_engine = TariffEngine()
    if "tariff_engine_result" in request:
        price_value = request["tariff_engine_result"]
        tariff_engine.compute_price = lambda _, __: price_value
    
    quote_store = QuoteStore()
    if "quote_store_result" in request:
        store_result = request["quote_store_result"]
        if store_result == "error":
            quote_store.store_quote = lambda *args, **kwargs: None
    
    notification_service = NotificationService()
    if "notification_service_result" in request:
        notif_result = request["notification_service_result"]
        if notif_result == "error":
            notification_service.send_quote_document = lambda *args, **kwargs: None
            notification_service.send_refusal_notice = lambda *args, **kwargs: None
    
    api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)
    
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)
    
    return api.handle_quote_request(shipper_id, weight_kg, distance_km, declared_value)