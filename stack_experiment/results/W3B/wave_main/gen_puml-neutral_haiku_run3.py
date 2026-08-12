from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime
import uuid


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


class PricingError(Exception):
    pass


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price_amount: Optional[float] = None
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.utcnow().isoformat()


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str, screening_result: Optional[str] = None, screening_status: Optional[str] = None, risk_index: Optional[float] = None) -> float:
        """
        Screen a shipper and return a risk index.
        
        Args:
            shipper_id: The shipper identifier
            screening_result: Test override for result ("error" triggers ScreeningError)
            screening_status: Test override for status
            risk_index: Test override for risk index value
            
        Returns:
            float: Risk index (0-100)
        """
        if screening_result == "error" or screening_status == "unavailable":
            raise ScreeningError("Screening service unavailable")
        
        if risk_index is not None:
            return risk_index
        
        return 25.0


class TariffEngine:
    """Computes freight price from weight and distance."""

    ACCEPT_MAX = 40
    REVIEW_MIN = 41
    REVIEW_MAX = 70
    REFUSE_MIN = 71

    def price(self, weight_kg: float, distance_km: float, pricing_result: Optional[str] = None) -> float:
        """
        Compute the freight price.
        
        Args:
            weight_kg: Weight in kilograms
            distance_km: Distance in kilometers
            pricing_result: Test override for result
            
        Returns:
            float: Price amount
        """
        if pricing_result == "error":
            raise PricingError("Pricing computation failed")
        
        base_rate = 5.0
        weight_factor = 0.02
        distance_factor = 0.15
        price = base_rate + (weight_kg * weight_factor) + (distance_km * distance_factor)
        return round(price, 2)


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float, notification_result: Optional[str] = None) -> str:
        """
        Send a quote document to the shipper (fire-and-forget).
        
        Returns:
            str: Confirmation identifier
        """
        if notification_result == "error":
            return "notification_failed"
        return f"doc_{quote_id}"

    def send_refusal_notice(self, shipper_id: str, quote_id: str, notification_result: Optional[str] = None) -> str:
        """
        Send a refusal notice to the shipper (fire-and-forget).
        
        Returns:
            str: Confirmation identifier
        """
        if notification_result == "error":
            return "notification_failed"
        return f"refusal_{quote_id}"


class QuoteStore:
    """PostgreSQL-backed quote storage."""

    def __init__(self):
        self.quotes = {}

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float, storage_result: Optional[str] = None) -> str:
        """
        Store a draft quote request.
        
        Args:
            storage_result: Test override ("error" triggers StorageError)
            
        Returns:
            str: Quote ID
        """
        if storage_result == "error":
            raise StorageError("Quote store unavailable")
        
        quote_id = str(uuid.uuid4())
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
        Update a quote with new status and optional price.
        
        Returns:
            Quote: Updated quote object
        """
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        quote.updated_at = datetime.utcnow().isoformat()
        return quote

    def get_quote(self, quote_id: str) -> Optional[Quote]:
        """Retrieve a quote by ID."""
        return self.quotes.get(quote_id)


class QuoteAPI:
    """Main quotation orchestration service."""

    def __init__(self, quote_store: QuoteStore, tariff_engine: TariffEngine, 
                 screening_service: ScreeningService, notification_service: NotificationService):
        self.quote_store = quote_store
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        """
        Validate request bounds per DT-V.
        
        Returns:
            bool: True if valid, False otherwise
        """
        if not shipper_id or len(shipper_id.strip()) == 0:
            return False
        if weight_kg <= 0 or weight_kg > 30000:
            return False
        if distance_km <= 0 or distance_km > 5000:
            return False
        if declared_value < 0 or declared_value > 1000000:
            return False
        return True

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float,
                     validation_result: Optional[str] = None, storage_result: Optional[str] = None,
                     screening_result: Optional[str] = None, screening_status: Optional[str] = None,
                     risk_index: Optional[float] = None, pricing_result: Optional[str] = None,
                     notification_result: Optional[str] = None) -> dict:
        """
        Handle a quote request end-to-end.
        
        Returns:
            dict: Response with 'status' key and optional 'quote_id', 'price', 'reason'
        """
        
        if validation_result == "error" or not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected_invalid_request"}
        
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value, storage_result=storage_result)
        except StorageError as e:
            return {"status": "store_unavailable_error", "reason": str(e)}
        
        screening_failed = False
        try:
            actual_risk_index = self.screening_service.screen(
                shipper_id, 
                screening_result=screening_result, 
                screening_status=screening_status,
                risk_index=risk_index
            )
        except ScreeningError:
            screening_failed = True
            actual_risk_index = None
        
        if screening_failed:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km, pricing_result=pricing_result)
                self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount=price_amount)
                return {
                    "status": "held_unscreened_response",
                    "quote_id": quote_id,
                    "price": price_amount
                }
            except PricingError as e:
                return {"status": "error", "reason": f"Pricing failed: {str(e)}"}
        
        if actual_risk_index <= self.tariff_engine.ACCEPT_MAX:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km, pricing_result=pricing_result)
            except PricingError as e:
                return {"status": "error", "reason": f"Pricing failed: {str(e)}"}
            
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount=price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount, notification_result=notification_result)
            return {
                "status": "quoted_response",
                "quote_id": quote_id,
                "price": price_amount
            }
        
        elif self.tariff_engine.REVIEW_MIN <= actual_risk_index <= self.tariff_engine.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {
                "status": "review_hold_response",
                "quote_id": quote_id
            }
        
        elif actual_risk_index >= self.tariff_engine.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            self.notification_service.send_refusal_notice(shipper_id, quote_id, notification_result=notification_result)
            return {
                "status": "refused_screening_response",
                "quote_id": quote_id
            }


def handle(request: dict) -> dict:
    """
    End-to-end quote request handler.
    
    Args:
        request: Dict with keys like shipper_id, weight_kg, distance_km, declared_value,
                 and test overrides like validation_result, storage_result, screening_result, etc.
    
    Returns:
        dict: Response with 'status' key and optional 'quote_id', 'price', 'reason'
    """
    quote_store = QuoteStore()
    tariff_engine = TariffEngine()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    quote_api = QuoteAPI(quote_store, tariff_engine, screening_service, notification_service)
    
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0.0)
    distance_km = request.get("distance_km", 0.0)
    declared_value = request.get("declared_value", 0.0)
    
    validation_result = request.get("validation_result")
    storage_result = request.get("storage_result")
    screening_result = request.get("screening_result")
    screening_status = request.get("screening_status")
    risk_index = request.get("risk_index")
    pricing_result = request.get("pricing_result")
    notification_result = request.get("notification_result")
    
    return quote_api.request_quote(
        shipper_id=shipper_id,
        weight_kg=weight_kg,
        distance_km=distance_km,
        declared_value=declared_value,
        validation_result=validation_result,
        storage_result=storage_result,
        screening_result=screening_result,
        screening_status=screening_status,
        risk_index=risk_index,
        pricing_result=pricing_result,
        notification_result=notification_result
    )