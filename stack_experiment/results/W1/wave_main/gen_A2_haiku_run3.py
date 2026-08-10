from dataclasses import dataclass
from typing import Optional
from enum import Enum
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
        """Return shipper risk index (0-100)."""
        return 0.0


class TariffEngine:
    """Computes freight price from weight and distance."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Return price amount in currency units."""
        base_rate = 10.0
        weight_factor = weight_kg * 0.5
        distance_factor = distance_km * 0.2
        return base_rate + weight_factor + distance_factor


class QuoteStore:
    """Persistent storage for quote records."""

    def __init__(self):
        self._quotes = {}
        self._counter = 0

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        """Store a draft quote and return its ID."""
        self._counter += 1
        quote_id = f"QT-{self._counter:06d}"
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
        self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None
    ) -> Quote:
        """Update quote status and optionally price, return updated quote."""
        if quote_id not in self._quotes:
            raise ValueError(f"Quote {quote_id} not found")
        quote = self._quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        quote.updated_at = datetime.now()
        return quote

    def get_quote(self, quote_id: str) -> Optional[Quote]:
        """Retrieve a quote by ID."""
        return self._quotes.get(quote_id)


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        """Send quote document to shipper. Returns confirmation status."""
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Send refusal notice to shipper. Returns confirmation status."""
        return "sent"


class QuoteAPI:
    """Orchestrates quote request validation, screening, pricing, and storage."""

    ACCEPT_MAX = 25.0
    REVIEW_MIN = 26.0
    REVIEW_MAX = 75.0
    REFUSE_MIN = 76.0

    def __init__(
        self,
        screening_service: ScreeningService,
        tariff_engine: TariffEngine,
        quote_store: QuoteStore,
        notification_service: NotificationService,
    ):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service

    def _validate_request(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> tuple[bool, Optional[str]]:
        """Validate quote request. Return (is_valid, error_message)."""
        if not shipper_id or len(shipper_id.strip()) == 0:
            return False, "shipper_id is required"
        if weight_kg <= 0:
            return False, "weight_kg must be positive"
        if distance_km <= 0:
            return False, "distance_km must be positive"
        if declared_value < 0:
            return False, "declared_value must be non-negative"
        return True, None

    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        """
        Main quote request handler.
        Returns dict with 'status' key describing outcome.
        """
        # Validate request
        is_valid, error_msg = self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if not is_valid:
            return {"status": "rejected_invalid_request", "error": error_msg}

        # Store draft quote
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception as e:
            return {"status": "error: store_unavailable", "error": str(e)}

        # Screen shipper
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception:
            # Screening failure: proceed with pricing and hold unscreened
            risk_index = None

        if risk_index is None:
            # Screening service unavailable: price but hold unscreened
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
                return {"status": "held_unscreened", "quote_id": quote_id, "price": price_amount}
            except Exception as e:
                return {"status": "error: pricing_failed", "error": str(e)}

        # Risk index available: apply screening decision rules
        if risk_index <= self.ACCEPT_MAX:
            # Accept: price and notify
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
                try:
                    self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
                except Exception:
                    # Notification failure is fire-and-forget; does not change response
                    pass
                return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
            except Exception as e:
                return {"status": "error: pricing_failed", "error": str(e)}

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review hold: no pricing, no notification
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {"status": "review_hold", "quote_id": quote_id}
            except Exception as e:
                return {"status": "error: update_failed", "error": str(e)}

        else:  # risk_index >= REFUSE_MIN
            # Refuse: update status and notify of refusal
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
                try:
                    self.notification_service.send_refusal_notice(shipper_id, quote_id)
                except Exception:
                    # Notification failure is fire-and-forget; does not change response
                    pass
                return {"status": "refused_screening", "quote_id": quote_id}
            except Exception as e:
                return {"status": "error: update_failed", "error": str(e)}


def handle(request: dict) -> dict:
    """
    End-to-end quote request handler.
    Accepts a request dict with shipper details and optional mock outcomes.
    Returns a dict with 'status' key describing the result.
    """
    shipper_id = request.get("shipper_id", "shipper_001")
    weight_kg = request.get("weight_kg", 500.0)
    distance_km = request.get("distance_km", 100.0)
    declared_value = request.get("declared_value", 5000.0)

    screening_service = MockScreeningService(request)
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = MockNotificationService(request)

    api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)

    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)


class MockScreeningService(ScreeningService):
    """Mock screening service for testing."""

    def __init__(self, request: dict):
        self.request = request

    def screen(self, shipper_id: str) -> float:
        """Return risk index from request or raise exception based on request flags."""
        if self.request.get("screening_status") == "error":
            raise Exception("Screening service unavailable")
        risk_index = self.request.get("screening_result", 0.0)
        if isinstance(risk_index, (int, float)):
            return float(risk_index)
        return 0.0


class MockNotificationService(NotificationService):
    """Mock notification service for testing."""

    def __init__(self, request: dict):
        self.request = request

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        """Send quote document. Return status or raise exception."""
        if self.request.get("notification_status") == "error":
            raise Exception("Notification service unavailable")
        return self.request.get("notification_result", "sent")

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Send refusal notice. Return status or raise exception."""
        if self.request.get("notification_status") == "error":
            raise Exception("Notification service unavailable")
        return self.request.get("notification_result", "sent")