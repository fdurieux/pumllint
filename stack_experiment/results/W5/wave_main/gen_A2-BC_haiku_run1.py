from enum import Enum
from dataclasses import dataclass
from typing import Optional


class QuoteStatus(Enum):
    ISSUED = "issued"
    HELD_FOR_REVIEW = "held_for_review"
    REFUSED = "refused"
    ERROR = "error"


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price: Optional[float] = None
    risk_index: Optional[float] = None
    reason: Optional[str] = None


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen_shipper(self, shipper_id: str) -> float:
        """Returns a risk index between 0.0 and 100.0."""
        return 25.0


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    def compute_price(self, weight_kg: float, distance_km: float) -> float:
        """
        Computes price based on tariff rules.
        Base rate: 5.0 per 100kg + 0.50 per km.
        """
        weight_charge = (weight_kg / 100.0) * 5.0
        distance_charge = distance_km * 0.50
        return round(weight_charge + distance_charge, 2)


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def send_quote_issued(self, shipper_id: str, quote_id: str, price: float) -> str:
        """Returns confirmation identifier."""
        return f"notif_{quote_id}_issued"
    
    def send_quote_held_for_review(self, shipper_id: str, quote_id: str) -> str:
        """Returns confirmation identifier."""
        return f"notif_{quote_id}_review"
    
    def send_quote_refused(self, shipper_id: str, quote_id: str, reason: str) -> str:
        """Returns confirmation identifier."""
        return f"notif_{quote_id}_refused"


class QuoteStore:
    """PostgreSQL-backed quote record storage."""
    
    def __init__(self):
        self.quotes = {}
        self.counter = 0
    
    def create_quote(self, shipper_id: str, weight_kg: float, distance_km: float, 
                    declared_value: float) -> str:
        """Creates a new quote record. Returns quote_id."""
        self.counter += 1
        quote_id = f"QT{self.counter:06d}"
        self.quotes[quote_id] = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.ISSUED
        )
        return quote_id
    
    def update_quote_status(self, quote_id: str, status: QuoteStatus, 
                           price: Optional[float] = None,
                           risk_index: Optional[float] = None,
                           reason: Optional[str] = None) -> str:
        """Updates quote status and optional fields. Returns confirmation."""
        if quote_id in self.quotes:
            quote = self.quotes[quote_id]
            quote.status = status
            if price is not None:
                quote.price = price
            if risk_index is not None:
                quote.risk_index = risk_index
            if reason is not None:
                quote.reason = reason
            return f"stored_{quote_id}"
        raise ValueError(f"Quote {quote_id} not found")
    
    def get_quote(self, quote_id: str) -> Quote:
        """Retrieves a quote by ID."""
        if quote_id in self.quotes:
            return self.quotes[quote_id]
        raise ValueError(f"Quote {quote_id} not found")


class QuoteAPI:
    """Main orchestration API for the quotation flow."""
    
    # Risk thresholds for screening-based decision
    RISK_THRESHOLD_REFUSE = 80.0
    RISK_THRESHOLD_REVIEW = 60.0
    
    # Minimum weight constraint
    MIN_WEIGHT_KG = 100.0
    
    def __init__(self, quote_store: QuoteStore, screening_service: ScreeningService,
                 tariff_engine: TariffEngine, notification_service: NotificationService):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service
    
    def validate_request(self, shipper_id: str, weight_kg: float, distance_km: float,
                        declared_value: float) -> bool:
        """Validates quote request parameters."""
        if not shipper_id or len(shipper_id) == 0:
            raise ValueError("shipper_id is required")
        if weight_kg < self.MIN_WEIGHT_KG:
            raise ValueError(f"weight_kg must be at least {self.MIN_WEIGHT_KG}")
        if distance_km <= 0:
            raise ValueError("distance_km must be positive")
        if declared_value < 0:
            raise ValueError("declared_value must be non-negative")
        return True
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float,
                     declared_value: float) -> dict:
        """
        Main quotation flow:
        1. Validate request
        2. Create quote record
        3. Screen shipper
        4. Apply screening decision (refuse/review/proceed)
        5. If proceeding, compute price
        6. Notify shipper
        7. Return outcome
        """
        try:
            # Step 1: Validate
            self.validate_request(shipper_id, weight_kg, distance_km, declared_value)
            
            # Step 2: Create quote record
            quote_id = self.quote_store.create_quote(shipper_id, weight_kg, distance_km, 
                                                      declared_value)
            
            # Step 3: Screen shipper
            risk_index = self.screening_service.screen_shipper(shipper_id)
            
            # Step 4: Apply screening decision
            if risk_index >= self.RISK_THRESHOLD_REFUSE:
                # Refuse the quote
                self.quote_store.update_quote_status(
                    quote_id, QuoteStatus.REFUSED, 
                    risk_index=risk_index,
                    reason="Shipper failed denied-party screening"
                )
                self.notification_service.send_quote_refused(
                    shipper_id, quote_id, "Shipper failed denied-party screening"
                )
                return {
                    "status": "rejected",
                    "quote_id": quote_id,
                    "reason": "Shipper failed denied-party screening"
                }
            elif risk_index >= self.RISK_THRESHOLD_REVIEW:
                # Hold for manual review
                self.quote_store.update_quote_status(
                    quote_id, QuoteStatus.HELD_FOR_REVIEW,
                    risk_index=risk_index,
                    reason="Held for compliance review"
                )
                self.notification_service.send_quote_held_for_review(shipper_id, quote_id)
                return {
                    "status": "held_for_review",
                    "quote_id": quote_id,
                    "reason": "Held for compliance review"
                }
            
            # Step 5: Compute price
            price = self.tariff_engine.compute_price(weight_kg, distance_km)
            
            # Step 6: Update and notify
            self.quote_store.update_quote_status(
                quote_id, QuoteStatus.ISSUED,
                price=price,
                risk_index=risk_index
            )
            self.notification_service.send_quote_issued(shipper_id, quote_id, price)
            
            # Step 7: Return outcome
            return {
                "status": "confirmed",
                "quote_id": quote_id,
                "price": price,
                "shipper_id": shipper_id,
                "weight_kg": weight_kg,
                "distance_km": distance_km,
                "declared_value": declared_value
            }
        
        except ValueError as e:
            return {
                "status": "error: invalid_request",
                "reason": str(e)
            }
        except Exception as e:
            return {
                "status": "error: internal_error",
                "reason": str(e)
            }


def handle(request: dict) -> dict:
    """
    End-to-end request handler for CargoQuote quotation flow.
    
    Expects request dict with keys:
    - shipper_id: str
    - weight_kg: float
    - distance_km: float
    - declared_value: float
    - Optional override keys for testing:
      - screening_service_result: float (risk index override)
      - tariff_engine_result: float (price override)
      - quote_store_result: str (confirmation override)
      - notification_service_result: str (confirmation override)
    
    Returns dict with "status" key and outcome details.
    """
    # Create dependencies
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    
    # Create API orchestrator
    quote_api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)
    
    # Handle test overrides
    if "screening_service_result" in request:
        original_screen = screening_service.screen_shipper
        risk_value = request["screening_service_result"]
        screening_service.screen_shipper = lambda _: risk_value
    
    if "tariff_engine_result" in request:
        original_compute = tariff_engine.compute_price
        price_value = request["tariff_engine_result"]
        tariff_engine.compute_price = lambda _, __: price_value
    
    # Execute quotation flow
    result = quote_api.request_quote(
        shipper_id=request.get("shipper_id", "SHIPPER_001"),
        weight_kg=request.get("weight_kg", 1000.0),
        distance_km=request.get("distance_km", 500.0),
        declared_value=request.get("declared_value", 10000.0)
    )
    
    return result