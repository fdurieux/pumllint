from dataclasses import dataclass
from typing import Optional
from enum import Enum
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


class StorageUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
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
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str) -> float:
        """
        Returns a risk index score.
        In production, this calls external API.
        """
        return 0.0


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Returns price amount based on tariff rules.
        Simple implementation: base rate + weight surcharge + distance rate.
        """
        base_rate = 50.0
        weight_rate = 0.5
        distance_rate = 0.1
        return base_rate + (weight_kg * weight_rate) + (distance_km * distance_rate)


class QuoteStore:
    """PostgreSQL-backed quote storage."""
    
    def __init__(self):
        self._quotes = {}
    
    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float
    ) -> str:
        """
        Stores a draft quote and returns quote ID.
        Raises StorageUnavailableError on failure.
        """
        quote_id = str(uuid.uuid4())
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT
        )
        self._quotes[quote_id] = quote
        return quote_id
    
    def update_quote(
        self,
        quote_id: str,
        status: QuoteStatus,
        price_amount: Optional[float] = None
    ) -> Quote:
        """
        Updates quote status and optionally price.
        Returns the updated quote.
        """
        quote = self._quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote


class NotificationService:
    """External messaging provider."""
    
    def send_quote_document(
        self,
        shipper_id: str,
        quote_id: str,
        price_amount: float
    ) -> str:
        """
        Sends quote document to shipper.
        Fire-and-forget; always succeeds from caller's perspective.
        Returns confirmation string.
        """
        return "quote_document_sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """
        Sends refusal notice to shipper.
        Fire-and-forget; always succeeds from caller's perspective.
        Returns confirmation string.
        """
        return "refusal_notice_sent"


class QuoteAPI:
    """
    Main orchestrator for quote requests.
    Validates, screens, prices, and stores quotes.
    """
    
    ACCEPT_MAX = 0.3
    REVIEW_MIN = 0.3
    REVIEW_MAX = 0.7
    REFUSE_MIN = 0.7
    
    def __init__(
        self,
        quote_store: QuoteStore,
        tariff_engine: TariffEngine,
        screening_service: ScreeningService,
        notification_service: NotificationService
    ):
        self.quote_store = quote_store
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service
    
    def _validate_request(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float
    ) -> None:
        """
        Validates request against bounds (decision table DT-V).
        Raises ValidationError if invalid.
        """
        if not shipper_id or shipper_id.strip() == "":
            raise ValidationError("shipper_id is required")
        if weight_kg <= 0:
            raise ValidationError("weight_kg must be positive")
        if distance_km <= 0:
            raise ValidationError("distance_km must be positive")
        if declared_value < 0:
            raise ValidationError("declared_value cannot be negative")
    
    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float
    ) -> dict:
        """
        Main quote request handler.
        Orchestrates validation, screening, pricing, storage, and notification.
        """
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {
                "status": "rejected",
                "reason": f"validation_error: {str(e)}"
            }
        
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id,
                weight_kg,
                distance_km,
                declared_value
            )
        except StorageUnavailableError:
            return {
                "status": "error",
                "reason": "quote_store_unavailable"
            }
        
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            risk_index = None
        
        if risk_index is None:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.HELD_UNSCREENED,
                price_amount
            )
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "reason": "screening_unavailable"
            }
        elif risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.QUOTED,
                price_amount
            )
            self.notification_service.send_quote_document(
                shipper_id,
                quote_id,
                price_amount
            )
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price_amount": price_amount
            }
        elif risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.REVIEW_HOLD
            )
            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "reason": "screening_review_required"
            }
        else:
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.REFUSED_SCREENING
            )
            self.notification_service.send_refusal_notice(
                shipper_id,
                quote_id
            )
            return {
                "status": "refused",
                "quote_id": quote_id,
                "reason": "screening_failed"
            }


def handle(request: dict) -> dict:
    """
    End-to-end handler for quote requests.
    Takes request dict and returns outcome dict.
    """
    quote_store = QuoteStore()
    tariff_engine = TariffEngine()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    
    quote_api = QuoteAPI(
        quote_store,
        tariff_engine,
        screening_service,
        notification_service
    )
    
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg", 0.0)
    distance_km = request.get("distance_km", 0.0)
    declared_value = request.get("declared_value", 0.0)
    
    if "screening_service_result" in request:
        screening_result = request["screening_service_result"]
        original_screen = screening_service.screen
        
        if screening_result == "error":
            screening_service.screen = lambda shipper_id: (_ for _ in ()).throw(
                ScreeningUnavailableError("screening service unavailable")
            )
        else:
            try:
                risk_index = float(screening_result)
                screening_service.screen = lambda shipper_id: risk_index
            except (ValueError, TypeError):
                pass
    
    if "quote_store_exists" in request and not request["quote_store_exists"]:
        def failing_store_draft(*args, **kwargs):
            raise StorageUnavailableError("quote store unavailable")
        quote_store.store_draft = failing_store_draft
    
    return quote_api.request_quote(
        shipper_id,
        weight_kg,
        distance_km,
        declared_value
    )