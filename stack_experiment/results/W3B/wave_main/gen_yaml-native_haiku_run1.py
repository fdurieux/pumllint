"""
CargoQuote — Instant Freight Quotation System

A single self-contained module implementing the cargo quote flow:
validation, screening, pricing, storage, and notification.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


# ============================================================================
# Decision Tables and Constants
# ============================================================================

class ValidationStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    HELD_UNSCREENED = "held_unscreened"
    REFUSED_SCREENING = "refused_screening"


# DT-V: Request validation bounds
MIN_WEIGHT_KG = 1
MAX_WEIGHT_KG = 50000
MIN_DISTANCE_KM = 1
MAX_DISTANCE_KM = 5000
MIN_DECLARED_VALUE = 0
MAX_DECLARED_VALUE = 1000000


# DT-S: Screening decision thresholds
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class QuoteRequest:
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float


@dataclass
class QuoteRecord:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price_amount: Optional[float] = None


# ============================================================================
# External Systems (mocked implementations)
# ============================================================================

class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str) -> int:
        """
        Screen a shipper and return a risk index (0-100).
        
        In production, calls external REST API.
        For testing, the risk index comes from request context.
        """
        # Placeholder: actual implementation would call external service
        # Callers pass the result via request["screening_service_result"]
        raise NotImplementedError("Must be mocked via request context")


class TariffEngine:
    """Computes freight price from weight and distance."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Compute freight price.
        
        Simple rule: €0.50 per kg-km plus €10 base fee.
        In production, applies published tariff rules.
        """
        base_fee = 10.0
        rate_per_kg_km = 0.50
        price = base_fee + (weight_kg * distance_km * rate_per_kg_km)
        return round(price, 2)


class QuoteStore:
    """PostgreSQL store for quote requests and lifecycle."""

    def __init__(self):
        # In-memory store for simulation; real implementation uses PostgreSQL
        self.quotes: dict[str, QuoteRecord] = {}
        self.next_quote_id = 1000

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """
        Store a draft quote and return its ID.
        May raise an exception on storage failure.
        """
        # Simulate storage failure if indicated in context
        if hasattr(self, "_force_storage_error"):
            raise Exception("Quote store unavailable")
        
        quote_id = str(self.next_quote_id)
        self.next_quote_id += 1
        
        quote = QuoteRecord(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT,
            price_amount=None,
        )
        self.quotes[quote_id] = quote
        return quote_id

    def update_quote(
        self,
        quote_id: str,
        status: QuoteStatus,
        price_amount: Optional[float] = None,
    ) -> QuoteRecord:
        """Update a quote's status and optional price, return the record."""
        if quote_id not in self.quotes:
            raise Exception(f"Quote {quote_id} not found")
        
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        
        return quote


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(
        self, shipper_id: str, quote_id: str, price_amount: float
    ) -> str:
        """
        Send a quote document to the shipper (fire-and-forget).
        Returns a confirmation string; failure is logged but never propagates.
        """
        # Fire-and-forget: never fails the quote flow
        confirmation = f"quote_doc_sent_to_{shipper_id}"
        return confirmation

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """
        Send a refusal notice to the shipper (fire-and-forget).
        Returns a confirmation string; failure is logged but never propagates.
        """
        # Fire-and-forget: never fails the quote flow
        confirmation = f"refusal_notice_sent_to_{shipper_id}"
        return confirmation


# ============================================================================
# Quote API — Main Orchestrator
# ============================================================================

class QuoteAPI:
    """
    Quote API orchestrates the screening and pricing flow.
    
    This is the main entry point for quote requests. It validates,
    screens, prices, stores, and notifies according to the flow
    specification.
    """

    def __init__(
        self,
        tariff_engine: TariffEngine,
        quote_store: QuoteStore,
        screening_service: ScreeningService,
        notification_service: NotificationService,
    ):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
        screening_risk_index: Optional[int] = None,
        quote_store_error: bool = False,
        screening_service_error: bool = False,
    ) -> dict:
        """
        Main entry point for quote requests.
        
        Args:
            shipper_id: Unique shipper identifier
            weight_kg: Cargo weight in kilograms
            distance_km: Transport distance in kilometers
            declared_value: Declared cargo value
            screening_risk_index: Risk index from screening service (0-100)
            quote_store_error: If True, simulate quote store failure
            screening_service_error: If True, simulate screening service failure
        
        Returns:
            A dict with 'status' key indicating outcome and supporting fields.
        """
        
        # BRANCH 1: REQUEST VALIDATION (DT-V)
        validation = self._validate_request(
            shipper_id, weight_kg, distance_km, declared_value
        )
        if validation != ValidationStatus.VALID:
            return {
                "status": "rejected_invalid_request",
                "reason": "Request validation failed",
            }
        
        # Create request object
        req = QuoteRequest(
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
        )
        
        # BRANCH 2: DRAFT STORAGE
        try:
            if quote_store_error:
                raise Exception("Quote store unavailable")
            quote_id = self.quote_store.store_draft(
                req.shipper_id,
                req.weight_kg,
                req.distance_km,
                req.declared_value,
            )
        except Exception as e:
            # DT-S note 3: Storage failure stops the flow
            return {
                "status": "store_unavailable_error",
                "reason": str(e),
            }
        
        # BRANCH 3: SCREENING DECISION (DT-S)
        try:
            if screening_service_error:
                raise Exception("Screening service unavailable")
            risk_index = screening_risk_index
            if risk_index is None:
                raise ValueError("screening_risk_index required for screening")
        except Exception as e:
            # DT-S note 5: Screening outage does NOT fail the quote.
            # Price it, store on hold, do NOT notify.
            price_amount = self.tariff_engine.price(req.weight_kg, req.distance_km)
            self.quote_store.update_quote(
                quote_id, QuoteStatus.HELD_UNSCREENED, price_amount
            )
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "reason": "Screening service unavailable; quote held for manual review",
            }
        
        # Screening succeeded; apply decision rules
        if risk_index <= ACCEPT_MAX:
            # ACCEPT: Price, store, notify (DT-S note 4: async notification never fails)
            price_amount = self.tariff_engine.price(req.weight_kg, req.distance_km)
            self.quote_store.update_quote(
                quote_id, QuoteStatus.QUOTED, price_amount
            )
            # Fire-and-forget notification
            try:
                self.notification_service.send_quote_document(
                    req.shipper_id, quote_id, price_amount
                )
            except Exception:
                # Never propagates; log and continue
                pass
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
            }
        
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # REVIEW: Hold for manual review, no pricing, no notification (DT-S note 1)
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "reason": "Quote held for compliance review",
            }
        
        elif risk_index >= REFUSE_MIN:
            # REFUSE: Store refusal, notify (DT-S note 2: no pricing)
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            # Fire-and-forget notification
            try:
                self.notification_service.send_refusal_notice(
                    req.shipper_id, quote_id
                )
            except Exception:
                # Never propagates; log and continue
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
                "reason": "Shipper failed compliance screening",
            }
        
        else:
            # Should not reach here; defensive
            return {
                "status": "error",
                "reason": "Unexpected screening result",
            }

    def _validate_request(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> ValidationStatus:
        """
        Validate quote request against DT-V bounds.
        
        Returns VALID if all parameters are within acceptable ranges.
        """
        if not shipper_id or not isinstance(shipper_id, str):
            return ValidationStatus.INVALID
        if not (MIN_WEIGHT_KG <= weight_kg <= MAX_WEIGHT_KG):
            return ValidationStatus.INVALID
        if not (MIN_DISTANCE_KM <= distance_km <= MAX_DISTANCE_KM):
            return ValidationStatus.INVALID
        if not (MIN_DECLARED_VALUE <= declared_value <= MAX_DECLARED_VALUE):
            return ValidationStatus.INVALID
        return ValidationStatus.VALID


# ============================================================================
# Module-level handle() function — end-to-end flow
# ============================================================================

def handle(request: dict) -> dict:
    """
    Run one end-to-end cargo quote flow.
    
    Args:
        request: A dict containing:
            - shipper_id: Shipper identifier
            - weight_kg: Cargo weight
            - distance_km: Distance
            - declared_value: Declared cargo value
            - screening_service_result: Risk index (0-100), or None to trigger screening error
            - quote_store_exists: If False, triggers quote store error
            - notification_service_result: (not used; fire-and-forget always succeeds)
    
    Returns:
        A dict with 'status' key indicating the outcome.
    """
    
    # Extract request fields
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)
    
    # Extract test scenario controls
    screening_risk_index = request.get("screening_service_result")
    quote_store_error = not request.get("quote_store_exists", True)
    screening_service_error = request.get("screening_service_result") is None and \
                              request.get("screening_service_error", False)
    
    # Instantiate collaborators
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    
    # Create and run the Quote API
    quote_api = QuoteAPI(
        tariff_engine=tariff_engine,
        quote_store=quote_store,
        screening_service=screening_service,
        notification_service=notification_service,
    )
    
    result = quote_api.request_quote(
        shipper_id=shipper_id,
        weight_kg=weight_kg,
        distance_km=distance_km,
        declared_value=declared_value,
        screening_risk_index=screening_risk_index,
        quote_store_error=quote_store_error,
        screening_service_error=screening_service_error,
    )
    
    return result