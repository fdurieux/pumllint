import uuid
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class QuoteRecord:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: str
    price: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str) -> int:
        """Return shipper risk index; higher is worse."""
        return 0


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules (DT-P)."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        DT-P pricing rules:
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00 (flat)
        P3: if distance_km >= 4912, multiply by 1.19 (applied after P2)
        P4: round to 2 decimal places
        """
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        if weight_kg > 1244:
            base += 316.00
        
        if distance_km >= 4912:
            base *= 1.19
        
        return round(base, 2)


class QuoteStore:
    """PostgreSQL quote storage."""
    
    def __init__(self):
        self.quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, 
                    declared_value: float) -> str:
        """Store draft quote; return quote_id."""
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = QuoteRecord(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status="draft"
        )
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> QuoteRecord:
        """Update quote status and price; return updated record."""
        record = self.quotes[quote_id]
        record.status = status
        if price is not None:
            record.price = price
        return record


class NotificationService:
    """External messaging provider."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        """Send quote document; return confirmation."""
        return "quote_document_sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Send refusal notice; return confirmation."""
        return "refusal_notice_sent"


class QuoteAPI:
    """Main orchestrator: validates, screens, prices, stores, notifies."""
    
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
    
    def validate_request(self, shipper_id: str, weight_kg: float, 
                        distance_km: float, declared_value: float) -> Optional[str]:
        """
        DT-V validation. Return error message if invalid; None if valid.
        V1: shipper_id present and non-empty
        V2: weight_kg in [3, 19400]
        V3: distance_km in [25, 7150]
        V4: declared_value in [50, 83000]
        """
        if not shipper_id or shipper_id == "":
            return "rejected: invalid_request"
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return "rejected: invalid_request"
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return "rejected: invalid_request"
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return "rejected: invalid_request"
        return None
    
    def request_quote(self, shipper_id: str, weight_kg: float, 
                     distance_km: float, declared_value: float) -> dict:
        """
        Main quotation flow per the sequence diagram and decision tables.
        Returns response dict with status, quote_id (if stored), price (if priced), hold (if applicable).
        """
        
        # Step 1: Validate request (DT-V)
        validation_error = self.validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if validation_error:
            return {"status": validation_error}
        
        # Step 2: Store draft quote
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception:
            return {"status": "error: store_unavailable"}
        
        # Step 3: Request screening (with fallback on unavailability)
        risk_index = None
        screening_failed = False
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception:
            screening_failed = True
        
        # Step 4 & 5: Apply screening decision (DT-S) and price if applicable
        response = {"status": None, "quote_id": quote_id}
        
        if screening_failed:
            # Screening unavailable: price anyway, mark as held_unscreened, don't notify
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            response["status"] = "held_unscreened"
            response["price"] = price
            response["hold"] = True
            return response
        
        # Apply DT-S banding
        if risk_index <= self.ACCEPT_MAX:
            # Accept: price, update to quoted, notify with quote document
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            response["status"] = "quoted"
            response["price"] = price
            # Fire-and-forget notification
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                pass
            return response
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review: no price, no notification, just hold
            self.quote_store.update_quote(quote_id, "review_hold")
            response["status"] = "review_hold"
            return response
        
        elif risk_index >= self.REFUSE_MIN:
            # Refuse: no price, update to refused_screening, notify with refusal notice
            self.quote_store.update_quote(quote_id, "refused_screening")
            response["status"] = "refused_screening"
            # Fire-and-forget notification
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass
            return response


def handle(request: dict) -> dict:
    """
    End-to-end flow handler. 
    
    Request keys:
      - shipper_id, weight_kg, distance_km, declared_value: quote request fields
      - screening_result: (optional) risk index to inject into screening service
      - notification_status: (optional) success or error to inject into notification service
      - store_unavailable: (optional) flag to fail storage
    
    Returns dict with 'status' key naming the outcome, plus quote_id/price/hold as applicable.
    """
    
    # Instantiate collaborators with optional test-time injection
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    
    # Inject test outcomes if provided
    if "screening_result" in request:
        screening_service.screen = lambda _: request["screening_result"]
    
    if "store_unavailable" in request and request["store_unavailable"]:
        original_store = quote_store.store_draft
        def failing_store(*args, **kwargs):
            raise Exception("store unavailable")
        quote_store.store_draft = failing_store
    
    if "notification_status" in request and request["notification_status"] == "error":
        notification_service.send_quote_document = lambda *args, **kwargs: (_ for _ in ()).throw(Exception("notification failed"))
        notification_service.send_refusal_notice = lambda *args, **kwargs: (_ for _ in ()).throw(Exception("notification failed"))
    
    api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)
    
    # Extract required fields from request
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)