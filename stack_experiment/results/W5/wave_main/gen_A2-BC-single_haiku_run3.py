from dataclasses import dataclass, asdict
from typing import Optional
from enum import Enum


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class QuoteRequest:
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    price: float
    risk_index: float
    status: str


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen_shipper(self, shipper_id: str) -> float:
        """Returns a risk index (0.0 to 1.0) for the shipper."""
        return 0.3


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    def compute_price(self, weight_kg: float, distance_km: float) -> float:
        """Returns the price in currency units."""
        base_rate = 2.5
        weight_surcharge = weight_kg * 0.01
        distance_rate = distance_km * 0.15
        return base_rate + weight_surcharge + distance_rate


class QuoteStore:
    """Stores quote requests and their lifecycle status."""
    
    def __init__(self):
        self._quotes = {}
        self._counter = 0
    
    def save_quote(self, request: QuoteRequest, price: float, risk_index: float, status: str) -> str:
        """Saves a quote and returns its ID."""
        self._counter += 1
        quote_id = f"Q{self._counter:06d}"
        quote = Quote(
            quote_id=quote_id,
            shipper_id=request.shipper_id,
            weight_kg=request.weight_kg,
            distance_km=request.distance_km,
            declared_value=request.declared_value,
            price=price,
            risk_index=risk_index,
            status=status
        )
        self._quotes[quote_id] = quote
        return quote_id
    
    def update_quote_status(self, quote_id: str, new_status: str) -> str:
        """Updates the status of a stored quote and returns the quote ID."""
        if quote_id in self._quotes:
            self._quotes[quote_id].status = new_status
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""
    
    def send_quote(self, quote_id: str, shipper_id: str, price: float) -> str:
        """Sends a quote document. Returns confirmation."""
        return f"quote_sent_{quote_id}"
    
    def send_refusal(self, quote_id: str, shipper_id: str, reason: str) -> str:
        """Sends a refusal notice. Returns confirmation."""
        return f"refusal_sent_{quote_id}"
    
    def send_hold_notice(self, quote_id: str, shipper_id: str) -> str:
        """Sends a notice that the quote is held for manual review. Returns confirmation."""
        return f"hold_sent_{quote_id}"


class QuoteAPI:
    """Receives quote requests, validates them, orchestrates screening and pricing."""
    
    def __init__(
        self,
        screening_service: ScreeningService,
        tariff_engine: TariffEngine,
        quote_store: QuoteStore,
        notification_service: NotificationService
    ):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service
        self.risk_threshold_hold = 0.5
        self.risk_threshold_reject = 0.8
    
    def validate_request(self, request_dict: dict) -> QuoteRequest:
        """Validates a quote request. Raises ValueError if invalid."""
        required_fields = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for field in required_fields:
            if field not in request_dict or request_dict[field] is None:
                raise ValueError(f"Missing required field: {field}")
        
        weight_kg = request_dict["weight_kg"]
        distance_km = request_dict["distance_km"]
        declared_value = request_dict["declared_value"]
        
        if not isinstance(weight_kg, (int, float)) or weight_kg <= 0:
            raise ValueError("weight_kg must be a positive number")
        if not isinstance(distance_km, (int, float)) or distance_km <= 0:
            raise ValueError("distance_km must be a positive number")
        if not isinstance(declared_value, (int, float)) or declared_value < 0:
            raise ValueError("declared_value must be a non-negative number")
        
        return QuoteRequest(
            shipper_id=request_dict["shipper_id"],
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value
        )
    
    def handle_quote_request(self, request_dict: dict) -> dict:
        """Main quotation flow."""
        try:
            request = self.validate_request(request_dict)
        except ValueError as e:
            return {"status": f"error: {str(e)}"}
        
        price = self.tariff_engine.compute_price(request.weight_kg, request.distance_km)
        
        risk_index = self.screening_service.screen_shipper(request.shipper_id)
        
        if risk_index >= self.risk_threshold_reject:
            quote_id = self.quote_store.save_quote(request, price, risk_index, "refused")
            self.notification_service.send_refusal(quote_id, request.shipper_id, "High-risk shipper")
            return {"status": "rejected", "quote_id": quote_id}
        
        if risk_index >= self.risk_threshold_hold:
            quote_id = self.quote_store.save_quote(request, price, risk_index, "held_for_review")
            self.notification_service.send_hold_notice(quote_id, request.shipper_id)
            return {"status": "held_for_review", "quote_id": quote_id}
        
        quote_id = self.quote_store.save_quote(request, price, risk_index, "issued")
        self.notification_service.send_quote(quote_id, request.shipper_id, price)
        return {"status": "confirmed", "quote_id": quote_id, "price": price}


def handle(request: dict) -> dict:
    """Module-level function that runs one end-to-end flow."""
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    
    api = QuoteAPI(
        screening_service=screening_service,
        tariff_engine=tariff_engine,
        quote_store=quote_store,
        notification_service=notification_service
    )
    
    if "screening_service_result" in request:
        screening_service.screen_shipper = lambda shipper_id: request["screening_service_result"]
    
    if "tariff_engine_result" in request:
        tariff_engine.compute_price = lambda weight_kg, distance_km: request["tariff_engine_result"]
    
    if "notification_service_status" in request:
        status = request["notification_service_status"]
        if status == "error":
            notification_service.send_quote = lambda quote_id, shipper_id, price: (_ for _ in ()).throw(Exception("Notification service error"))
            notification_service.send_refusal = lambda quote_id, shipper_id, reason: (_ for _ in ()).throw(Exception("Notification service error"))
            notification_service.send_hold_notice = lambda quote_id, shipper_id: (_ for _ in ()).throw(Exception("Notification service error"))
    
    try:
        result = api.handle_quote_request(request)
        return result
    except Exception as e:
        return {"status": f"error: {str(e)}"}