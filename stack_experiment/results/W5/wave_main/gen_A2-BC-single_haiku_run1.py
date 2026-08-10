from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime


class QuoteStatus(Enum):
    ISSUED = "issued"
    HELD_FOR_REVIEW = "held_for_review"
    REFUSED = "refused"


class ScreeningProvider:
    """External denied-party screening service."""
    
    def screen_shipper(self, shipper_id: str) -> float:
        """
        Screen a shipper and return risk index (0.0 to 1.0).
        0.0 = no risk, 1.0 = maximum risk.
        """
        return 0.3


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    PRICE_PER_KG_KM = 0.05
    BASE_CHARGE = 50.0
    
    def compute_price(self, weight_kg: float, distance_km: float) -> float:
        """Compute price based on weight and distance."""
        if weight_kg <= 0 or distance_km <= 0:
            raise ValueError("Weight and distance must be positive")
        return self.BASE_CHARGE + (weight_kg * distance_km * self.PRICE_PER_KG_KM)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""
    
    def __init__(self):
        self._quotes = {}
        self._next_id = 1000
    
    def store_quote(self, shipper_id: str, weight_kg: float, distance_km: float, 
                   declared_value: float, status: QuoteStatus, price: Optional[float] = None,
                   risk_index: Optional[float] = None) -> str:
        """Store a quote request and return confirmation (quote ID)."""
        quote_id = f"Q{self._next_id}"
        self._next_id += 1
        
        self._quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": status,
            "price": price,
            "risk_index": risk_index,
            "created_at": datetime.utcnow().isoformat()
        }
        
        return quote_id
    
    def get_quote(self, quote_id: str) -> Optional[dict]:
        """Retrieve a stored quote."""
        return self._quotes.get(quote_id)


class NotificationProvider:
    """External notification service for sending quote documents and refusal notices."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        """Send quote document to shipper. Returns delivery confirmation."""
        return f"quote_delivered_{quote_id}"
    
    def send_refusal_notice(self, shipper_id: str, reason: str) -> str:
        """Send refusal notice to shipper. Returns delivery confirmation."""
        return f"refusal_delivered"


@dataclass
class QuoteRequest:
    """Represents a quote request from a shipper."""
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float


class QuoteAPI:
    """
    Main quotation orchestrator. Validates requests, screens shippers,
    computes pricing, stores quotes, and sends notifications.
    """
    
    RISK_THRESHOLD_REVIEW = 0.5
    RISK_THRESHOLD_REFUSE = 0.8
    
    def __init__(self, 
                 screening_provider: Optional[ScreeningProvider] = None,
                 tariff_engine: Optional[TariffEngine] = None,
                 quote_store: Optional[QuoteStore] = None,
                 notification_provider: Optional[NotificationProvider] = None):
        self.screening_provider = screening_provider or ScreeningProvider()
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.notification_provider = notification_provider or NotificationProvider()
    
    def _validate_request(self, request: QuoteRequest) -> None:
        """Validate quote request. Raises ValueError on invalid input."""
        if not request.shipper_id or not isinstance(request.shipper_id, str):
            raise ValueError("Invalid shipper ID")
        if request.weight_kg <= 0:
            raise ValueError("Weight must be positive")
        if request.distance_km <= 0:
            raise ValueError("Distance must be positive")
        if request.declared_value < 0:
            raise ValueError("Declared value cannot be negative")
    
    def request_quote(self, request: QuoteRequest) -> dict:
        """
        Main quotation flow:
        1. Validate request
        2. Store initial quote record
        3. Screen shipper
        4. Determine outcome based on risk:
           - High risk (>= 0.8): refuse
           - Medium risk (0.5-0.8): hold for review
           - Low risk (< 0.5): compute price and issue
        5. Send notification
        6. Return outcome
        """
        try:
            self._validate_request(request)
        except ValueError as e:
            return {"status": f"error: {str(e)}"}
        
        risk_index = self.screening_provider.screen_shipper(request.shipper_id)
        
        if risk_index >= self.RISK_THRESHOLD_REFUSE:
            quote_id = self.quote_store.store_quote(
                request.shipper_id,
                request.weight_kg,
                request.distance_km,
                request.declared_value,
                QuoteStatus.REFUSED,
                risk_index=risk_index
            )
            self.notification_provider.send_refusal_notice(
                request.shipper_id,
                "High risk shipper"
            )
            return {
                "status": "rejected",
                "reason": "High risk shipper",
                "quote_id": quote_id,
                "risk_index": risk_index
            }
        
        if risk_index >= self.RISK_THRESHOLD_REVIEW:
            quote_id = self.quote_store.store_quote(
                request.shipper_id,
                request.weight_kg,
                request.distance_km,
                request.declared_value,
                QuoteStatus.HELD_FOR_REVIEW,
                risk_index=risk_index
            )
            return {
                "status": "held_for_review",
                "quote_id": quote_id,
                "reason": "Medium risk shipper - compliance review required",
                "risk_index": risk_index
            }
        
        try:
            price = self.tariff_engine.compute_price(request.weight_kg, request.distance_km)
        except ValueError as e:
            return {"status": f"error: {str(e)}"}
        
        quote_id = self.quote_store.store_quote(
            request.shipper_id,
            request.weight_kg,
            request.distance_km,
            request.declared_value,
            QuoteStatus.ISSUED,
            price=price,
            risk_index=risk_index
        )
        
        self.notification_provider.send_quote_document(
            request.shipper_id,
            quote_id,
            price
        )
        
        return {
            "status": "confirmed",
            "quote_id": quote_id,
            "price": price,
            "risk_index": risk_index
        }


def handle(request: dict) -> dict:
    """
    End-to-end quote request handler.
    
    Input dict may contain:
    - shipper_id: str
    - weight_kg: float
    - distance_km: float
    - declared_value: float
    - screening_result: str or float (overrides provider)
    - pricing_result: float (overrides engine)
    
    Returns dict with "status" key and outcome details.
    """
    screening_provider = ScreeningProvider()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_provider = NotificationProvider()
    
    class MockScreeningProvider(ScreeningProvider):
        def screen_shipper(self, shipper_id: str) -> float:
            if "screening_result" in request:
                result = request["screening_result"]
                if isinstance(result, (int, float)):
                    return float(result)
                result_map = {
                    "low": 0.2,
                    "medium": 0.6,
                    "high": 0.9,
                    "approved": 0.1,
                    "declined": 0.95
                }
                return result_map.get(result.lower(), 0.3)
            return 0.3
    
    class MockTariffEngine(TariffEngine):
        def compute_price(self, weight_kg: float, distance_km: float) -> float:
            if "pricing_result" in request:
                return float(request["pricing_result"])
            return super().compute_price(weight_kg, distance_km)
    
    api = QuoteAPI(
        screening_provider=MockScreeningProvider(),
        tariff_engine=MockTariffEngine(),
        quote_store=quote_store,
        notification_provider=notification_provider
    )
    
    quote_request = QuoteRequest(
        shipper_id=request.get("shipper_id", "SHIPPER001"),
        weight_kg=request.get("weight_kg", 100.0),
        distance_km=request.get("distance_km", 500.0),
        declared_value=request.get("declared_value", 5000.0)
    )
    
    return api.request_quote(quote_request)