import uuid
import json
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str) -> int:
        """Return the shipper risk index (higher is worse)."""
        raise NotImplementedError("Subclass must implement")


class DefaultScreeningService(ScreeningService):
    """Plausible stub implementation of screening service."""
    
    def screen(self, shipper_id: str) -> int:
        return 35


class TariffEngine:
    """Computes freight price from weight and distance per DT-P."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute price per decision table DT-P."""
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        if weight_kg > 1244:
            base += 316.00
        
        if distance_km >= 4912:
            base *= 1.19
        
        return round(base, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""
    
    def __init__(self):
        self.quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, 
                    distance_km: float, declared_value: float) -> str:
        """Store a draft quote, return quote_id."""
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "quote_id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": QuoteStatus.DRAFT.value,
            "price": None,
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: QuoteStatus, 
                     price: Optional[float] = None) -> dict:
        """Update quote status and optionally price, return updated quote."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        
        self.quotes[quote_id]["status"] = status.value
        if price is not None:
            self.quotes[quote_id]["price"] = price
        
        return self.quotes[quote_id]


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, 
                           price: float) -> str:
        """Send quote document to shipper. Fire-and-forget."""
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Send refusal notice to shipper. Fire-and-forget."""
        return "sent"


class DefaultNotificationService(NotificationService):
    """Plausible stub implementation of notification service."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, 
                           price: float) -> str:
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class QuoteAPI:
    """Quote API: orchestrates screening, pricing, and storage."""
    
    # DT-S boundaries
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def __init__(self, 
                 screening_service: ScreeningService,
                 tariff_engine: TariffEngine,
                 quote_store: QuoteStore,
                 notification_service: NotificationService):
        self.screening = screening_service
        self.tariff = tariff_engine
        self.store = quote_store
        self.notification = notification_service
    
    def validate_request(self, shipper_id: str, weight_kg: float,
                        distance_km: float, declared_value: float) -> bool:
        """Validate request per DT-V."""
        if not shipper_id or len(shipper_id) == 0:
            return False
        
        if not (3 <= weight_kg <= 19400):
            return False
        
        if not (25 <= distance_km <= 7150):
            return False
        
        if not (50 <= declared_value <= 83000):
            return False
        
        return True
    
    def request_quote(self, shipper_id: str, weight_kg: float,
                     distance_km: float, declared_value: float) -> dict:
        """Main quotation flow."""
        
        # Step 1: Validate request (DT-V)
        if not self.validate_request(shipper_id, weight_kg, distance_km, 
                                     declared_value):
            return {
                "status": "rejected: invalid_request"
            }
        
        # Step 2: Store draft
        try:
            quote_id = self.store.store_draft(shipper_id, weight_kg, 
                                              distance_km, declared_value)
        except Exception:
            return {
                "status": "error: store_unavailable"
            }
        
        # Step 3: Request screening
        risk_index = None
        screening_unavailable = False
        try:
            risk_index = self.screening.screen(shipper_id)
        except Exception:
            screening_unavailable = True
        
        # Step 4: Apply screening decision (DT-S)
        if screening_unavailable:
            # DT-S note 5: screening outage does not fail quote
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, 
                                   price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }
        
        # risk_index is available
        if risk_index <= self.ACCEPT_MAX:
            # Accept path: price and notify
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, QuoteStatus.QUOTED, price)
            
            # Fire-and-forget notification
            try:
                self.notification.send_quote_document(shipper_id, quote_id, 
                                                      price)
            except Exception:
                pass
            
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review hold: no pricing, no notification
            self.store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        
        elif risk_index >= self.REFUSE_MIN:
            # Refuse: notify but no pricing
            self.store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            
            # Fire-and-forget notification
            try:
                self.notification.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass
            
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }


def handle(request: dict) -> dict:
    """Run one end-to-end quotation flow."""
    
    # Extract request parameters
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    # Create services (with optional overrides from request)
    screening = _make_screening_service(request)
    tariff = TariffEngine()
    store = QuoteStore()
    notification = _make_notification_service(request)
    
    # Instantiate API and run quotation
    api = QuoteAPI(screening, tariff, store, notification)
    
    try:
        result = api.request_quote(shipper_id, weight_kg, distance_km, 
                                   declared_value)
        return result
    except Exception as e:
        return {
            "status": f"error: {str(e)}"
        }


def _make_screening_service(request: dict) -> ScreeningService:
    """Create screening service, optionally mocked by request."""
    
    class MockScreeningService(ScreeningService):
        def __init__(self, result: int):
            self.result = result
        
        def screen(self, shipper_id: str) -> int:
            return self.result
    
    if "screening_result" in request:
        result = request["screening_result"]
        if isinstance(result, str):
            if result == "error" or result == "unavailable":
                class ErrorScreeningService(ScreeningService):
                    def screen(self, shipper_id: str) -> int:
                        raise Exception("Screening unavailable")
                return ErrorScreeningService()
            else:
                raise ValueError(f"Unknown screening_result: {result}")
        elif isinstance(result, int):
            return MockScreeningService(result)
    
    return DefaultScreeningService()


def _make_notification_service(request: dict) -> NotificationService:
    """Create notification service, optionally mocked by request."""
    
    class MockNotificationService(NotificationService):
        def __init__(self, result: str):
            self.result = result
        
        def send_quote_document(self, shipper_id: str, quote_id: str,
                               price: float) -> str:
            if self.result == "error":
                raise Exception("Notification unavailable")
            return self.result
        
        def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
            if self.result == "error":
                raise Exception("Notification unavailable")
            return self.result
    
    if "notification_result" in request:
        result = request["notification_result"]
        return MockNotificationService(result)
    
    return DefaultNotificationService()