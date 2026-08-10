"""CargoQuote — Instant Freight Quotation System"""

from enum import Enum
from typing import Optional
import uuid


class ValidationError(Exception):
    """Raised when request validation fails."""
    pass


class StorageError(Exception):
    """Raised when quote store operation fails."""
    pass


class ScreeningError(Exception):
    """Raised when screening service is unavailable."""
    pass


class QuoteStatus(str, Enum):
    """Quote lifecycle statuses."""
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


class ScreeningService:
    """External denied-party screening provider."""
    
    def __init__(self, screening_result: Optional[int] = None, 
                 screening_status: str = "ok"):
        """
        screening_result: risk index (0-100), or None to simulate unavailable.
        screening_status: "ok" (normal), "error" (service unavailable).
        """
        self.screening_result = screening_result
        self.screening_status = screening_status
    
    def screen(self, shipper_id: str) -> int:
        """Return riskIndex. Raises ScreeningError if unavailable."""
        if self.screening_status == "error":
            raise ScreeningError("Screening service unavailable")
        if self.screening_result is None:
            raise ScreeningError("Screening service unavailable")
        return self.screening_result


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    def __init__(self, price_result: Optional[float] = None):
        """price_result: the price amount to return, or None for error."""
        self.price_result = price_result
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute priceAmount for a validated request."""
        if self.price_result is None:
            raise ValueError("Pricing unavailable")
        base_price = 50.0
        weight_factor = weight_kg * 0.1
        distance_factor = distance_km * 0.5
        return base_price + weight_factor + distance_factor + self.price_result


class QuoteStore:
    """Stores quote requests and their lifecycle status."""
    
    def __init__(self, store_status: str = "ok"):
        """store_status: "ok" (normal), "error" (storage unavailable)."""
        self.store_status = store_status
        self.quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, 
                    distance_km: float, declared_value: float) -> str:
        """Store the draft; return quoteId. Raises StorageError if unavailable."""
        if self.store_status == "error":
            raise StorageError("Quote store unavailable")
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": QuoteStatus.DRAFT,
            "price_amount": None
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: QuoteStatus, 
                     price_amount: Optional[float] = None) -> str:
        """Update quote status and optionally price. Returns quote_id."""
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        self.quotes[quote_id]["status"] = status
        if price_amount is not None:
            self.quotes[quote_id]["price_amount"] = price_amount
        return quote_id


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def __init__(self, notification_status: str = "ok"):
        """notification_status: "ok" (normal), "error" (delivery fails)."""
        self.notification_status = notification_status
        self.sent_messages = []
    
    def send_quote_document(self, shipper_id: str, quote_id: str, 
                           price_amount: float) -> None:
        """Deliver the quote document. Fire-and-forget."""
        message = {
            "type": "quote_document",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
            "price_amount": price_amount
        }
        self.sent_messages.append(message)
        if self.notification_status == "error":
            pass
        return None
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Deliver the refusal notice. Fire-and-forget."""
        message = {
            "type": "refusal_notice",
            "shipper_id": shipper_id,
            "quote_id": quote_id
        }
        self.sent_messages.append(message)
        if self.notification_status == "error":
            pass
        return None


class QuoteAPI:
    """Orchestrates screening, pricing, storage, and notification."""
    
    ACCEPT_MAX = 25
    REVIEW_MIN = 26
    REVIEW_MAX = 75
    REFUSE_MIN = 76
    
    def __init__(self, screening_service: ScreeningService,
                 tariff_engine: TariffEngine,
                 quote_store: QuoteStore,
                 notification_service: NotificationService):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service
    
    def _validate_request(self, shipper_id: str, weight_kg: float,
                         distance_km: float, declared_value: float) -> bool:
        """Validate request bounds per decision table DT-V."""
        if not shipper_id or len(shipper_id) == 0:
            return False
        if weight_kg <= 0 or weight_kg > 30000:
            return False
        if distance_km <= 0 or distance_km > 3000:
            return False
        if declared_value < 0 or declared_value > 1000000:
            return False
        return True
    
    def request_quote(self, shipper_id: str, weight_kg: float,
                     distance_km: float, declared_value: float) -> dict:
        """Execute the quotation flow."""
        
        if not self._validate_request(shipper_id, weight_kg, distance_km, 
                                     declared_value):
            return {
                "status": "rejected_invalid_request",
                "quote_id": None,
                "price_amount": None,
                "reason": "Request validation failed"
            }
        
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageError as e:
            return {
                "status": "store_unavailable_error",
                "quote_id": None,
                "price_amount": None,
                "reason": str(e)
            }
        
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError as e:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.HELD_UNSCREENED, price_amount
                )
                return {
                    "status": "held_unscreened_response",
                    "quote_id": quote_id,
                    "price_amount": price_amount,
                    "reason": "Screening service unavailable"
                }
            except Exception as pricing_error:
                return {
                    "status": "error",
                    "quote_id": quote_id,
                    "price_amount": None,
                    "reason": f"Pricing failed: {str(pricing_error)}"
                }
        
        if risk_index <= self.ACCEPT_MAX:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.QUOTED, price_amount
                )
                self.notification_service.send_quote_document(
                    shipper_id, quote_id, price_amount
                )
                return {
                    "status": "quoted_response",
                    "quote_id": quote_id,
                    "price_amount": price_amount
                }
            except Exception as e:
                return {
                    "status": "error",
                    "quote_id": quote_id,
                    "price_amount": None,
                    "reason": str(e)
                }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            try:
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.REVIEW_HOLD
                )
                return {
                    "status": "review_hold_response",
                    "quote_id": quote_id,
                    "price_amount": None,
                    "reason": "Quote held for manual compliance review"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "quote_id": quote_id,
                    "price_amount": None,
                    "reason": str(e)
                }
        
        elif risk_index >= self.REFUSE_MIN:
            try:
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.REFUSED_SCREENING
                )
                self.notification_service.send_refusal_notice(
                    shipper_id, quote_id
                )
                return {
                    "status": "refused_screening_response",
                    "quote_id": quote_id,
                    "price_amount": None,
                    "reason": "Shipper failed screening"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "quote_id": quote_id,
                    "price_amount": None,
                    "reason": str(e)
                }
        
        return {
            "status": "error",
            "quote_id": quote_id,
            "price_amount": None,
            "reason": "Unexpected screening result"
        }


def handle(request: dict) -> dict:
    """Run one end-to-end flow from a test request dict."""
    
    shipper_id = request.get("shipper_id", "shipper_001")
    weight_kg = request.get("weight_kg", 500)
    distance_km = request.get("distance_km", 200)
    declared_value = request.get("declared_value", 5000)
    
    screening_result = request.get("screening_result", 10)
    screening_status = request.get("screening_status", "ok")
    
    price_result = request.get("price_result", 0)
    
    store_status = request.get("store_status", "ok")
    notification_status = request.get("notification_status", "ok")
    
    screening_service = ScreeningService(
        screening_result=screening_result,
        screening_status=screening_status
    )
    tariff_engine = TariffEngine(price_result=price_result)
    quote_store = QuoteStore(store_status=store_status)
    notification_service = NotificationService(
        notification_status=notification_status
    )
    
    quote_api = QuoteAPI(
        screening_service,
        tariff_engine,
        quote_store,
        notification_service
    )
    
    result = quote_api.request_quote(
        shipper_id, weight_kg, distance_km, declared_value
    )
    
    return result