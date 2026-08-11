"""
CargoQuote — Instant Freight Quotation System.

Single self-contained module implementing the quotation flow:
validation, screening, pricing, storage, and notification.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


# ============================================================================
# Enumerations and Constants
# ============================================================================

class QuoteStatus(Enum):
    """Quote lifecycle statuses."""
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


# Screening decision thresholds
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71


# Validation bounds (from DT-V)
MIN_WEIGHT_KG = 100
MAX_WEIGHT_KG = 30000
MIN_DISTANCE_KM = 10
MAX_DISTANCE_KM = 2000
MIN_DECLARED_VALUE = 100
MAX_DECLARED_VALUE = 500000


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class Quote:
    """Internal quote record."""
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price_amount: Optional[float] = None


# ============================================================================
# External Systems (Boundary)
# ============================================================================

class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str, screening_result: Optional[int] = None) -> int:
        """
        Screen a shipper and return a risk index.
        
        Args:
            shipper_id: The shipper to screen.
            screening_result: Override value for testing; if None, return 0.
        
        Returns:
            Risk index (0–100).
        """
        return screening_result if screening_result is not None else 0


class NotificationService:
    """External messaging provider."""

    def send_quote_document(
        self,
        shipper_id: str,
        quote_id: str,
        price_amount: float,
        notification_result: Optional[str] = None,
    ) -> str:
        """
        Send a quote document to the shipper (fire-and-forget).
        
        Args:
            shipper_id: The shipper receiving the quote.
            quote_id: The quote identifier.
            price_amount: The quoted price.
            notification_result: Override result for testing; if None, return "sent".
        
        Returns:
            Status string (e.g., "sent", "error").
        """
        return notification_result if notification_result is not None else "sent"

    def send_refusal_notice(
        self,
        shipper_id: str,
        quote_id: str,
        notification_result: Optional[str] = None,
    ) -> str:
        """
        Send a refusal notice to the shipper (fire-and-forget).
        
        Args:
            shipper_id: The shipper receiving the notice.
            quote_id: The quote identifier.
            notification_result: Override result for testing; if None, return "sent".
        
        Returns:
            Status string (e.g., "sent", "error").
        """
        return notification_result if notification_result is not None else "sent"


class TariffEngine:
    """Tariff computation engine."""

    def price(self, weight_kg: float, distance_km: float, price_result: Optional[float] = None) -> float:
        """
        Compute freight price from weight and distance.
        
        Args:
            weight_kg: Cargo weight in kilograms.
            distance_km: Distance in kilometers.
            price_result: Override price for testing; if None, compute from tariff.
        
        Returns:
            Price amount.
        """
        if price_result is not None:
            return price_result
        # Simple tariff: base + per-kg + per-km
        base = 50.0
        per_kg = 0.5
        per_km = 0.1
        return base + (weight_kg * per_kg) + (distance_km * per_km)


class QuoteStore:
    """Quote persistence layer."""

    def __init__(self):
        """Initialize in-memory quote storage."""
        self.quotes: dict[str, Quote] = {}
        self._next_id = 1

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
        store_result: Optional[str] = None,
    ) -> str:
        """
        Store a draft quote request.
        
        Args:
            shipper_id: The shipper identifier.
            weight_kg: Cargo weight.
            distance_km: Distance.
            declared_value: Declared cargo value.
            store_result: Override result for testing ("stored", "error", or None for success).
        
        Returns:
            Quote ID if successful.
        
        Raises:
            Exception: If store_result is "error".
        """
        if store_result == "error":
            raise Exception("store_unavailable_error")
        
        quote_id = f"Q{self._next_id:06d}"
        self._next_id += 1
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
        store_result: Optional[str] = None,
    ) -> Quote:
        """
        Update a quote's status and optionally price.
        
        Args:
            quote_id: The quote to update.
            status: New status.
            price_amount: New price (optional).
            store_result: Override result for testing.
        
        Returns:
            Updated quote.
        
        Raises:
            Exception: If store_result is "error".
        """
        if store_result == "error":
            raise Exception("store_unavailable_error")
        
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote


# ============================================================================
# Validation (Decision Table DT-V)
# ============================================================================

def validate_request(
    shipper_id: str,
    weight_kg: float,
    distance_km: float,
    declared_value: float,
) -> Optional[str]:
    """
    Validate a quote request against bounds.
    
    Args:
        shipper_id: The shipper identifier.
        weight_kg: Cargo weight in kg.
        distance_km: Distance in km.
        declared_value: Declared value in currency units.
    
    Returns:
        None if valid; error message if invalid.
    """
    if not shipper_id or shipper_id.strip() == "":
        return "shipper_id_missing"
    if weight_kg < MIN_WEIGHT_KG or weight_kg > MAX_WEIGHT_KG:
        return "weight_out_of_bounds"
    if distance_km < MIN_DISTANCE_KM or distance_km > MAX_DISTANCE_KM:
        return "distance_out_of_bounds"
    if declared_value < MIN_DECLARED_VALUE or declared_value > MAX_DECLARED_VALUE:
        return "declared_value_out_of_bounds"
    return None


# ============================================================================
# Quote API (Main Orchestrator)
# ============================================================================

class QuoteAPI:
    """Main quote request handler."""

    def __init__(
        self,
        quote_store: QuoteStore,
        screening_service: ScreeningService,
        tariff_engine: TariffEngine,
        notification_service: NotificationService,
    ):
        """
        Initialize the Quote API with collaborators.
        
        Args:
            quote_store: Persistence layer.
            screening_service: External screening provider.
            tariff_engine: Pricing engine.
            notification_service: External notification provider.
        """
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
        store_result: Optional[str] = None,
        screening_result: Optional[int] = None,
        price_result: Optional[float] = None,
        notification_result: Optional[str] = None,
    ) -> dict:
        """
        Process a quote request end-to-end.
        
        Orchestrates validation, storage, screening, pricing, and notification
        according to the quotation flow (behavior/quote_flow.mmd).
        
        Args:
            shipper_id: Shipper identifier.
            weight_kg: Cargo weight in kg.
            distance_km: Distance in km.
            declared_value: Declared cargo value.
            store_result: Test override for storage result.
            screening_result: Test override for screening risk index.
            price_result: Test override for computed price.
            notification_result: Test override for notification delivery.
        
        Returns:
            Dictionary with "status" key describing outcome.
        """
        # Step 1: Validate request (DT-V)
        validation_error = validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if validation_error:
            return {"status": f"rejected_invalid_request: {validation_error}"}

        # Step 2: Store draft quote
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value,
                store_result=store_result,
            )
        except Exception as e:
            return {"status": f"error: {str(e)}"}

        # Step 3: Screen shipper (DT-S)
        try:
            risk_index = self.screening_service.screen(shipper_id, screening_result=screening_result)
        except Exception as e:
            # Screening outage: price anyway, store on hold, no notification (DT-S note 5)
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km, price_result=price_result)
                self.quote_store.update_quote(
                    quote_id,
                    QuoteStatus.HELD_UNSCREENED,
                    price_amount=price_amount,
                    store_result=store_result,
                )
                return {"status": "held_unscreened"}
            except Exception as update_error:
                return {"status": f"error: {str(update_error)}"}

        # Step 4: Apply screening decision
        if risk_index <= ACCEPT_MAX:
            # Accept: price and quote (DT-S row accept)
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km, price_result=price_result)
                self.quote_store.update_quote(
                    quote_id,
                    QuoteStatus.QUOTED,
                    price_amount=price_amount,
                    store_result=store_result,
                )
                # Fire-and-forget notification (DT-S note 4)
                try:
                    self.notification_service.send_quote_document(
                        shipper_id, quote_id, price_amount,
                        notification_result=notification_result,
                    )
                except Exception:
                    # Notification failure does not change response
                    pass
                return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
            except Exception as e:
                return {"status": f"error: {str(e)}"}

        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # Review hold: do not price, do not notify (DT-S row review, note 1)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    QuoteStatus.REVIEW_HOLD,
                    store_result=store_result,
                )
                return {"status": "review_hold"}
            except Exception as e:
                return {"status": f"error: {str(e)}"}

        else:  # risk_index >= REFUSE_MIN
            # Refuse: do not price, notify refusal (DT-S row refuse, note 2)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    QuoteStatus.REFUSED_SCREENING,
                    store_result=store_result,
                )
                # Fire-and-forget notification (DT-S note 4)
                try:
                    self.notification_service.send_refusal_notice(
                        shipper_id, quote_id,
                        notification_result=notification_result,
                    )
                except Exception:
                    # Notification failure does not change response
                    pass
                return {"status": "refused_screening"}
            except Exception as e:
                return {"status": f"error: {str(e)}"}


# ============================================================================
# System Assembly and Public Handler
# ============================================================================

def handle(request: dict) -> dict:
    """
    Handle a quote request end-to-end.
    
    Assembles the system, processes the request with test overrides from the
    input dict, and returns the outcome.
    
    Args:
        request: Dictionary containing:
            - shipper_id: Shipper identifier (required)
            - weight_kg: Weight in kg (required)
            - distance_km: Distance in km (required)
            - declared_value: Declared value (required)
            - Optional test overrides:
              - store_result: "stored", "error", etc.
              - screening_result: Risk index (integer)
              - price_result: Price amount (float)
              - notification_result: "sent", "error", etc.
    
    Returns:
        Dictionary with "status" key and optional "quote_id" and "price".
    """
    # Assemble system components
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    quote_api = QuoteAPI(
        quote_store, screening_service, tariff_engine, notification_service
    )

    # Extract request parameters
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0.0)
    distance_km = request.get("distance_km", 0.0)
    declared_value = request.get("declared_value", 0.0)

    # Extract test overrides
    store_result = request.get("store_result")
    screening_result = request.get("screening_result")
    price_result = request.get("price_result")
    notification_result = request.get("notification_result")

    # Process the quote request
    return quote_api.request_quote(
        shipper_id=shipper_id,
        weight_kg=weight_kg,
        distance_km=distance_km,
        declared_value=declared_value,
        store_result=store_result,
        screening_result=screening_result,
        price_result=price_result,
        notification_result=notification_result,
    )