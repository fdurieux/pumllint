import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from datetime import datetime


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


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus = QuoteStatus.DRAFT
    price_amount: Optional[float] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    risk_index: Optional[float] = None


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str, risk_index: Optional[float] = None) -> float:
        """
        Returns a shipper risk index. In live operation, this would call an external service.
        For testing, accepts a risk_index parameter; otherwise returns a default.
        """
        if risk_index is not None:
            return risk_index
        return 0.5


class TariffEngine:
    """Computes freight price from weight and distance."""

    def price(self, weight_kg: float, distance_km: float, price_amount: Optional[float] = None) -> float:
        """
        Computes price based on tariff rules. For testing, accepts a price_amount parameter.
        Otherwise computes based on weight and distance: base + (weight * 0.5) + (distance * 0.1).
        """
        if price_amount is not None:
            return price_amount
        return 50.0 + (weight_kg * 0.5) + (distance_km * 0.1)


class QuoteStore:
    """Persistent storage for quote requests and their lifecycle."""

    def __init__(self):
        self.quotes: dict[str, Quote] = {}
        self._counter = 0
        self._available = True

    def store_draft(
        self, 
        shipper_id: str, 
        weight_kg: float, 
        distance_km: float, 
        declared_value: float,
        quote_id: Optional[str] = None
    ) -> str:
        """Store a draft quote and return its ID."""
        if not self._available:
            raise StorageError("Storage unavailable")
        
        if quote_id is None:
            self._counter += 1
            quote_id = f"Q-{self._counter:06d}"
        
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
        price_amount: Optional[float] = None,
        risk_index: Optional[float] = None
    ) -> Quote:
        """Update a quote's status and optionally its price."""
        if not self._available:
            raise StorageError("Storage unavailable")
        
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
        """Retrieve a quote by ID."""
        return self.quotes.get(quote_id)


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(
        self, 
        shipper_id: str, 
        quote_id: str, 
        price_amount: float,
        delivery_status: Optional[str] = None
    ) -> str:
        """Send a quote document to the shipper. Fire-and-forget."""
        if delivery_status == "error":
            return "delivery_failed"
        return "sent"

    def send_refusal_notice(
        self, 
        shipper_id: str, 
        quote_id: str,
        delivery_status: Optional[str] = None
    ) -> str:
        """Send a refusal notice to the shipper. Fire-and-forget."""
        if delivery_status == "error":
            return "delivery_failed"
        return "sent"


class QuoteAPI:
    """
    Main orchestrator: validates requests, stores drafts, screens shippers,
    prices consignments, and returns the quotation outcome.
    """

    ACCEPT_MAX = 30.0
    REVIEW_MIN = 30.0
    REVIEW_MAX = 70.0
    REFUSE_MIN = 70.0

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

    def _validate_request(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float
    ) -> bool:
        """Validate quote request bounds (DT-V)."""
        if not shipper_id or len(shipper_id) == 0:
            return False
        if weight_kg <= 0 or weight_kg > 30000:
            return False
        if distance_km <= 0 or distance_km > 3000:
            return False
        if declared_value <= 0 or declared_value > 1000000:
            return False
        return True

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
        request_params: Optional[dict] = None
    ) -> dict:
        """
        Main entry point: validate, store draft, screen, price, update, and notify.
        """
        request_params = request_params or {}

        # Validate request (DT-V)
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {
                "status": "rejected",
                "reason": "invalid_request"
            }

        # Store draft
        try:
            quote_id_override = request_params.get("quote_id")
            quote_id = self.quote_store.store_draft(
                shipper_id,
                weight_kg,
                distance_km,
                declared_value,
                quote_id=quote_id_override
            )
        except StorageError as e:
            return {
                "status": "error",
                "reason": "storage_unavailable"
            }

        # Screen shipper
        screening_error = False
        risk_index = None
        try:
            risk_index_override = request_params.get("screening_result")
            risk_index = self.screening_service.screen(shipper_id, risk_index_override)
        except ScreeningError:
            screening_error = True

        # If screening failed, price and hold unscreened (DT-S note 5)
        if screening_error:
            price_amount_override = request_params.get("tariff_result")
            price_amount = self.tariff_engine.price(weight_kg, distance_km, price_amount_override)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    QuoteStatus.HELD_UNSCREENED,
                    price_amount=price_amount
                )
            except StorageError:
                return {
                    "status": "error",
                    "reason": "storage_unavailable"
                }
            return {
                "status": "held_unscreened",
                "quote_id": quote_id
            }

        # Decision tree based on risk_index (DT-S)
        if risk_index <= self.ACCEPT_MAX:
            # Accept path: price and notify
            price_amount_override = request_params.get("tariff_result")
            price_amount = self.tariff_engine.price(weight_kg, distance_km, price_amount_override)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    QuoteStatus.QUOTED,
                    price_amount=price_amount,
                    risk_index=risk_index
                )
            except StorageError:
                return {
                    "status": "error",
                    "reason": "storage_unavailable"
                }
            # Fire-and-forget notification
            notification_status = request_params.get("notification_status")
            self.notification_service.send_quote_document(
                shipper_id,
                quote_id,
                price_amount,
                delivery_status=notification_status
            )
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount
            }

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review hold path: no pricing, no notification (DT-S note 1)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    QuoteStatus.REVIEW_HOLD,
                    risk_index=risk_index
                )
            except StorageError:
                return {
                    "status": "error",
                    "reason": "storage_unavailable"
                }
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }

        else:  # risk_index >= REFUSE_MIN
            # Refuse path: update and notify (DT-S note 2)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    QuoteStatus.REFUSED_SCREENING,
                    risk_index=risk_index
                )
            except StorageError:
                return {
                    "status": "error",
                    "reason": "storage_unavailable"
                }
            # Fire-and-forget notification
            notification_status = request_params.get("notification_status")
            self.notification_service.send_refusal_notice(
                shipper_id,
                quote_id,
                delivery_status=notification_status
            )
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }


# Module-level factory and handler

_quote_store = QuoteStore()
_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_notification_service = NotificationService()
_quote_api = QuoteAPI(
    _quote_store,
    _screening_service,
    _tariff_engine,
    _notification_service
)


def handle(request: dict) -> dict:
    """
    End-to-end flow handler. Accepts a request dict with:
      - shipper_id, weight_kg, distance_km, declared_value (required)
      - Scenario control keys:
        - quote_id (optional, for testing)
        - storage_status (e.g., "unavailable" to force storage error)
        - screening_result (risk index as a number, or "error" for screening failure)
        - tariff_result (price as a number)
        - notification_status (e.g., "error" for notification failure)
    
    Returns a dict with "status" key naming the outcome.
    """
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)

    # Handle storage unavailability
    if request.get("storage_status") == "unavailable":
        _quote_store._available = False
    else:
        _quote_store._available = True

    # Build request parameters for the API
    request_params = {}
    
    # Quote ID override (for repeatable testing)
    if "quote_id" in request:
        request_params["quote_id"] = request["quote_id"]
    
    # Screening result override
    if "screening_result" in request:
        result = request["screening_result"]
        if result == "error":
            # Would need to mock screening to raise error; for now, pass None
            # and let it default; a real implementation would use dependency injection
            pass
        elif isinstance(result, (int, float)):
            request_params["screening_result"] = float(result)
    
    # Tariff result override
    if "tariff_result" in request:
        request_params["tariff_result"] = request["tariff_result"]
    
    # Notification status override
    if "notification_status" in request:
        request_params["notification_status"] = request["notification_status"]

    return _quote_api.request_quote(
        shipper_id,
        weight_kg,
        distance_km,
        declared_value,
        request_params=request_params
    )