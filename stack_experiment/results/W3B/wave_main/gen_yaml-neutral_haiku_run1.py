import json
from enum import Enum
from typing import Optional
from dataclasses import dataclass


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


class NotificationError(Exception):
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
        """Returns a shipper risk index (0-100 or higher)."""
        return 25.0


class TariffEngine:
    """Computes freight price from weight and distance."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Returns price amount based on tariff rules."""
        base_rate = 0.5
        distance_rate = 0.01
        return (weight_kg * base_rate) + (distance_km * distance_rate)


class QuoteStore:
    """PostgreSQL-backed quote storage."""

    def __init__(self):
        self.quotes = {}
        self._next_id = 1000

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """Stores a draft quote and returns quote ID."""
        quote_id = f"Q{self._next_id}"
        self._next_id += 1
        self.quotes[quote_id] = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT,
        )
        return quote_id

    def update_quote(
        self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None
    ) -> Quote:
        """Updates quote status and optionally price, returns updated quote."""
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
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
        """Fire-and-forget send of quote document. Returns confirmation."""
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Fire-and-forget send of refusal notice. Returns confirmation."""
        return "sent"


class QuoteAPI:
    """Main quotation orchestration service."""

    # Screening decision thresholds
    ACCEPT_MAX = 30.0
    REVIEW_MIN = 31.0
    REVIEW_MAX = 70.0
    REFUSE_MIN = 71.0

    # Validation bounds
    MIN_WEIGHT_KG = 100.0
    MAX_WEIGHT_KG = 30000.0
    MIN_DISTANCE_KM = 1.0
    MAX_DISTANCE_KM = 5000.0
    MIN_DECLARED_VALUE = 100.0
    MAX_DECLARED_VALUE = 1000000.0

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

    def _validate_request(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> None:
        """Validates request against bounds. Raises ValidationError if invalid."""
        if not shipper_id or not isinstance(shipper_id, str):
            raise ValidationError("Invalid shipper_id")
        if not (self.MIN_WEIGHT_KG <= weight_kg <= self.MAX_WEIGHT_KG):
            raise ValidationError(
                f"Weight must be between {self.MIN_WEIGHT_KG} and {self.MAX_WEIGHT_KG} kg"
            )
        if not (self.MIN_DISTANCE_KM <= distance_km <= self.MAX_DISTANCE_KM):
            raise ValidationError(
                f"Distance must be between {self.MIN_DISTANCE_KM} and {self.MAX_DISTANCE_KM} km"
            )
        if not (
            self.MIN_DECLARED_VALUE <= declared_value <= self.MAX_DECLARED_VALUE
        ):
            raise ValidationError(
                f"Declared value must be between {self.MIN_DECLARED_VALUE} and {self.MAX_DECLARED_VALUE}"
            )

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        """Main entry point for quote requests. Returns outcome dict."""
        # Step 1: Validate request
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {
                "status": "rejected",
                "reason": f"invalid_request: {str(e)}",
            }

        # Step 2: Store draft quote
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageError as e:
            return {
                "status": "error",
                "reason": f"storage_unavailable: {str(e)}",
            }

        # Step 3: Screen shipper
        risk_index = None
        screening_failed = False
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            screening_failed = True

        # Step 4: Screening decision or fallback
        if screening_failed:
            # Screening outage: price, hold unscreened, don't notify
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.HELD_UNSCREENED, price_amount
                )
                return {
                    "status": "held_unscreened",
                    "quote_id": quote_id,
                    "reason": "screening_unavailable",
                }
            except Exception as e:
                return {
                    "status": "error",
                    "reason": f"pricing_failed: {str(e)}",
                }

        # Normal screening result
        if risk_index <= self.ACCEPT_MAX:
            # Accept: price, store quoted, notify
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.QUOTED, price_amount
                )
                # Fire-and-forget notification
                try:
                    self.notification_service.send_quote_document(
                        shipper_id, quote_id, price_amount
                    )
                except NotificationError:
                    pass
                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price": price_amount,
                }
            except Exception as e:
                return {
                    "status": "error",
                    "reason": f"pricing_failed: {str(e)}",
                }

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review hold: no pricing, no notification
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {
                    "status": "review_hold",
                    "quote_id": quote_id,
                    "reason": "manual_review_required",
                }
            except Exception as e:
                return {
                    "status": "error",
                    "reason": f"storage_failed: {str(e)}",
                }

        elif risk_index >= self.REFUSE_MIN:
            # Refuse: store refused, notify
            try:
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.REFUSED_SCREENING
                )
                # Fire-and-forget notification
                try:
                    self.notification_service.send_refusal_notice(
                        shipper_id, quote_id
                    )
                except NotificationError:
                    pass
                return {
                    "status": "refused",
                    "quote_id": quote_id,
                    "reason": "screening_failed",
                }
            except Exception as e:
                return {
                    "status": "error",
                    "reason": f"storage_failed: {str(e)}",
                }

        return {
            "status": "error",
            "reason": "unknown_screening_outcome",
        }


def handle(request: dict) -> dict:
    """
    End-to-end flow handler.
    
    request keys:
      - shipper_id: str
      - weight_kg: float
      - distance_km: float
      - declared_value: float
      - screening_result: float (risk index, optional override)
      - tariff_result: float (price, optional override)
      - store_result: str (status, optional override)
      - notification_result: str (status, optional override)
    """
    
    # Extract request parameters
    shipper_id = request.get("shipper_id", "S001")
    weight_kg = request.get("weight_kg", 500.0)
    distance_km = request.get("distance_km", 100.0)
    declared_value = request.get("declared_value", 10000.0)
    
    # Create services with optional mocking/overrides
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    
    # Override screening result if provided
    if "screening_result" in request:
        original_screen = screening_service.screen
        def mock_screen(sid):
            return request["screening_result"]
        screening_service.screen = mock_screen
    
    # Override tariff result if provided
    if "tariff_result" in request:
        original_price = tariff_engine.price
        def mock_price(w, d):
            return request["tariff_result"]
        tariff_engine.price = mock_price
    
    # Override store result if provided
    if "store_result" in request and request["store_result"] == "error":
        original_store = quote_store.store_draft
        def mock_store(*args, **kwargs):
            raise StorageError("Storage unavailable")
        quote_store.store_draft = mock_store
    
    # Override notification result if provided
    if "notification_result" in request and request["notification_result"] == "error":
        original_send_quote = notification_service.send_quote_document
        original_send_refusal = notification_service.send_refusal_notice
        def mock_send_quote(*args, **kwargs):
            raise NotificationError("Notification failed")
        def mock_send_refusal(*args, **kwargs):
            raise NotificationError("Notification failed")
        notification_service.send_quote_document = mock_send_quote
        notification_service.send_refusal_notice = mock_send_refusal
    
    # Create API and process request
    api = QuoteAPI(tariff_engine, quote_store, screening_service, notification_service)
    result = api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    
    return result