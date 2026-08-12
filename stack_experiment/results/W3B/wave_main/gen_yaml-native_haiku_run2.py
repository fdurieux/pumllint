import json
from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
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
    risk_index: Optional[float] = None


class ScreeningService:
    """External denied-party screening provider."""
    
    def __init__(self):
        self.screening_result = None
    
    def screen(self, shipper_id: str) -> float:
        """
        Returns a shipper risk index.
        Can be overridden by test via screening_result attribute.
        """
        if self.screening_result == "error":
            raise ScreeningError("Screening service unavailable")
        
        if isinstance(self.screening_result, (int, float)):
            return float(self.screening_result)
        
        return 0.0


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    def __init__(self):
        self.pricing_result = None
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Returns the freight price amount.
        Can be overridden by test via pricing_result attribute.
        """
        if self.pricing_result == "error":
            raise Exception("Pricing engine error")
        
        if isinstance(self.pricing_result, (int, float)):
            return float(self.pricing_result)
        
        base_rate = 50.0
        weight_factor = weight_kg * 0.5
        distance_factor = distance_km * 0.1
        return base_rate + weight_factor + distance_factor


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def __init__(self):
        self.notification_result = None
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        """Sends quote document. Returns confirmation."""
        if self.notification_result == "error":
            return "send_failed"
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Sends refusal notice. Returns confirmation."""
        if self.notification_result == "error":
            return "send_failed"
        return "sent"


class QuoteStore:
    """PostgreSQL-backed quote storage."""
    
    def __init__(self):
        self.quotes: dict[str, Quote] = {}
        self.quote_counter = 0
        self.store_result = None
    
    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float
    ) -> str:
        """Stores a draft quote. Returns quoteId."""
        if self.store_result == "error":
            raise StorageError("Quote store unavailable")
        
        self.quote_counter += 1
        quote_id = f"QUOTE-{self.quote_counter:06d}"
        
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
    
    def update_quote(
        self,
        quote_id: str,
        status: QuoteStatus,
        price_amount: Optional[float] = None
    ) -> Quote:
        """Updates quote status and optionally price. Returns updated quote."""
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        
        return quote


class QuoteAPI:
    """Main quotation API orchestrating the screening and pricing flow."""
    
    ACCEPT_MAX = 30.0
    REVIEW_MIN = 30.0
    REVIEW_MAX = 70.0
    REFUSE_MIN = 70.0
    
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
    ) -> bool:
        """Validates request bounds."""
        if not shipper_id or len(shipper_id) == 0:
            return False
        if weight_kg <= 0 or weight_kg > 100000:
            return False
        if distance_km <= 0 or distance_km > 10000:
            return False
        if declared_value < 0 or declared_value > 10000000:
            return False
        return True
    
    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float
    ) -> dict:
        """
        Main entry point: receives quote request and orchestrates the flow.
        Returns outcome dict with "status" key and outcome details.
        """
        
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {
                "status": "rejected",
                "reason": "invalid_request",
                "message": "Request validation failed"
            }
        
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageError as e:
            return {
                "status": "error",
                "reason": "store_unavailable",
                "message": str(e)
            }
        
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            risk_index = None
        
        if risk_index is not None:
            if risk_index <= self.ACCEPT_MAX:
                return self._handle_accept(quote_id, weight_kg, distance_km, shipper_id)
            elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
                return self._handle_review(quote_id)
            elif risk_index >= self.REFUSE_MIN:
                return self._handle_refuse(quote_id, shipper_id)
        
        else:
            return self._handle_screening_failure(quote_id, weight_kg, distance_km)
    
    def _handle_accept(
        self,
        quote_id: str,
        weight_kg: float,
        distance_km: float,
        shipper_id: str
    ) -> dict:
        """Handle accept path: price and notify."""
        price_amount = self.tariff_engine.price(weight_kg, distance_km)
        self.quote_store.update_quote(
            quote_id,
            QuoteStatus.QUOTED,
            price_amount
        )
        self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
        
        return {
            "status": "quoted",
            "quote_id": quote_id,
            "price": price_amount
        }
    
    def _handle_review(self, quote_id: str) -> dict:
        """Handle review path: hold for manual review."""
        self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
        
        return {
            "status": "review_hold",
            "quote_id": quote_id,
            "message": "Quote held for manual compliance review"
        }
    
    def _handle_refuse(self, quote_id: str, shipper_id: str) -> dict:
        """Handle refuse path: refuse and notify."""
        self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
        self.notification_service.send_refusal_notice(shipper_id, quote_id)
        
        return {
            "status": "refused",
            "quote_id": quote_id,
            "reason": "screening_failed"
        }
    
    def _handle_screening_failure(
        self,
        quote_id: str,
        weight_kg: float,
        distance_km: float
    ) -> dict:
        """Handle screening service outage: price but hold unscreened."""
        price_amount = self.tariff_engine.price(weight_kg, distance_km)
        self.quote_store.update_quote(
            quote_id,
            QuoteStatus.HELD_UNSCREENED,
            price_amount
        )
        
        return {
            "status": "held_unscreened",
            "quote_id": quote_id,
            "price": price_amount,
            "message": "Screening unavailable; quote priced and held pending screening"
        }


def handle(request: dict) -> dict:
    """
    End-to-end flow handler.
    
    request dict may contain:
      - shipper_id, weight_kg, distance_km, declared_value: request parameters
      - screening_service_result: mocked screening result (number or "error")
      - tariff_engine_result: mocked pricing result (number or "error")
      - quote_store_result: mocked storage result ("error" for failure, else normal)
      - notification_service_result: mocked notification result ("error" for failure, else normal)
    
    Returns dict with "status" key describing the outcome.
    """
    
    quote_store = QuoteStore()
    tariff_engine = TariffEngine()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    
    quote_store.store_result = request.get("quote_store_result")
    tariff_engine.pricing_result = request.get("tariff_engine_result")
    screening_service.screening_result = request.get("screening_service_result")
    notification_service.notification_result = request.get("notification_service_result")
    
    api = QuoteAPI(
        quote_store,
        tariff_engine,
        screening_service,
        notification_service
    )
    
    shipper_id = request.get("shipper_id", "SHIPPER-001")
    weight_kg = request.get("weight_kg", 1000.0)
    distance_km = request.get("distance_km", 500.0)
    declared_value = request.get("declared_value", 50000.0)
    
    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)