import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


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
    created_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()


class ScreeningService:
    """External denied-party screening provider."""

    def __init__(self, mock_result: Optional[int] = None):
        self.mock_result = mock_result

    def screen(self, shipper_id: str) -> int:
        """Returns a risk index (0-100)."""
        if self.mock_result is not None:
            return self.mock_result
        return 25


class TariffEngine:
    """Computes freight price from weight and distance."""

    def __init__(self, mock_result: Optional[float] = None):
        self.mock_result = mock_result

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Returns the price amount in the company's currency."""
        if self.mock_result is not None:
            return self.mock_result
        base_rate = 10.0
        weight_factor = 0.05
        distance_factor = 0.02
        return base_rate + (weight_kg * weight_factor) + (distance_km * distance_factor)


class QuoteStore:
    """PostgreSQL-backed quote repository."""

    def __init__(self, storage_available: bool = True):
        self.storage_available = storage_available
        self.quotes = {}

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        """Stores a draft quote and returns the quote ID."""
        if not self.storage_available:
            raise StorageUnavailableError("Quote store unavailable")

        quote_id = str(uuid4())
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
        """Updates a quote's status and optionally its price."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")

        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        quote.updated_at = datetime.now().isoformat()
        return quote


class NotificationService:
    """External messaging provider."""

    def __init__(self, mock_result: Optional[str] = None):
        self.mock_result = mock_result
        self.sent_messages = []

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        """Sends a quote document to the shipper. Fire-and-forget; returns 'sent'."""
        message = {
            "type": "quote_document",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
            "price_amount": price_amount,
            "sent_at": datetime.now().isoformat(),
        }
        self.sent_messages.append(message)
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Sends a refusal notice to the shipper. Fire-and-forget; returns 'sent'."""
        message = {
            "type": "refusal_notice",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
            "sent_at": datetime.now().isoformat(),
        }
        self.sent_messages.append(message)
        return "sent"


class QuoteAPI:
    """Main orchestration service for the quotation flow."""

    ACCEPT_MAX = 30
    REVIEW_MIN = 31
    REVIEW_MAX = 70
    REFUSE_MIN = 71

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
        """Validates request bounds per decision table DT-V."""
        if not shipper_id or not isinstance(shipper_id, str):
            raise ValidationError("shipper_id is required and must be a string")
        if weight_kg <= 0 or weight_kg > 30000:
            raise ValidationError("weight_kg must be > 0 and <= 30000")
        if distance_km <= 0 or distance_km > 5000:
            raise ValidationError("distance_km must be > 0 and <= 5000")
        if declared_value < 0 or declared_value > 1000000:
            raise ValidationError("declared_value must be >= 0 and <= 1000000")

    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        """Main entry point for quote requests."""
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": "rejected", "reason": f"invalid_request: {str(e)}"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageUnavailableError:
            return {"status": "error", "reason": "store_unavailable"}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            risk_index = None

        if risk_index is None:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "reason": "screening_unavailable",
            }

        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price_amount": price_amount,
            }

        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "reason": "screening_review_required",
            }

        if risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused",
                "quote_id": quote_id,
                "reason": "screening_failed",
            }


def handle(request: dict) -> dict:
    """
    End-to-end quote request handler.

    Input keys:
    - shipper_id: string
    - weight_kg: float
    - distance_km: float
    - declared_value: float
    - quote_store_exists: bool (default True)
    - screening_service_result: int (risk index, default 25)
    - tariff_engine_result: float (price, default computed)
    - notification_service_result: str (default 'sent')

    Returns a dict with at minimum a 'status' key.
    """
    quote_store_exists = request.get("quote_store_exists", True)
    quote_store = QuoteStore(storage_available=quote_store_exists)

    screening_result = request.get("screening_service_result")
    screening_service = ScreeningService(mock_result=screening_result)

    tariff_result = request.get("tariff_engine_result")
    tariff_engine = TariffEngine(mock_result=tariff_result)

    notification_service = NotificationService()

    api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)

    shipper_id = request.get("shipper_id", "shipper_001")
    weight_kg = request.get("weight_kg", 500.0)
    distance_km = request.get("distance_km", 200.0)
    declared_value = request.get("declared_value", 10000.0)

    result = api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    return result