import json
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ValidationError(Exception):
    """Raised when request validation fails."""
    pass


class StorageError(Exception):
    """Raised when quote store operation fails."""
    pass


class ScreeningError(Exception):
    """Raised when screening service is unavailable."""
    pass


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price_amount: Optional[float] = None


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str) -> float:
        """
        Request shipper risk index from screening service.
        Returns a risk index as a float.
        """
        # In real system, would call external API
        # For testing/simulation, check request for screening_result
        return 0.0


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Compute freight price for validated request.
        Returns price amount as a float.
        """
        # Simple tariff: base fee + weight rate + distance rate
        base_fee = 50.0
        weight_rate = 0.5  # per kg
        distance_rate = 0.2  # per km
        return base_fee + (weight_kg * weight_rate) + (distance_km * distance_rate)


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        """
        Send quote document to shipper.
        Returns confirmation string.
        """
        # Fire-and-forget; failures are provider's responsibility
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """
        Send refusal notice to shipper.
        Returns confirmation string.
        """
        # Fire-and-forget; failures are provider's responsibility
        return "sent"


class QuoteStore:
    """PostgreSQL-backed quote storage."""
    
    def __init__(self):
        self.quotes = {}
        self.next_id = 1
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """
        Store a draft quote request.
        Returns quote ID as a string.
        Raises StorageError if storage is unavailable.
        """
        quote_id = f"Q{self.next_id}"
        self.next_id += 1
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT
        )
        self.quotes[quote_id] = quote
        return quote_id
    
    def update_quote(self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None) -> Quote:
        """
        Update quote status and optionally price.
        Returns updated quote object.
        Raises StorageError if quote not found or storage fails.
        """
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote


class QuoteAPI:
    """Main orchestrator for quote requests."""
    
    # Screening decision boundaries (from decision table DT-S)
    ACCEPT_MAX = 30
    REVIEW_MIN = 31
    REVIEW_MAX = 70
    REFUSE_MIN = 71
    
    # Validation bounds (from decision table DT-V)
    MIN_WEIGHT_KG = 100
    MAX_WEIGHT_KG = 10000
    MIN_DISTANCE_KM = 10
    MAX_DISTANCE_KM = 3000
    MIN_DECLARED_VALUE = 100
    MAX_DECLARED_VALUE = 1000000
    
    def __init__(self, quote_store: QuoteStore, tariff_engine: TariffEngine, 
                 screening_service: ScreeningService, notification_service: NotificationService):
        self.quote_store = quote_store
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service
    
    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> None:
        """
        Validate quote request against bounds.
        Raises ValidationError if any field is invalid.
        """
        if not shipper_id or len(shipper_id) == 0:
            raise ValidationError("shipper_id is required")
        if weight_kg < self.MIN_WEIGHT_KG or weight_kg > self.MAX_WEIGHT_KG:
            raise ValidationError(f"weight_kg must be between {self.MIN_WEIGHT_KG} and {self.MAX_WEIGHT_KG}")
        if distance_km < self.MIN_DISTANCE_KM or distance_km > self.MAX_DISTANCE_KM:
            raise ValidationError(f"distance_km must be between {self.MIN_DISTANCE_KM} and {self.MAX_DISTANCE_KM}")
        if declared_value < self.MIN_DECLARED_VALUE or declared_value > self.MAX_DECLARED_VALUE:
            raise ValidationError(f"declared_value must be between {self.MIN_DECLARED_VALUE} and {self.MAX_DECLARED_VALUE}")
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        """
        Main entry point for quote requests.
        Returns response dict with status and details.
        """
        # Step 1: Request validation
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {
                "status": "rejected_invalid_request",
                "error": str(e)
            }
        
        # Step 2: Draft storage
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError as e:
            return {
                "status": "store_unavailable_error",
                "error": str(e)
            }
        
        # Step 3: Screening decision
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError as e:
            # Screening failure: price the quote, store on hold, no notification
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
                return {
                    "status": "held_unscreened",
                    "quote_id": quote_id,
                    "price": price_amount,
                    "message": "Quote held pending screening retry"
                }
            except StorageError:
                return {
                    "status": "error",
                    "error": "Storage failure during fallback pricing"
                }
        
        # Process screening result
        if risk_index <= self.ACCEPT_MAX:
            # Accept: price, store, notify
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
                # Notification is fire-and-forget
                self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price": price_amount
                }
            except StorageError:
                return {
                    "status": "error",
                    "error": "Storage failure during quote confirmation"
                }
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review hold: store, no pricing, no notification
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {
                    "status": "review_hold",
                    "quote_id": quote_id,
                    "message": "Quote held for manual compliance review"
                }
            except StorageError:
                return {
                    "status": "error",
                    "error": "Storage failure during review hold"
                }
        elif risk_index >= self.REFUSE_MIN:
            # Refuse: store, notify, no pricing
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
                # Notification is fire-and-forget
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
                return {
                    "status": "refused_screening",
                    "quote_id": quote_id,
                    "message": "Quote refused on screening grounds"
                }
            except StorageError:
                return {
                    "status": "error",
                    "error": "Storage failure during refusal"
                }
        
        return {
            "status": "error",
            "error": "Unknown screening decision"
        }


class CargoQuoteSystem:
    """Main system facade."""
    
    def __init__(self):
        self.quote_store = QuoteStore()
        self.tariff_engine = TariffEngine()
        self.screening_service = ScreeningService()
        self.notification_service = NotificationService()
        self.quote_api = QuoteAPI(
            self.quote_store,
            self.tariff_engine,
            self.screening_service,
            self.notification_service
        )
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        """Delegate to QuoteAPI."""
        return self.quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)


# Global system instance
_system = CargoQuoteSystem()


def handle(request: dict) -> dict:
    """
    Handle one end-to-end quote flow.
    
    Input request dict keys:
    - shipper_id: string
    - weight_kg: float
    - distance_km: float
    - declared_value: float
    - screening_result: optional float (for testing)
    - store_result: optional string (for testing)
    
    Returns dict with "status" key naming the outcome.
    """
    # Extract request parameters
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)
    
    # Handle test injections
    if "store_result" in request and request["store_result"] == "error":
        return {
            "status": "store_unavailable_error",
            "error": "Simulated storage failure"
        }
    
    if "screening_result" in request:
        screening_result = request["screening_result"]
        # Inject screening result
        original_screen = _system.screening_service.screen
        _system.screening_service.screen = lambda sid: screening_result
        try:
            result = _system.request_quote(shipper_id, weight_kg, distance_km, declared_value)
        finally:
            _system.screening_service.screen = original_screen
        return result
    
    # Normal flow
    return _system.request_quote(shipper_id, weight_kg, distance_km, declared_value)