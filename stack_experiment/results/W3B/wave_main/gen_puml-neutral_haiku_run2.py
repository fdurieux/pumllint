from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime


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
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow().isoformat()


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str) -> float:
        """
        Returns shipper risk index (0-100).
        In test/mock mode, can be controlled via request['screening_result'].
        """
        return 0.0


class TariffEngine:
    """Computes freight price from weight and distance."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Returns price amount.
        In test/mock mode, can be controlled via request['tariff_result'].
        """
        base_rate = 0.5
        weight_charge = weight_kg * 0.1
        distance_charge = distance_km * base_rate
        return weight_charge + distance_charge


class QuoteStore:
    """PostgreSQL-backed quote store."""

    def __init__(self):
        self.quotes = {}
        self.next_id = 1

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        """Stores a draft quote. Returns quoteId."""
        quote_id = f"QT-{self.next_id:06d}"
        self.next_id += 1
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

    def update_quote(self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None) -> Quote:
        """Updates quote status and optionally price. Returns updated quote."""
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        quote.updated_at = datetime.utcnow().isoformat()
        return quote


class NotificationService:
    """External messaging provider."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        """
        Sends quote document. Fire-and-forget; returns confirmation.
        In test/mock mode, can be controlled via request['notification_result'].
        """
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """
        Sends refusal notice. Fire-and-forget; returns confirmation.
        In test/mock mode, can be controlled via request['notification_result'].
        """
        return "sent"


class QuoteAPI:
    """Main orchestrator for quote requests."""

    ACCEPT_MAX = 20.0
    REVIEW_MIN = 20.0
    REVIEW_MAX = 79.0
    REFUSE_MIN = 80.0

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
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> None:
        """Validates request bounds per DT-V."""
        if not shipper_id or shipper_id.strip() == "":
            raise ValidationError("shipper_id is required")
        if weight_kg <= 0 or weight_kg > 100000:
            raise ValidationError("weight_kg must be between 0 and 100000")
        if distance_km <= 0 or distance_km > 5000:
            raise ValidationError("distance_km must be between 0 and 5000")
        if declared_value < 0 or declared_value > 1000000:
            raise ValidationError("declared_value must be between 0 and 1000000")

    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        """
        Main quote request handler. Returns a dict with status and details.
        """
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": "rejected_invalid_request", "reason": str(e)}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError as e:
            return {"status": "store_unavailable_error", "reason": str(e)}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError as e:
            risk_index = None

        if risk_index is None:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
            return {
                "status": "held_unscreened_response",
                "quote_id": quote_id,
                "reason": "screening unavailable",
            }

        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted_response",
                "quote_id": quote_id,
                "price_amount": price_amount,
            }

        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {
                "status": "review_hold_response",
                "quote_id": quote_id,
                "reason": "held for compliance review",
            }

        if risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening_response",
                "quote_id": quote_id,
                "reason": "failed screening",
            }

        return {"status": "error", "reason": "unexpected state"}


class MockScreeningService(ScreeningService):
    """Mock screening service for testing."""

    def __init__(self, result: Optional[float] = None):
        self.result = result if result is not None else 0.0

    def screen(self, shipper_id: str) -> float:
        if self.result == "error":
            raise ScreeningError("screening unavailable")
        return float(self.result)


class MockTariffEngine(TariffEngine):
    """Mock tariff engine for testing."""

    def __init__(self, result: Optional[float] = None):
        self.result = result if result is not None else 100.0

    def price(self, weight_kg: float, distance_km: float) -> float:
        if self.result == "error":
            raise Exception("tariff computation failed")
        return float(self.result)


class MockNotificationService(NotificationService):
    """Mock notification service for testing."""

    def __init__(self, result: Optional[str] = None):
        self.result = result if result is not None else "sent"

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        if self.result == "error":
            return "delivery_failed"
        return self.result

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if self.result == "error":
            return "delivery_failed"
        return self.result


def handle(request: dict) -> dict:
    """
    End-to-end quote request handler.
    
    Input keys:
      - shipper_id: str
      - weight_kg: float
      - distance_km: float
      - declared_value: float
      - shipper_exists: bool (optional, for validation)
      - screening_result: float or "error" (optional, mock override)
      - tariff_result: float or "error" (optional, mock override)
      - notification_result: str (optional, mock override)
    
    Returns: dict with "status" key and supporting fields.
    """
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0.0)
    distance_km = request.get("distance_km", 0.0)
    declared_value = request.get("declared_value", 0.0)

    quote_store = QuoteStore()

    screening_result = request.get("screening_result")
    if screening_result is not None:
        screening_service = MockScreeningService(screening_result)
    else:
        screening_service = ScreeningService()

    tariff_result = request.get("tariff_result")
    if tariff_result is not None:
        tariff_engine = MockTariffEngine(tariff_result)
    else:
        tariff_engine = TariffEngine()

    notification_result = request.get("notification_result")
    if notification_result is not None:
        notification_service = MockNotificationService(notification_result)
    else:
        notification_service = NotificationService()

    api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)

    try:
        result = api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
        return result
    except Exception as e:
        return {"status": "error", "reason": str(e)}