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


class ValidationError(Exception):
    pass


class StorageUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price_amount: Optional[float] = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str) -> float:
        """
        Returns shipper risk index.
        In the test harness, this is injected via screening_result in the request.
        """
        pass


class TariffEngine:
    """Computes freight price from weight and distance."""

    PRICE_PER_KG_KM = 0.05

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Returns priceAmount."""
        return weight_kg * distance_km * self.PRICE_PER_KG_KM


class NotificationService:
    """External messaging provider."""

    def send_quote_document(
        self, shipper_id: str, quote_id: str, price_amount: float
    ) -> str:
        """Fire-and-forget. Returns confirmation or error; never changes response."""
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Fire-and-forget. Returns confirmation or error; never changes response."""
        return "sent"


class QuoteStore:
    """PostgreSQL 16 quote store."""

    def __init__(self):
        self.quotes = {}
        self._next_id = 1

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        """Stores draft quote. Returns quoteId."""
        quote_id = f"QT-{self._next_id:06d}"
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

    def update_quote(self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None) -> Quote:
        """Updates quote status and optionally price. Returns updatedQuote."""
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        quote.updated_at = datetime.now()
        return quote


class QuoteAPI:
    """Main orchestrator for quote requests."""

    ACCEPT_MAX = 30
    REVIEW_MIN = 30
    REVIEW_MAX = 70
    REFUSE_MIN = 70

    def __init__(
        self,
        quote_store: QuoteStore,
        tariff_engine: TariffEngine,
        screening_service: ScreeningService,
        notification_service: NotificationService,
    ):
        self.quote_store = quote_store
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate_request(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> None:
        """Validation bounds from decision table DT-V."""
        if not shipper_id or shipper_id.strip() == "":
            raise ValidationError("shipper_id is required")
        if weight_kg <= 0 or weight_kg > 10000:
            raise ValidationError("weight_kg must be > 0 and <= 10000")
        if distance_km <= 0 or distance_km > 5000:
            raise ValidationError("distance_km must be > 0 and <= 5000")
        if declared_value < 0 or declared_value > 100000:
            raise ValidationError("declared_value must be >= 0 and <= 100000")

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        """
        Main entry point for quote requests.
        Returns dict with "status" and optional "quote_id", "price_amount", "risk_index".
        """
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": "rejected_invalid_request", "reason": str(e)}

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageUnavailableError:
            return {"status": "store_unavailable_error"}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            risk_index = None

        if risk_index is not None:
            if risk_index <= self.ACCEPT_MAX:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
                self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price_amount": price_amount,
                }
            elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {
                    "status": "review_hold",
                    "quote_id": quote_id,
                    "risk_index": risk_index,
                }
            else:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
                return {
                    "status": "refused_screening",
                    "quote_id": quote_id,
                    "risk_index": risk_index,
                }
        else:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, QuoteStatus.HELD_UNSCREENED, price_amount
            )
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price_amount": price_amount,
            }


class MockScreeningService(ScreeningService):
    """Mock screening service for testing."""

    def __init__(self, result: Optional[float] = None):
        self.result = result

    def screen(self, shipper_id: str) -> float:
        if self.result is None:
            raise ScreeningUnavailableError("Screening service unavailable")
        return self.result


class MockNotificationService(NotificationService):
    """Mock notification service for testing."""

    def __init__(self, status: str = "sent"):
        self.status = status
        self.sent_documents = []
        self.sent_refusals = []

    def send_quote_document(
        self, shipper_id: str, quote_id: str, price_amount: float
    ) -> str:
        self.sent_documents.append((shipper_id, quote_id, price_amount))
        return self.status

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        self.sent_refusals.append((shipper_id, quote_id))
        return self.status


def handle(request: dict) -> dict:
    """
    Main entry point for end-to-end quote flow.
    
    request dict keys:
    - shipper_id: string
    - weight_kg: float
    - distance_km: float
    - declared_value: float
    - screening_result: optional float (risk index); if absent, screening fails
    - notification_status: optional string (default "sent")
    """
    quote_store = QuoteStore()
    tariff_engine = TariffEngine()

    screening_result = request.get("screening_result")
    screening_service = MockScreeningService(result=screening_result)

    notification_status = request.get("notification_status", "sent")
    notification_service = MockNotificationService(status=notification_status)

    quote_api = QuoteAPI(
        quote_store=quote_store,
        tariff_engine=tariff_engine,
        screening_service=screening_service,
        notification_service=notification_service,
    )

    try:
        result = quote_api.request_quote(
            shipper_id=request.get("shipper_id", ""),
            weight_kg=request.get("weight_kg", 0),
            distance_km=request.get("distance_km", 0),
            declared_value=request.get("declared_value", 0),
        )
        return result
    except Exception as e:
        return {"status": f"error: {str(e)}"}