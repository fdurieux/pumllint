"""
CargoQuote — Instant Freight Quotation System

A synchronous quotation system that validates cargo requests, screens shippers,
prices consignments, and returns outcomes with optional notification delivery.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ============================================================================
# Enums and Constants
# ============================================================================

class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


class ValidationError(Exception):
    """Raised when request validation fails."""
    pass


class StorageError(Exception):
    """Raised when quote store is unavailable."""
    pass


class ScreeningError(Exception):
    """Raised when screening service is unavailable."""
    pass


# Decision table bounds (DT-S)
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71


# Validation bounds (DT-V)
MIN_WEIGHT_KG = 1
MAX_WEIGHT_KG = 10000
MIN_DISTANCE_KM = 1
MAX_DISTANCE_KM = 5000
MIN_DECLARED_VALUE = 100
MAX_DECLARED_VALUE = 1000000


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price_amount: Optional[float] = None
    risk_index: Optional[int] = None


# ============================================================================
# External Systems (Outside Boundary)
# ============================================================================

class ScreeningService:
    """External denied-party screening provider."""

    def __init__(self):
        self.available = True
        self.risk_index = 25

    def screen(self, shipper_id: str) -> int:
        """
        Returns the shipper's risk index.
        
        Raises ScreeningError if service is unavailable.
        """
        if not self.available:
            raise ScreeningError("Screening service unavailable")
        return self.risk_index


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def __init__(self):
        self.available = True

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        """
        Fire-and-forget delivery of quote document.
        Returns confirmation string (never fails the quote flow).
        """
        if not self.available:
            # Per spec: notification failure is provider's retry problem
            return "notification_pending"
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """
        Fire-and-forget delivery of refusal notice.
        Returns confirmation string (never fails the quote flow).
        """
        if not self.available:
            return "notification_pending"
        return "sent"


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules."""

    def __init__(self):
        # Simple tariff: base 50, 0.5 per kg, 2 per km
        self.base_rate = 50.0
        self.rate_per_kg = 0.5
        self.rate_per_km = 2.0

    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Returns the computed freight price.
        """
        return self.base_rate + (weight_kg * self.rate_per_kg) + (distance_km * self.rate_per_km)


# ============================================================================
# Internal Systems (Within Boundary)
# ============================================================================

class QuoteStore:
    """PostgreSQL-backed quote store for persisting quote requests and lifecycle."""

    def __init__(self):
        self.available = True
        self.quotes = {}
        self._counter = 0

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """
        Stores a draft quote and returns its quoteId.
        
        Raises StorageError if store is unavailable.
        """
        if not self.available:
            raise StorageError("Quote store unavailable")

        self._counter += 1
        quote_id = f"Q-{self._counter:06d}"
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT,
        )
        self.quotes[quote_id] = quote
        return quote_id

    def update_quote(
        self,
        quote_id: str,
        status: QuoteStatus,
        price_amount: Optional[float] = None,
    ) -> Quote:
        """
        Updates a quote with new status and optional price.
        Returns the updated quote.
        """
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")

        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote


class QuoteAPI:
    """
    Main orchestrator: receives quote requests, validates them, orchestrates
    screening and pricing, and returns outcomes.
    """

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

    def validate_request(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> bool:
        """
        Validates request according to DT-V bounds.
        
        Raises ValidationError if invalid.
        """
        if not shipper_id:
            raise ValidationError("Missing shipper_id")

        if weight_kg < MIN_WEIGHT_KG or weight_kg > MAX_WEIGHT_KG:
            raise ValidationError(
                f"weight_kg out of bounds [{MIN_WEIGHT_KG}, {MAX_WEIGHT_KG}]"
            )

        if distance_km < MIN_DISTANCE_KM or distance_km > MAX_DISTANCE_KM:
            raise ValidationError(
                f"distance_km out of bounds [{MIN_DISTANCE_KM}, {MAX_DISTANCE_KM}]"
            )

        if (
            declared_value < MIN_DECLARED_VALUE
            or declared_value > MAX_DECLARED_VALUE
        ):
            raise ValidationError(
                f"declared_value out of bounds [{MIN_DECLARED_VALUE}, {MAX_DECLARED_VALUE}]"
            )

        return True

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        """
        Main quotation flow orchestrator.
        
        Returns a dict with status and outcome details.
        """

        # Step 1: Request validation (DT-V)
        try:
            self.validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {
                "status": "rejected_invalid_request",
                "reason": str(e),
            }

        # Step 2: Draft storage
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageError as e:
            return {
                "status": "error",
                "reason": f"store_unavailable: {e}",
            }

        # Step 3: Screening (DT-S)
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError as e:
            # Screening outage: price and hold unscreened (DT-S note 5)
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id,
                    QuoteStatus.HELD_UNSCREENED,
                    price_amount,
                )
                return {
                    "status": "held_unscreened",
                    "quote_id": quote_id,
                    "price_amount": price_amount,
                    "reason": "screening_unavailable",
                }
            except Exception as storage_error:
                return {
                    "status": "error",
                    "reason": f"screening and storage error: {storage_error}",
                }

        # Step 4: Screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            # Accept: price, store, notify (DT-S note 1)
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.QUOTED,
                price_amount,
            )
            # Fire-and-forget notification (DT-S note 4)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount
            )
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price_amount": price_amount,
            }

        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # Review: hold for manual review, no pricing, no notification (DT-S note 1)
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.REVIEW_HOLD,
            )
            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "reason": "high_risk_screening",
            }

        else:  # risk_index >= REFUSE_MIN
            # Refuse: store refusal, notify (DT-S note 2)
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.REFUSED_SCREENING,
            )
            # Fire-and-forget notification
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
                "reason": "shipper_risk_too_high",
            }


# ============================================================================
# Module-level handler function
# ============================================================================

def handle(request: dict) -> dict:
    """
    Runs one end-to-end quotation flow.
    
    request keys:
        - shipper_id: str
        - weight_kg: float
        - distance_km: float
        - declared_value: float
        - screening_service_available: bool (optional, default True)
        - screening_result: int (optional, default 25 for risk index)
        - notification_service_available: bool (optional, default True)
        - quote_store_available: bool (optional, default True)
    
    Returns a dict with:
        - status: str (e.g. "quoted", "rejected_invalid_request", "error", etc.)
        - Additional fields depending on outcome
    """

    # Extract request parameters
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)

    # Configure external services based on request flags
    screening_service = ScreeningService()
    screening_service.available = request.get("screening_service_available", True)
    if "screening_result" in request:
        screening_service.risk_index = request["screening_result"]

    notification_service = NotificationService()
    notification_service.available = request.get(
        "notification_service_available", True
    )

    quote_store = QuoteStore()
    quote_store.available = request.get("quote_store_available", True)

    tariff_engine = TariffEngine()

    # Instantiate API and run flow
    api = QuoteAPI(
        quote_store=quote_store,
        screening_service=screening_service,
        tariff_engine=tariff_engine,
        notification_service=notification_service,
    )

    result = api.request_quote(
        shipper_id=shipper_id,
        weight_kg=weight_kg,
        distance_km=distance_km,
        declared_value=declared_value,
    )

    return result


if __name__ == "__main__":
    # Example usage
    result = handle({
        "shipper_id": "SHIP-001",
        "weight_kg": 500,
        "distance_km": 300,
        "declared_value": 50000,
    })
    print(result)