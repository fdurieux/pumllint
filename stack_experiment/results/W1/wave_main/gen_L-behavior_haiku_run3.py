import uuid
from typing import Optional


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen_shipper(self, shipper_id: str) -> int:
        """Return risk index; higher is worse."""
        # Simulated: would call external REST service
        raise NotImplementedError("Subclass or mock must implement")


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """Return price in EUR."""
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
        """Store a draft quote; return quote_id."""
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
    
    def update_status(self, quote_id: str, status: str, price: Optional[float] = None) -> str:
        """Update quote status and optionally price; return quote_id."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        return quote_id


class NotificationService:
    """External messaging provider."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        """Send quote document; return confirmation or raise."""
        # Simulated: would call external REST service
        # Returns a confirmation string
        return "delivered"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Send refusal notice; return confirmation or raise."""
        # Simulated: would call external REST service
        return "delivered"


class QuoteAPI:
    """Orchestrates the quotation flow."""
    
    # DT-S risk band boundaries
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def __init__(self, screening_service: ScreeningService, 
                 tariff_engine: TariffEngine,
                 quote_store: QuoteStore,
                 notification_service: NotificationService):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service
    
    def _validate_request(self, request: dict) -> Optional[str]:
        """Validate per DT-V; return error message or None if valid."""
        # V1: shipper_id present and non-empty
        if not request.get("shipper_id"):
            return "shipper_id missing or empty"
        
        # V2: weight_kg in range [3, 19400]
        weight = request.get("weight_kg")
        if weight is None or not isinstance(weight, (int, float)):
            return "weight_kg missing or not a number"
        if weight < 3 or weight > 19400:
            return f"weight_kg out of range: {weight}"
        
        # V3: distance_km in range [25, 7150]
        distance = request.get("distance_km")
        if distance is None or not isinstance(distance, (int, float)):
            return "distance_km missing or not a number"
        if distance < 25 or distance > 7150:
            return f"distance_km out of range: {distance}"
        
        # V4: declared_value in range [50, 83000]
        value = request.get("declared_value")
        if value is None or not isinstance(value, (int, float)):
            return "declared_value missing or not a number"
        if value < 50 or value > 83000:
            return f"declared_value out of range: {value}"
        
        return None
    
    def handle_request(self, request: dict) -> dict:
        """Run the quotation flow; return response dict."""
        # Step 1: Validate
        validation_error = self._validate_request(request)
        if validation_error:
            return {"status": "rejected: invalid_request"}
        
        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]
        
        # Step 2: Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except Exception:
            return {"status": "error: store_unavailable"}
        
        # Step 3: Request screening
        risk_index = None
        screening_available = True
        try:
            risk_index = self.screening_service.screen_shipper(shipper_id)
        except Exception:
            screening_available = False
        
        # Step 4 & 5 & 6: Apply screening decision, price if applicable, notify if applicable
        if not screening_available:
            # Screening outage: price anyway, hold, don't notify
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_status(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }
        
        # Screening is available; apply decision per DT-S
        if risk_index <= self.ACCEPT_MAX:
            # Accept: price and notify
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_status(quote_id, "quoted", price)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                # Notification failure never changes the outcome (DT-S note 4)
                pass
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review: hold without price or notification
            self.quote_store.update_status(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        else:  # risk_index >= self.REFUSE_MIN
            # Refuse: notify, no price
            self.quote_store.update_status(quote_id, "refused_screening")
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                # Notification failure never changes the outcome
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }


class MockScreeningService(ScreeningService):
    """Mock screening service for testing."""
    
    def __init__(self, result: Optional[int] = None, available: bool = True):
        self.result = result
        self.available = available
    
    def screen_shipper(self, shipper_id: str) -> int:
        if not self.available:
            raise Exception("Screening service unavailable")
        if self.result is not None:
            return self.result
        return 0


class MockNotificationService(NotificationService):
    """Mock notification service for testing."""
    
    def __init__(self, delivery_failure: bool = False):
        self.delivery_failure = delivery_failure
        self.sent_documents = []
        self.sent_refusals = []
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        if self.delivery_failure:
            raise Exception("Notification delivery failed")
        self.sent_documents.append((shipper_id, quote_id, price))
        return "delivered"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if self.delivery_failure:
            raise Exception("Notification delivery failed")
        self.sent_refusals.append((shipper_id, quote_id))
        return "delivered"


def handle(request: dict) -> dict:
    """
    Run one end-to-end quotation flow.
    
    request carries: shipper_id, weight_kg, distance_km, declared_value,
    plus optional keys: screening_result (risk index), screening_status
    (e.g. "unavailable"), notification_status (e.g. "failed").
    
    Returns dict with "status" key and optional "quote_id", "price", "hold".
    """
    screening_result = request.get("screening_result")
    screening_status = request.get("screening_status")
    notification_status = request.get("notification_status")
    
    # Build screening service
    if screening_status == "unavailable":
        screening_service = MockScreeningService(available=False)
    else:
        screening_service = MockScreeningService(
            result=screening_result if screening_result is not None else 0
        )
    
    # Build notification service
    notification_failure = notification_status == "failed"
    notification_service = MockNotificationService(delivery_failure=notification_failure)
    
    # Build tariff engine
    tariff_engine = TariffEngine()
    
    # Build quote store
    quote_store = QuoteStore()
    
    # Build API and handle
    api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)
    return api.handle_request(request)