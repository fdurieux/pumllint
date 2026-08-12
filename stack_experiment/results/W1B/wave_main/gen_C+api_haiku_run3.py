import json
from typing import Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from abc import ABC, abstractmethod


class QuoteStatus(str, Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price: Optional[float] = None
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str) -> float:
        """
        Screen a shipper and return their risk index (0-100).
        In production, this calls an external REST API.
        """
        return 0.0


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Compute freight price in cents.
        Simple rule: base 1000 cents + 10 cents per kg + 5 cents per km.
        """
        return 1000 + (weight_kg * 10) + (distance_km * 5)


class QuoteStore:
    """Stores quote requests and their lifecycle."""
    
    def __init__(self):
        self._quotes = {}
        self._next_id = 1000
    
    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """Store a draft quote and return its quote_id."""
        quote_id = f"QT-{self._next_id}"
        self._next_id += 1
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT,
        )
        self._quotes[quote_id] = quote
        return quote_id
    
    def update_quote(
        self,
        quote_id: str,
        status: QuoteStatus,
        price: Optional[float] = None,
    ) -> Quote:
        """Update a quote's status and optionally its price."""
        if quote_id not in self._quotes:
            raise ValueError(f"Quote {quote_id} not found")
        quote = self._quotes[quote_id]
        quote.status = status
        if price is not None:
            quote.price = price
        return quote
    
    def get_quote(self, quote_id: str) -> Optional[Quote]:
        """Retrieve a quote by id."""
        return self._quotes.get(quote_id)


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def send_quote_document(
        self,
        shipper_id: str,
        quote_id: str,
        price: float,
    ) -> bool:
        """Send a quote document. Fire-and-forget; return success flag."""
        return True
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> bool:
        """Send a refusal notice. Fire-and-forget; return success flag."""
        return True


class QuoteAPI:
    """Main orchestration service for quote requests."""
    
    def __init__(
        self,
        quote_store: QuoteStore,
        screening_service: ScreeningService,
        tariff_engine: TariffEngine,
        notification_service: NotificationService,
    ):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service
    
    def _validate_request(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> bool:
        """Validate request against OpenAPI schema bounds (DT-V)."""
        if not shipper_id or len(shipper_id) < 1:
            return False
        if weight_kg < 3 or weight_kg > 19400:
            return False
        if distance_km < 25 or distance_km > 7150:
            return False
        if declared_value < 50 or declared_value > 83000:
            return False
        return True
    
    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        """
        Main quote request handler implementing the quotation flow (quote_flow.puml).
        Returns a dict with status and optional quote_id, price, hold.
        """
        
        # Validation (DT-V)
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {
                "status": "rejected: invalid_request",
            }
        
        # Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except Exception:
            return {
                "status": "error: store_unavailable",
            }
        
        # Screen (DT-S)
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception:
            risk_index = None
        
        # Decision tree based on screening outcome
        if risk_index is not None:
            if risk_index <= ACCEPT_MAX:
                # Accept path: price, store, notify
                price = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price)
                
                # Fire-and-forget notification
                try:
                    self.notification_service.send_quote_document(
                        shipper_id, quote_id, price
                    )
                except Exception:
                    pass
                
                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price": price,
                }
            
            elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
                # Review hold path: no pricing, no notification
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {
                    "status": "review_hold",
                    "quote_id": quote_id,
                }
            
            elif risk_index >= REFUSE_MIN:
                # Refuse path: no pricing, notify refusal
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
                
                # Fire-and-forget notification
                try:
                    self.notification_service.send_refusal_notice(shipper_id, quote_id)
                except Exception:
                    pass
                
                return {
                    "status": "refused_screening",
                    "quote_id": quote_id,
                }
        else:
            # Screening failure path: price, store on hold, no notification
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }


# Default instances
_quote_store = QuoteStore()
_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_notification_service = NotificationService()
_quote_api = QuoteAPI(
    _quote_store,
    _screening_service,
    _tariff_engine,
    _notification_service,
)


def handle(request: dict) -> dict:
    """
    End-to-end quote request handler.
    
    Supports request keys: shipper_id, weight_kg, distance_km, declared_value.
    Supports test-mode overrides via: screening_service_result (risk index),
    quote_store_result (stored, unavailable), notification_service_result (success, error).
    
    Returns dict with 'status' and optional 'quote_id', 'price', 'hold'.
    """
    global _quote_store, _screening_service, _tariff_engine, _notification_service, _quote_api
    
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)
    
    # Test mode: inject mock behaviors
    original_screening = _screening_service.screen
    original_store = _quote_store.store_draft
    original_notify_doc = _notification_service.send_quote_document
    original_notify_ref = _notification_service.send_refusal_notice
    
    try:
        if "screening_service_result" in request:
            result_val = request["screening_service_result"]
            if result_val == "error":
                _screening_service.screen = lambda sid: (_ for _ in ()).throw(
                    Exception("Screening unavailable")
                )
            else:
                risk_idx = float(result_val) if isinstance(result_val, (int, float)) else 0
                _screening_service.screen = lambda sid: risk_idx
        
        if request.get("quote_store_result") == "unavailable":
            _quote_store.store_draft = lambda *args: (_ for _ in ()).throw(
                Exception("Store unavailable")
            )
        
        if request.get("notification_service_result") == "error":
            _notification_service.send_quote_document = lambda *args: False
            _notification_service.send_refusal_notice = lambda *args: False
        
        response = _quote_api.request_quote(
            shipper_id, weight_kg, distance_km, declared_value
        )
        return response
    
    finally:
        _screening_service.screen = original_screening
        _quote_store.store_draft = original_store
        _notification_service.send_quote_document = original_notify_doc
        _notification_service.send_refusal_notice = original_notify_ref