from dataclasses import dataclass
from typing import Optional
from enum import Enum
import uuid


class ValidationError(Exception):
    pass


class StorageUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
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


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str) -> float:
        """
        Returns shipper risk index (0-100).
        In production, would call external API.
        """
        return 0.0


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Computes price based on tariff rules.
        Tariff: base 500 + (weight_kg * 0.5) + (distance_km * 1.2)
        """
        base = 500.0
        weight_component = weight_kg * 0.5
        distance_component = distance_km * 1.2
        total = base + weight_component + distance_component
        return round(total, 2)


class QuoteStore:
    """PostgreSQL-backed quote storage."""
    
    def __init__(self):
        self.quotes: dict[str, Quote] = {}
    
    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float
    ) -> str:
        """
        Stores a draft quote.
        Returns quote_id on success.
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
        self.quotes[quote_id] = quote
        return quote_id
    
    def update_quote(
        self,
        quote_id: str,
        status: QuoteStatus,
        price_amount: Optional[float] = None
    ) -> Quote:
        """
        Updates a quote's status and optionally its price.
        Returns the updated quote.
        """
        quote = self.quotes[quote_id]
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
        Fire-and-forget: returns "sent" or raises exception.
        In production, would call external API.
        """
        return "sent"
    
    def send_refusal_notice(
        self,
        shipper_id: str,
        quote_id: str
    ) -> str:
        """
        Sends refusal notice to shipper.
        Fire-and-forget: returns "sent" or raises exception.
        In production, would call external API.
        """
        return "sent"


class QuoteAPI:
    """
    Main orchestrator for quote requests.
    Validates requests, stores drafts, orchestrates screening and pricing,
    and returns outcomes.
    """
    
    # Screening decision thresholds (from decision table DT-S)
    ACCEPT_MAX = 25  # risk index <= 25: accept and quote
    REVIEW_MIN = 26  # 26 <= risk index <= 75: hold for review
    REVIEW_MAX = 75
    REFUSE_MIN = 76  # risk index >= 76: refuse
    
    # Validation bounds (from decision table DT-V)
    MIN_WEIGHT_KG = 10
    MAX_WEIGHT_KG = 5000
    MIN_DISTANCE_KM = 1
    MAX_DISTANCE_KM = 3000
    MIN_DECLARED_VALUE = 100
    MAX_DECLARED_VALUE = 500000
    
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
    ) -> None:
        """
        Validates request bounds per decision table DT-V.
        Raises ValidationError if invalid.
        """
        if not shipper_id or len(shipper_id.strip()) == 0:
            raise ValidationError("shipper_id required")
        
        if weight_kg < self.MIN_WEIGHT_KG or weight_kg > self.MAX_WEIGHT_KG:
            raise ValidationError(
                f"weight must be between {self.MIN_WEIGHT_KG} and {self.MAX_WEIGHT_KG} kg"
            )
        
        if distance_km < self.MIN_DISTANCE_KM or distance_km > self.MAX_DISTANCE_KM:
            raise ValidationError(
                f"distance must be between {self.MIN_DISTANCE_KM} and {self.MAX_DISTANCE_KM} km"
            )
        
        if declared_value < self.MIN_DECLARED_VALUE or declared_value > self.MAX_DECLARED_VALUE:
            raise ValidationError(
                f"declared value must be between {self.MIN_DECLARED_VALUE} and {self.MAX_DECLARED_VALUE}"
            )
    
    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float
    ) -> dict:
        """
        Main entry point for quote requests.
        Returns a response dict with "status" and optional "price", "hold" keys.
        """
        # Validate request (DT-V)
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {
                "status": "rejected: invalid_request",
                "reason": str(e)
            }
        
        # Store draft (DT-S)
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageUnavailableError:
            return {
                "status": "error: store_unavailable"
            }
        
        # Screen shipper
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage: price but hold unscreened
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.HELD_UNSCREENED,
                price_amount
            )
            return {
                "status": "held_unscreened",
                "price": price_amount,
                "hold": True
            }
        
        # Decision based on risk index (DT-S)
        if risk_index <= self.ACCEPT_MAX:
            # Accept: price and quote
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.QUOTED,
                price_amount
            )
            # Fire-and-forget notification
            try:
                self.notification_service.send_quote_document(
                    shipper_id, quote_id, price_amount
                )
            except Exception:
                # Notification failure does not change outcome (DT-S note 4)
                pass
            
            return {
                "status": "quoted",
                "price": price_amount
            }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review hold: no pricing, no notification
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.REVIEW_HOLD
            )
            return {
                "status": "review_hold"
            }
        
        else:  # risk_index >= REFUSE_MIN
            # Refuse: notify but do not price
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.REFUSED_SCREENING
            )
            # Fire-and-forget notification
            try:
                self.notification_service.send_refusal_notice(
                    shipper_id, quote_id
                )
            except Exception:
                # Notification failure noted but quote is still refused
                pass
            
            return {
                "status": "refused_screening"
            }


def handle(request: dict) -> dict:
    """
    End-to-end quote request handler.
    
    request keys:
      - shipper_id: string
      - weight_kg: float
      - distance_km: float
      - declared_value: float
      - screening_result: optional risk index (default 0 if not provided)
      - screening_status: optional "unavailable" to simulate outage
      - store_status: optional "unavailable" to simulate storage failure
      - notification_status: optional "failed" to simulate delivery failure
    
    Returns:
      dict with "status" and optional "price", "hold" keys
    """
    
    # Initialize collaborators
    quote_store = QuoteStore()
    
    # Wrap screening service with test injection
    screening_service = ScreeningService()
    original_screen = screening_service.screen
    def mock_screen(shipper_id: str) -> float:
        if request.get("screening_status") == "unavailable":
            raise ScreeningUnavailableError("Service unavailable")
        return float(request.get("screening_result", 0.0))
    screening_service.screen = mock_screen
    
    # Wrap store with test injection
    original_store_draft = quote_store.store_draft
    def mock_store_draft(shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if request.get("store_status") == "unavailable":
            raise StorageUnavailableError("Store unavailable")
        return original_store_draft(shipper_id, weight_kg, distance_km, declared_value)
    quote_store.store_draft = mock_store_draft
    
    # Wrap notification service with test injection
    notification_service = NotificationService()
    original_send_quote = notification_service.send_quote_document
    original_send_refusal = notification_service.send_refusal_notice
    def mock_send_quote(shipper_id: str, quote_id: str, price_amount: float) -> str:
        if request.get("notification_status") == "failed":
            raise Exception("Notification delivery failed")
        return original_send_quote(shipper_id, quote_id, price_amount)
    def mock_send_refusal(shipper_id: str, quote_id: str) -> str:
        if request.get("notification_status") == "failed":
            raise Exception("Notification delivery failed")
        return original_send_refusal(shipper_id, quote_id)
    notification_service.send_quote_document = mock_send_quote
    notification_service.send_refusal_notice = mock_send_refusal
    
    tariff_engine = TariffEngine()
    
    api = QuoteAPI(
        quote_store,
        screening_service,
        tariff_engine,
        notification_service
    )
    
    return api.request_quote(
        request.get("shipper_id", ""),
        request.get("weight_kg", 0.0),
        request.get("distance_km", 0.0),
        request.get("declared_value", 0.0)
    )