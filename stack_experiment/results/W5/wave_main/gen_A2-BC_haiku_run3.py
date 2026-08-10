"""
CargoQuote — Instant Freight Quotation System

A self-contained implementation of the cargo quotation flow:
- Request validation
- Shipper screening (external)
- Tariff-based price computation
- Quote storage
- Notification delivery (external)
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class QuoteStatus(Enum):
    """Possible states of a quote through its lifecycle."""
    SUBMITTED = "submitted"
    SCREENED = "screened"
    HELD_FOR_REVIEW = "held_for_review"
    ISSUED = "issued"
    REFUSED = "refused"
    ERROR = "error"


class RiskLevel(Enum):
    """Risk categories from screening."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class QuoteRequest:
    """A quote request from a shipper."""
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value_eur: float
    
    def validate(self) -> Optional[str]:
        """Validate request fields. Return error message if invalid."""
        if not self.shipper_id or not self.shipper_id.strip():
            return "shipper_id required"
        if self.weight_kg <= 0:
            return "weight_kg must be positive"
        if self.distance_km <= 0:
            return "distance_km must be positive"
        if self.declared_value_eur < 0:
            return "declared_value_eur cannot be negative"
        return None


@dataclass
class Quote:
    """A persisted quote record."""
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value_eur: float
    status: QuoteStatus
    price_eur: Optional[float] = None
    risk_index: Optional[float] = None
    reason: Optional[str] = None


class ScreeningService:
    """
    External denied-party screening provider.
    Returns a shipper risk index (0.0 to 1.0).
    """
    
    def request_risk_index(self, shipper_id: str) -> float:
        """
        Screen a shipper and return risk index.
        0.0 = low risk, 1.0 = high risk.
        """
        # In real system, calls external screening API.
        # For test/demo: synthetic logic based on shipper_id.
        if shipper_id.startswith("high_"):
            return 0.95
        elif shipper_id.startswith("med_"):
            return 0.65
        else:
            return 0.15


class TariffEngine:
    """
    Computes freight price from weight and distance per tariff rules.
    """
    
    def compute_price(self, weight_kg: float, distance_km: float) -> float:
        """
        Calculate price in EUR based on tariff.
        
        Simple tariff: base_rate + per_kg + per_km
        """
        base_rate = 15.0  # EUR
        per_kg_rate = 0.5  # EUR per kg
        per_km_rate = 0.02  # EUR per km
        
        price = base_rate + (weight_kg * per_kg_rate) + (distance_km * per_km_rate)
        return round(price, 2)


class QuoteStore:
    """
    PostgreSQL-backed quote persistence.
    """
    
    def __init__(self):
        """Initialize in-memory store (simulates PostgreSQL)."""
        self._quotes = {}
        self._next_id = 1000
    
    def create_quote(self, request: QuoteRequest) -> str:
        """
        Store a new quote request.
        Return the assigned quote_id.
        """
        quote_id = f"Q{self._next_id}"
        self._next_id += 1
        
        quote = Quote(
            quote_id=quote_id,
            shipper_id=request.shipper_id,
            weight_kg=request.weight_kg,
            distance_km=request.distance_km,
            declared_value_eur=request.declared_value_eur,
            status=QuoteStatus.SUBMITTED
        )
        self._quotes[quote_id] = quote
        return quote_id
    
    def update_quote(
        self,
        quote_id: str,
        status: QuoteStatus,
        price_eur: Optional[float] = None,
        risk_index: Optional[float] = None,
        reason: Optional[str] = None
    ) -> str:
        """
        Update quote with screening/pricing outcome.
        Return quote_id for chaining.
        """
        if quote_id not in self._quotes:
            raise ValueError(f"Quote {quote_id} not found")
        
        quote = self._quotes[quote_id]
        quote.status = status
        if price_eur is not None:
            quote.price_eur = price_eur
        if risk_index is not None:
            quote.risk_index = risk_index
        if reason is not None:
            quote.reason = reason
        
        return quote_id
    
    def get_quote(self, quote_id: str) -> Optional[Quote]:
        """Retrieve a quote by ID."""
        return self._quotes.get(quote_id)


class NotificationService:
    """
    External messaging provider.
    Delivers quote documents and refusal notices to shipper.
    """
    
    def send_quote_issued(self, shipper_id: str, quote_id: str, price_eur: float) -> str:
        """
        Deliver an issued quote to the shipper.
        Return confirmation token.
        """
        confirmation = f"NOTIF-ISSUED-{quote_id}"
        # In real system: sends email/SMS/API notification with quote document.
        return confirmation
    
    def send_quote_held_for_review(self, shipper_id: str, quote_id: str) -> str:
        """
        Notify shipper that quote is held for manual review.
        Return confirmation token.
        """
        confirmation = f"NOTIF-HELD-{quote_id}"
        # In real system: sends notification explaining review process.
        return confirmation
    
    def send_quote_refused(self, shipper_id: str, quote_id: str, reason: str) -> str:
        """
        Deliver refusal notice to shipper.
        Return confirmation token.
        """
        confirmation = f"NOTIF-REFUSED-{quote_id}"
        # In real system: sends notification with refusal reason.
        return confirmation


class QuoteAPI:
    """
    Main orchestrator of the quotation flow.
    
    Responsibilities:
    - Validate incoming requests
    - Store quote requests
    - Orchestrate screening
    - Orchestrate pricing
    - Apply risk-based rules
    - Trigger notifications
    - Return quotation outcome to shipper
    """
    
    # Risk thresholds
    RISK_THRESHOLD_REVIEW = 0.7  # Above this: hold for review
    RISK_THRESHOLD_REFUSE = 0.9  # Above this: refuse outright
    
    def __init__(
        self,
        quote_store: QuoteStore,
        screening_service: ScreeningService,
        tariff_engine: TariffEngine,
        notification_service: NotificationService
    ):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service
    
    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value_eur: float
    ) -> dict:
        """
        Main entry point: process a quote request end-to-end.
        
        Return a dict with:
        - status: "issued", "held_for_review", "refused", or "error: <reason>"
        - quote_id: assigned quote ID (if applicable)
        - price_eur: computed price (if issued)
        - reason: explanation (if held or refused)
        """
        
        # Step 1: Validate request
        request = QuoteRequest(
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value_eur=declared_value_eur
        )
        
        error = request.validate()
        if error:
            return {"status": f"error: {error}"}
        
        # Step 2: Store the request
        try:
            quote_id = self.quote_store.create_quote(request)
        except Exception as e:
            return {"status": f"error: failed to store quote: {str(e)}"}
        
        # Step 3: Screen the shipper
        try:
            risk_index = self.screening_service.request_risk_index(shipper_id)
        except Exception as e:
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.ERROR,
                reason=f"screening_failed: {str(e)}"
            )
            return {"status": f"error: screening service unavailable"}
        
        self.quote_store.update_quote(quote_id, QuoteStatus.SCREENED, risk_index=risk_index)
        
        # Step 4: Apply risk-based decision rules
        if risk_index >= self.RISK_THRESHOLD_REFUSE:
            # High-risk shipper: refuse outright
            reason = f"shipper_risk_too_high: index={risk_index:.2f}"
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.REFUSED,
                reason=reason
            )
            try:
                self.notification_service.send_quote_refused(shipper_id, quote_id, reason)
            except Exception:
                pass  # Notification failure doesn't fail the quote decision.
            
            return {
                "status": "refused",
                "quote_id": quote_id,
                "reason": reason
            }
        
        elif risk_index >= self.RISK_THRESHOLD_REVIEW:
            # Medium-risk shipper: hold for manual review
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.HELD_FOR_REVIEW,
                reason=f"risk_index={risk_index:.2f}_exceeds_auto_threshold"
            )
            try:
                self.notification_service.send_quote_held_for_review(shipper_id, quote_id)
            except Exception:
                pass  # Notification failure doesn't fail the quote decision.
            
            return {
                "status": "held_for_review",
                "quote_id": quote_id,
                "reason": f"Manual compliance review required (risk index: {risk_index:.2f})"
            }
        
        # Step 5: Low-risk shipper: compute price and issue quote
        try:
            price_eur = self.tariff_engine.compute_price(weight_kg, distance_km)
        except Exception as e:
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.ERROR,
                reason=f"pricing_failed: {str(e)}"
            )
            return {"status": f"error: pricing service failed"}
        
        self.quote_store.update_quote(
            quote_id,
            QuoteStatus.ISSUED,
            price_eur=price_eur
        )
        
        # Step 6: Notify shipper of issued quote
        try:
            self.notification_service.send_quote_issued(shipper_id, quote_id, price_eur)
        except Exception:
            pass  # Notification failure doesn't fail the quote issuance.
        
        return {
            "status": "issued",
            "quote_id": quote_id,
            "price_eur": price_eur
        }


# Module-level handle() function to drive end-to-end scenarios
def handle(request: dict) -> dict:
    """
    Run one end-to-end quotation flow from a request dict.
    
    Input dict keys:
    - shipper_id: string
    - weight_kg: float
    - distance_km: float
    - declared_value_eur: float
    - screening_result (optional): "high", "med", "low" or numeric risk index
    - tariff_result (optional): numeric price in EUR
    - notification_status (optional): "success", "error"
    
    Return dict with:
    - status: outcome string ("issued", "held_for_review", "refused", "error: ...")
    - Additional keys depending on outcome (quote_id, price_eur, reason)
    """
    
    shipper_id = request.get("shipper_id", "unknown")
    weight_kg = float(request.get("weight_kg", 100.0))
    distance_km = float(request.get("distance_km", 500.0))
    declared_value_eur = float(request.get("declared_value_eur", 10000.0))
    
    # Validate request early
    test_request = QuoteRequest(
        shipper_id=shipper_id,
        weight_kg=weight_kg,
        distance_km=distance_km,
        declared_value_eur=declared_value_eur
    )
    
    error = test_request.validate()
    if error:
        return {"status": f"error: {error}"}
    
    # Build collaborators
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    
    # Override screening if test data provides a result
    if "screening_result" in request:
        result = request["screening_result"]
        if isinstance(result, (int, float)):
            risk_index = float(result)
        elif result == "high":
            risk_index = 0.95
        elif result == "med":
            risk_index = 0.65
        elif result == "low":
            risk_index = 0.15
        else:
            risk_index = 0.5
        
        screening_service.request_risk_index = lambda _: risk_index
    
    # Override tariff if test data provides a result
    if "tariff_result" in request:
        price = float(request["tariff_result"])
        tariff_engine.compute_price = lambda _, __: price
    
    # Build API
    api = QuoteAPI(
        quote_store=quote_store,
        screening_service=screening_service,
        tariff_engine=tariff_engine,
        notification_service=notification_service
    )
    
    # Process the quote request
    result = api.request_quote(
        shipper_id=shipper_id,
        weight_kg=weight_kg,
        distance_km=distance_km,
        declared_value_eur=declared_value_eur
    )
    
    return result


if __name__ == "__main__":
    # Example scenarios
    
    # Scenario 1: Low-risk shipper, issued quote
    print("Scenario 1: Low-risk shipper")
    response = handle({
        "shipper_id": "shipper_acme",
        "weight_kg": 500.0,
        "distance_km": 1000.0,
        "declared_value_eur": 50000.0,
        "screening_result": "low"
    })
    print(f"  Result: {response}")
    print()
    
    # Scenario 2: Medium-risk shipper, held for review
    print("Scenario 2: Medium-risk shipper")
    response = handle({
        "shipper_id": "med_shipper",
        "weight_kg": 250.0,
        "distance_km": 500.0,
        "declared_value_eur": 25000.0,
        "screening_result": "med"
    })
    print(f"  Result: {response}")
    print()
    
    # Scenario 3: High-risk shipper, refused
    print("Scenario 3: High-risk shipper")
    response = handle({
        "shipper_id": "high_risk_co",
        "weight_kg": 100.0,
        "distance_km": 200.0,
        "declared_value_eur": 5000.0,
        "screening_result": "high"
    })
    print(f"  Result: {response}")
    print()
    
    # Scenario 4: Invalid request (negative weight)
    print("Scenario 4: Invalid request")
    response = handle({
        "shipper_id": "shipper_bad",
        "weight_kg": -10.0,
        "distance_km": 500.0,
        "declared_value_eur": 10000.0
    })
    print(f"  Result: {response}")