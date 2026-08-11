"""
CargoQuote — Instant Freight Quotation System

A self-contained module implementing the cargo quote request flow:
validation, screening, pricing, storage, and notification.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ValidationError(Exception):
    """Raised when request validation fails."""
    pass


class StorageError(Exception):
    """Raised when quote store is unavailable."""
    pass


class ScreeningError(Exception):
    """Raised when screening service is unavailable."""
    pass


class QuoteStatus(Enum):
    """Quote lifecycle statuses."""
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


@dataclass
class Quote:
    """A stored quote record."""
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

    def __init__(self, risk_index: Optional[float] = None, available: bool = True):
        """
        Initialize screening service.
        
        Args:
            risk_index: Risk score to return (if None, will be set via handle's screening_result)
            available: Whether service is available
        """
        self.risk_index = risk_index
        self.available = available

    def screen(self, shipper_id: str) -> float:
        """
        Screen a shipper by ID.
        
        Returns:
            float: Risk index (0-100 scale where higher = riskier)
            
        Raises:
            ScreeningError: If service unavailable
        """
        if not self.available:
            raise ScreeningError("Screening service unavailable")
        if self.risk_index is None:
            raise ValueError("Risk index not configured")
        return self.risk_index


class TariffEngine:
    """Tariff engine for freight price computation."""

    def __init__(self, base_rate: float = 1.0):
        """
        Initialize tariff engine.
        
        Args:
            base_rate: Base rate per ton-km (default 1.0 for unit pricing)
        """
        self.base_rate = base_rate

    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Compute freight price from weight and distance.
        
        Args:
            weight_kg: Weight in kilograms
            distance_km: Distance in kilometers
            
        Returns:
            float: Price amount (currency units)
        """
        # Convert kg to metric tons
        weight_tonnes = weight_kg / 1000.0
        # Compute price: base_rate * tonnes * distance
        price = self.base_rate * weight_tonnes * distance_km
        # Round to 2 decimal places
        return round(price, 2)


class QuoteStore:
    """Quote storage (PostgreSQL backend)."""

    def __init__(self, available: bool = True):
        """
        Initialize quote store.
        
        Args:
            available: Whether storage is available
        """
        self.available = available
        self._quotes = {}
        self._next_id = 1

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """
        Store a draft quote.
        
        Args:
            shipper_id: ID of requesting shipper
            weight_kg: Cargo weight in kg
            distance_km: Distance in km
            declared_value: Declared cargo value
            
        Returns:
            str: Unique quote ID
            
        Raises:
            StorageError: If storage unavailable
        """
        if not self.available:
            raise StorageError("Quote store unavailable")

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
        self._quotes[quote_id] = quote
        return quote_id

    def update_quote(
        self,
        quote_id: str,
        status: QuoteStatus,
        price_amount: Optional[float] = None,
    ) -> Quote:
        """
        Update a quote's status and optionally its price.
        
        Args:
            quote_id: ID of quote to update
            status: New status
            price_amount: Price (if applicable)
            
        Returns:
            Quote: Updated quote object
            
        Raises:
            StorageError: If storage unavailable
        """
        if not self.available:
            raise StorageError("Quote store unavailable")

        if quote_id not in self._quotes:
            raise ValueError(f"Quote {quote_id} not found")

        quote = self._quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount

        return quote


class NotificationService:
    """External notification provider for quote documents and refusals."""

    def __init__(self, available: bool = True):
        """
        Initialize notification service.
        
        Args:
            available: Whether service is available
        """
        self.available = available
        self.sent_documents = []
        self.sent_refusals = []

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        """
        Send quote document to shipper (async fire-and-forget).
        
        Args:
            shipper_id: Recipient shipper ID
            quote_id: Quote ID
            price_amount: Quoted price
            
        Returns:
            str: Confirmation token (or error if service down, but error is ignored)
        """
        if not self.available:
            # Fire-and-forget: failure is silently logged and never changes response
            return "error"
        confirmation = f"DOC-{quote_id}-{shipper_id}"
        self.sent_documents.append((shipper_id, quote_id, price_amount))
        return confirmation

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """
        Send refusal notice to shipper (async fire-and-forget).
        
        Args:
            shipper_id: Recipient shipper ID
            quote_id: Quote ID
            
        Returns:
            str: Confirmation token (or error if service down, but error is ignored)
        """
        if not self.available:
            # Fire-and-forget: failure is silently logged and never changes response
            return "error"
        confirmation = f"REFUSAL-{quote_id}-{shipper_id}"
        self.sent_refusals.append((shipper_id, quote_id))
        return confirmation


class QuoteAPI:
    """Quote API: main orchestrator of the quotation flow."""

    # Screening decision thresholds (decision table DT-S)
    ACCEPT_MAX = 35
    REVIEW_MIN = 35
    REVIEW_MAX = 70
    REFUSE_MIN = 70

    def __init__(
        self,
        screening_service: ScreeningService,
        tariff_engine: TariffEngine,
        quote_store: QuoteStore,
        notification_service: NotificationService,
    ):
        """
        Initialize Quote API with collaborators.
        
        Args:
            screening_service: Denied-party screening provider
            tariff_engine: Pricing engine
            quote_store: Quote storage
            notification_service: Notification provider
        """
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service

    def _validate_request(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> None:
        """
        Validate quote request (decision table DT-V).
        
        Raises:
            ValidationError: If request is invalid
        """
        if not shipper_id:
            raise ValidationError("Shipper ID required")
        if weight_kg <= 0:
            raise ValidationError("Weight must be positive")
        if distance_km <= 0:
            raise ValidationError("Distance must be positive")
        if declared_value < 0:
            raise ValidationError("Declared value cannot be negative")

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        """
        Main entry point: process a quote request.
        
        Implements the full screening and pricing flow from behavior/quote_flow.yaml.
        
        Args:
            shipper_id: ID of requesting shipper
            weight_kg: Cargo weight in kilograms
            distance_km: Distance in kilometers
            declared_value: Declared cargo value
            
        Returns:
            dict: Response describing quotation outcome (status, quote_id, price, etc.)
        """
        # Step 1: Validate request (DT-V)
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": "rejected_invalid_request", "error": str(e)}

        # Step 2: Store draft (DT-S, note 3)
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageError as e:
            return {"status": "error", "error": f"storage_unavailable: {e}"}

        # Step 3: Screen shipper (DT-S)
        risk_index = None
        screening_failed = False
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError as e:
            # DT-S note 5: screening outage → price anyway, hold unscreened, no notify
            screening_failed = True

        # Step 4: Screening decision (DT-S rows)
        if screening_failed:
            # Screening unavailable: price, store on hold, no notification
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, QuoteStatus.HELD_UNSCREENED, price_amount
            )
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "message": "Quote held pending screening service recovery",
            }
        elif risk_index <= self.ACCEPT_MAX:
            # Row "accept": price, store quoted, send document, respond quoted
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
            # Fire-and-forget notification (DT-S note 4)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
                "message": f"Quote issued at {price_amount}",
            }
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Row "review": hold for manual review, no pricing, no notification (DT-S note 1)
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "message": "Quote held for compliance review",
            }
        elif risk_index >= self.REFUSE_MIN:
            # Row "refuse": refuse, store refused, send refusal, no pricing (DT-S note 2)
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            # Fire-and-forget notification (DT-S note 4 applies here too)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
                "message": "Quote declined due to screening",
            }

        # Should not reach here
        return {"status": "error", "error": "Unknown screening outcome"}


def handle(request: dict) -> dict:
    """
    End-to-end entry point: orchestrate a complete quote request flow.
    
    Input dict keys:
        shipper_id (str): Shipper identifier
        weight_kg (float): Weight in kilograms
        distance_km (float): Distance in kilometers
        declared_value (float): Declared cargo value
        
        Optional override keys (for testing):
        screening_available (bool): Whether screening service responds (default True)
        screening_result (float): Risk index to return from screening (default 20.0)
        storage_available (bool): Whether quote store responds (default True)
        notification_available (bool): Whether notification service responds (default True)
        tariff_base_rate (float): Base rate for pricing (default 1.0)
        
    Returns:
        dict: Quotation outcome with "status" key and optional details
              Statuses: "quoted", "review_hold", "refused_screening", "held_unscreened",
                       "rejected_invalid_request", "error"
    """
    # Extract request parameters
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)

    # Initialize collaborators with test overrides
    screening_available = request.get("screening_available", True)
    screening_result = request.get("screening_result", 20.0)
    storage_available = request.get("storage_available", True)
    notification_available = request.get("notification_available", True)
    tariff_base_rate = request.get("tariff_base_rate", 1.0)

    screening_service = ScreeningService(
        risk_index=screening_result,
        available=screening_available,
    )
    tariff_engine = TariffEngine(base_rate=tariff_base_rate)
    quote_store = QuoteStore(available=storage_available)
    notification_service = NotificationService(available=notification_available)

    # Instantiate API and run flow
    api = QuoteAPI(
        screening_service=screening_service,
        tariff_engine=tariff_engine,
        quote_store=quote_store,
        notification_service=notification_service,
    )

    response = api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    return response