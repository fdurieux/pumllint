from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


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
    status: QuoteStatus = QuoteStatus.DRAFT
    price_amount: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    risk_index: Optional[float] = None


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


class PricingError(Exception):
    pass


class NotificationError(Exception):
    pass


class RequestValidator:
    """Validates quote request parameters per decision table DT-V."""
    
    MIN_WEIGHT = 0.1
    MAX_WEIGHT = 30000.0
    MIN_DISTANCE = 1.0
    MAX_DISTANCE = 5000.0
    MIN_DECLARED_VALUE = 0.0
    MAX_DECLARED_VALUE = 1000000.0
    
    def validate(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        """
        Validate request bounds.
        Returns True if valid, raises ValidationError otherwise.
        """
        if not shipper_id or not isinstance(shipper_id, str) or len(shipper_id.strip()) == 0:
            raise ValidationError("shipper_id is required and must be non-empty")
        
        if not isinstance(weight_kg, (int, float)) or weight_kg < self.MIN_WEIGHT or weight_kg > self.MAX_WEIGHT:
            raise ValidationError(f"weight_kg must be between {self.MIN_WEIGHT} and {self.MAX_WEIGHT}")
        
        if not isinstance(distance_km, (int, float)) or distance_km < self.MIN_DISTANCE or distance_km > self.MAX_DISTANCE:
            raise ValidationError(f"distance_km must be between {self.MIN_DISTANCE} and {self.MAX_DISTANCE}")
        
        if not isinstance(declared_value, (int, float)) or declared_value < self.MIN_DECLARED_VALUE or declared_value > self.MAX_DECLARED_VALUE:
            raise ValidationError(f"declared_value must be between {self.MIN_DECLARED_VALUE} and {self.MAX_DECLARED_VALUE}")
        
        return True


class QuoteStore:
    """Stores and retrieves quote records."""
    
    def __init__(self):
        self.quotes = {}
        self.available = True
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """
        Store a draft quote.
        Returns quote_id on success, raises StorageError on failure.
        """
        if not self.available:
            raise StorageError("Quote store unavailable")
        
        quote_id = str(uuid4())
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
    
    def update_quote(self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None, risk_index: Optional[float] = None) -> Quote:
        """
        Update a quote's status and optional price.
        Returns updated quote, raises StorageError if not found or store unavailable.
        """
        if not self.available:
            raise StorageError("Quote store unavailable")
        
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        if risk_index is not None:
            quote.risk_index = risk_index
        return quote
    
    def get_quote(self, quote_id: str) -> Optional[Quote]:
        """Retrieve a quote by id."""
        return self.quotes.get(quote_id)


class ScreeningService:
    """External denied-party screening provider."""
    
    def __init__(self):
        self.available = True
    
    def screen(self, shipper_id: str) -> float:
        """
        Screen shipper against denied-party lists.
        Returns a risk index (float), raises ScreeningError on service unavailability.
        """
        if not self.available:
            raise ScreeningError("Screening service unavailable")
        return 0.0


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    BASE_RATE = 10.0
    WEIGHT_RATE = 0.5
    DISTANCE_RATE = 0.1
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Compute freight price.
        Returns price amount as a single float value.
        """
        base = self.BASE_RATE
        weight_cost = weight_kg * self.WEIGHT_RATE
        distance_cost = distance_km * self.DISTANCE_RATE
        return base + weight_cost + distance_cost


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def __init__(self):
        self.available = True
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        """
        Send quote document to shipper.
        Returns confirmation identifier. Fire-and-forget; failures do not affect quotation response.
        """
        if not self.available:
            raise NotificationError("Notification service unavailable")
        return f"quote_notification_{quote_id}"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """
        Send refusal notice to shipper.
        Returns confirmation identifier. Fire-and-forget; failures do not affect quotation response.
        """
        if not self.available:
            raise NotificationError("Notification service unavailable")
        return f"refusal_notification_{quote_id}"


class QuoteAPI:
    """
    Main quotation orchestrator.
    Receives requests, validates, screens, prices, stores, and notifies.
    """
    
    ACCEPT_MAX = 25.0
    REVIEW_MIN = 25.0
    REVIEW_MAX = 75.0
    REFUSE_MIN = 75.0
    
    def __init__(self, validator: RequestValidator, store: QuoteStore, 
                 screening: ScreeningService, tariff: TariffEngine, 
                 notification: NotificationService):
        self.validator = validator
        self.store = store
        self.screening = screening
        self.tariff = tariff
        self.notification = notification
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        """
        Process a quote request end-to-end.
        Returns a response dict with 'status' key and optional 'quote_id' and 'price' keys.
        """
        try:
            self.validator.validate(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": f"rejected_invalid_request: {str(e)}"}
        
        try:
            quote_id = self.store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError as e:
            return {"status": f"store_unavailable_error: {str(e)}"}
        
        screening_available = True
        risk_index = None
        
        try:
            risk_index = self.screening.screen(shipper_id)
        except ScreeningError:
            screening_available = False
        
        if screening_available:
            if risk_index <= self.ACCEPT_MAX:
                try:
                    price_amount = self.tariff.price(weight_kg, distance_km)
                    self.store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount=price_amount, risk_index=risk_index)
                    try:
                        self.notification.send_quote_document(shipper_id, quote_id, price_amount)
                    except NotificationError:
                        pass
                    return {
                        "status": "quoted",
                        "quote_id": quote_id,
                        "price": price_amount
                    }
                except (StorageError, PricingError) as e:
                    return {"status": f"error: {str(e)}"}
            
            elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
                try:
                    self.store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD, risk_index=risk_index)
                    return {
                        "status": "review_hold",
                        "quote_id": quote_id
                    }
                except StorageError as e:
                    return {"status": f"error: {str(e)}"}
            
            elif risk_index >= self.REFUSE_MIN:
                try:
                    self.store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING, risk_index=risk_index)
                    try:
                        self.notification.send_refusal_notice(shipper_id, quote_id)
                    except NotificationError:
                        pass
                    return {
                        "status": "refused_screening",
                        "quote_id": quote_id
                    }
                except StorageError as e:
                    return {"status": f"error: {str(e)}"}
        
        else:
            try:
                price_amount = self.tariff.price(weight_kg, distance_km)
                self.store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount=price_amount)
                return {
                    "status": "held_unscreened",
                    "quote_id": quote_id,
                    "price": price_amount
                }
            except (StorageError, PricingError) as e:
                return {"status": f"error: {str(e)}"}


def handle(request: dict) -> dict:
    """
    Handle a quote request end-to-end.
    
    Input request dict keys:
      - shipper_id: str
      - weight_kg: float
      - distance_km: float
      - declared_value: float
      - quote_store_available: bool (optional, default True)
      - screening_service_available: bool (optional, default True)
      - notification_service_available: bool (optional, default True)
      - screening_result: float (optional, overrides screening service result)
    
    Returns dict with 'status' key and optional 'quote_id' and 'price' keys.
    """
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0.0)
    distance_km = request.get("distance_km", 0.0)
    declared_value = request.get("declared_value", 0.0)
    
    validator = RequestValidator()
    store = QuoteStore()
    screening = ScreeningService()
    tariff = TariffEngine()
    notification = NotificationService()
    
    store.available = request.get("quote_store_available", True)
    screening.available = request.get("screening_service_available", True)
    notification.available = request.get("notification_service_available", True)
    
    if "screening_result" in request:
        original_screen = screening.screen
        screening_result_value = request["screening_result"]
        def mock_screen(shipper_id: str) -> float:
            if screening.available:
                return screening_result_value
            else:
                raise ScreeningError("Screening service unavailable")
        screening.screen = mock_screen
    
    api = QuoteAPI(validator, store, screening, tariff, notification)
    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)