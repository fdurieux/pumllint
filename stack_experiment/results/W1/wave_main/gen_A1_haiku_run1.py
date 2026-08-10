from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional
import uuid


class QuoteStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    HELD_FOR_REVIEW = "held_for_review"
    REFUSED = "refused"
    ERROR = "error"


@dataclass
class Quote:
    id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus = QuoteStatus.PENDING
    risk_index: Optional[float] = None
    price: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    reason: Optional[str] = None


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen_shipper(self, shipper_id: str) -> float:
        """
        Screen a shipper and return a risk index.
        Risk index: 0.0 = no risk, 1.0 = maximum risk.
        """
        return 0.0


class TariffEngine:
    """Computes freight price based on weight and distance."""
    
    def compute_price(self, weight_kg: float, distance_km: float) -> float:
        """
        Compute price for a shipment.
        Base rate: 2.0 per kg, 0.5 per km.
        """
        base_price = (weight_kg * 2.0) + (distance_km * 0.5)
        return max(base_price, 50.0)


class QuoteStore:
    """Stores and retrieves quote records."""
    
    def __init__(self):
        self.quotes: dict[str, Quote] = {}
    
    def create_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """Create and store a new quote. Returns quote ID."""
        quote_id = str(uuid.uuid4())
        quote = Quote(
            id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
        )
        self.quotes[quote_id] = quote
        return quote_id
    
    def update_quote(self, quote_id: str, quote: Quote) -> str:
        """Update an existing quote. Returns quote ID."""
        self.quotes[quote_id] = quote
        return quote_id
    
    def get_quote(self, quote_id: str) -> Optional[Quote]:
        """Retrieve a quote by ID."""
        return self.quotes.get(quote_id)


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def send_approval(self, shipper_id: str, quote_id: str, price: float) -> str:
        """Send quote approval to shipper. Returns confirmation ID."""
        return f"notif_{uuid.uuid4()}"
    
    def send_refusal(self, shipper_id: str, quote_id: str, reason: str) -> str:
        """Send refusal notice to shipper. Returns confirmation ID."""
        return f"notif_{uuid.uuid4()}"
    
    def send_manual_review_notice(self, shipper_id: str, quote_id: str) -> str:
        """Send manual review hold notice to shipper. Returns confirmation ID."""
        return f"notif_{uuid.uuid4()}"


class QuoteAPI:
    """Main orchestrator: receives requests, validates, screens, prices, and returns outcome."""
    
    def __init__(
        self,
        screening_service: ScreeningService,
        tariff_engine: TariffEngine,
        quote_store: QuoteStore,
        notification_service: NotificationService,
    ):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service
    
    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        """
        Main entry point: handle a quote request end-to-end.
        
        Flow:
        1. Validate request
        2. Create and store quote record
        3. Screen shipper
        4. Compute price
        5. Decide outcome (approved, held for review, or refused)
        6. Notify shipper
        7. Return result
        """
        
        # Validate request
        if not shipper_id or weight_kg <= 0 or distance_km <= 0 or declared_value <= 0:
            return {"status": "error: invalid_request"}
        
        try:
            # Create quote record
            quote_id = self.quote_store.create_quote(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
            
            # Screen shipper
            risk_index = self.screening_service.screen_shipper(shipper_id)
            
            # Get quote from store and update with risk index
            quote = self.quote_store.get_quote(quote_id)
            quote.risk_index = risk_index
            
            # Compute price
            price = self.tariff_engine.compute_price(weight_kg, distance_km)
            quote.price = price
            
            # Decide outcome based on risk index
            if risk_index > 0.8:
                # High risk: refuse
                quote.status = QuoteStatus.REFUSED
                quote.reason = "shipper_high_risk"
                self.quote_store.update_quote(quote_id, quote)
                self.notification_service.send_refusal(
                    shipper_id, quote_id, "shipper_high_risk"
                )
                return {"status": "rejected", "quote_id": quote_id, "reason": "high_risk"}
            
            elif risk_index > 0.5:
                # Medium risk: hold for manual review
                quote.status = QuoteStatus.HELD_FOR_REVIEW
                quote.reason = "manual_review_required"
                self.quote_store.update_quote(quote_id, quote)
                self.notification_service.send_manual_review_notice(shipper_id, quote_id)
                return {
                    "status": "held_for_review",
                    "quote_id": quote_id,
                    "reason": "manual_review_required",
                }
            
            else:
                # Low risk: approve
                quote.status = QuoteStatus.APPROVED
                self.quote_store.update_quote(quote_id, quote)
                self.notification_service.send_approval(shipper_id, quote_id, price)
                return {
                    "status": "confirmed",
                    "quote_id": quote_id,
                    "price": price,
                }
        
        except Exception as e:
            return {"status": f"error: {str(e)}"}


def handle(request: dict) -> dict:
    """
    End-to-end handler for quote requests.
    
    Expected request keys:
    - shipper_id: str
    - weight_kg: float
    - distance_km: float
    - declared_value: float
    
    Optional overrides (for testing):
    - screening_service_result: float (risk index, 0.0-1.0)
    - tariff_engine_result: float (price)
    - quote_store_status: str ("stored", "error", etc.)
    - notification_service_status: str ("sent", "error", etc.)
    
    Returns dict with "status" key and optional "quote_id", "price", "reason".
    """
    
    # Initialize services
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    
    # Create API instance
    api = QuoteAPI(
        screening_service=screening_service,
        tariff_engine=tariff_engine,
        quote_store=quote_store,
        notification_service=notification_service,
    )
    
    # Override service behaviors if test values provided
    if "screening_service_result" in request:
        screening_service.screen_shipper = (
            lambda shipper_id: request["screening_service_result"]
        )
    
    if "tariff_engine_result" in request:
        tariff_engine.compute_price = (
            lambda weight_kg, distance_km: request["tariff_engine_result"]
        )
    
    if "quote_store_status" in request and request["quote_store_status"] == "error":
        quote_store.create_quote = (
            lambda *args, **kwargs: (_ for _ in ()).throw(
                Exception("quote_store error")
            )
        )
    
    # Process the quote request
    result = api.request_quote(
        shipper_id=request.get("shipper_id", ""),
        weight_kg=request.get("weight_kg", 0),
        distance_km=request.get("distance_km", 0),
        declared_value=request.get("declared_value", 0),
    )
    
    return result