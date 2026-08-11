"""
CargoQuote — Instant Freight Quotation System

A synchronous quotation flow that validates shipper requests, screens for
denied parties, computes tariffs, stores quotes, and notifies outcomes.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class QuoteStatus(Enum):
    """Quote lifecycle status."""
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


class ValidationError(Exception):
    """Request validation failed."""
    pass


class StorageError(Exception):
    """Quote store operation failed."""
    pass


class ScreeningError(Exception):
    """Screening service error."""
    pass


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


class ScreeningService:
    """External denied-party screening provider."""

    def __init__(self):
        self.available = True
        self.risk_index_value = None

    def screen(self, shipper_id: str) -> float:
        """
        Return a shipper risk index (0–100 scale).
        Raise ScreeningError if unavailable.
        """
        if not self.available:
            raise ScreeningError("Screening service unavailable")
        if self.risk_index_value is not None:
            return self.risk_index_value
        return 25.0


class TariffEngine:
    """Tariff pricing computation."""

    def __init__(self):
        self.price_value = None

    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Compute freight price from weight and distance.
        Base: €0.50 per kg-km plus €50 handling.
        """
        if self.price_value is not None:
            return self.price_value
        return (weight_kg * distance_km * 0.50) + 50.0


class QuoteStore:
    """Quote database."""

    def __init__(self):
        self.available = True
        self.quotes = {}
        self.next_id = 1000

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """
        Store a draft quote. Return quote_id.
        Raise StorageError if unavailable.
        """
        if not self.available:
            raise StorageError("Quote store unavailable")
        quote_id = f"QT-{self.next_id}"
        self.next_id += 1
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
        self,
        quote_id: str,
        status: QuoteStatus,
        price_amount: Optional[float] = None,
    ) -> Quote:
        """Update quote status and optionally price. Return updated quote."""
        if not self.available:
            raise StorageError("Quote store unavailable")
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote


class NotificationService:
    """External messaging provider."""

    def __init__(self):
        self.available = True
        self.sent_notifications = []

    def send_quote_document(
        self, shipper_id: str, quote_id: str, price_amount: float
    ) -> str:
        """Send quote document. Fire-and-forget; always succeeds from caller's view."""
        if self.available:
            self.sent_notifications.append(
                {"type": "quote_document", "shipper_id": shipper_id, "quote_id": quote_id}
            )
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Send refusal notice. Fire-and-forget; always succeeds from caller's view."""
        if self.available:
            self.sent_notifications.append(
                {"type": "refusal_notice", "shipper_id": shipper_id, "quote_id": quote_id}
            )
        return "sent"


class QuoteAPI:
    """Quote request orchestration and validation."""

    # Screening thresholds (decision table DT-S)
    ACCEPT_MAX = 30.0
    REVIEW_MIN = 31.0
    REVIEW_MAX = 70.0
    REFUSE_MIN = 71.0

    # Validation bounds (decision table DT-V)
    MIN_WEIGHT_KG = 100.0
    MAX_WEIGHT_KG = 25000.0
    MIN_DISTANCE_KM = 10.0
    MAX_DISTANCE_KM = 3000.0
    MIN_DECLARED_VALUE = 100.0
    MAX_DECLARED_VALUE = 500000.0

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

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        """
        Main quotation flow: validate, screen, price, store, notify.
        Return outcome dict.
        """
        # Validate request (DT-V)
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": "rejected", "reason": str(e)}

        # Store draft (DT-S decision: storage available)
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageError as e:
            # Storage failure → no screening, pricing, or notification (DT-S note 3)
            return {"status": "error", "reason": f"store_unavailable: {e}"}

        # Screen shipper
        risk_index = None
        screening_failed = False
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError as e:
            # Screening failure → price anyway, hold unscreened (DT-S note 5)
            screening_failed = True

        # Route on screening outcome
        if screening_failed:
            # Pricing runs; quote held unscreened; no notification
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, QuoteStatus.HELD_UNSCREENED, price_amount
            )
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "reason": "Screening unavailable",
            }

        if risk_index <= self.ACCEPT_MAX:
            # Accept: price, store, notify (DT-S row accept)
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
            # Fire-and-forget notification (DT-S note 4)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount
            )
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price_amount": price_amount,
            }

        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review hold: no pricing, no notification (DT-S note 1)
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "reason": f"Risk index {risk_index} requires manual review",
            }

        if risk_index >= self.REFUSE_MIN:
            # Refuse: store refusal, notify (DT-S note 2)
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            # Fire-and-forget notification
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused",
                "quote_id": quote_id,
                "reason": f"Screening: risk index {risk_index}",
            }

        # Unreachable (risk_index must fall into one of the above bands)
        return {"status": "error", "reason": "Unexpected screening outcome"}

    def _validate_request(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> None:
        """Validate request against bounds (DT-V)."""
        if not shipper_id or not isinstance(shipper_id, str):
            raise ValidationError("shipper_id required")
        if not (self.MIN_WEIGHT_KG <= weight_kg <= self.MAX_WEIGHT_KG):
            raise ValidationError(
                f"weight_kg must be {self.MIN_WEIGHT_KG}–{self.MAX_WEIGHT_KG}"
            )
        if not (self.MIN_DISTANCE_KM <= distance_km <= self.MAX_DISTANCE_KM):
            raise ValidationError(
                f"distance_km must be {self.MIN_DISTANCE_KM}–{self.MAX_DISTANCE_KM}"
            )
        if not (self.MIN_DECLARED_VALUE <= declared_value <= self.MAX_DECLARED_VALUE):
            raise ValidationError(
                f"declared_value must be {self.MIN_DECLARED_VALUE}–{self.MAX_DECLARED_VALUE}"
            )


# Module-level singleton instances
_quote_store = QuoteStore()
_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_notification_service = NotificationService()
_quote_api = QuoteAPI(
    _quote_store, _screening_service, _tariff_engine, _notification_service
)


def handle(request: dict) -> dict:
    """
    End-to-end quotation flow entry point.

    Input keys:
      - shipper_id: str
      - weight_kg: float
      - distance_km: float
      - declared_value: float
      - (optional) quote_store_exists: bool (simulate store unavailability if False)
      - (optional) screening_result: float (risk index override)
      - (optional) screening_status: str ("available" | "unavailable")
      - (optional) tariff_engine_result: float (price override)

    Return dict with "status" key and optional metadata.
    """
    # Set up test fixtures from request
    if "quote_store_exists" in request and not request["quote_store_exists"]:
        _quote_store.available = False
    else:
        _quote_store.available = True

    if "screening_status" in request:
        _screening_service.available = request["screening_status"] == "available"
    else:
        _screening_service.available = True

    if "screening_result" in request:
        _screening_service.risk_index_value = request["screening_result"]
    else:
        _screening_service.risk_index_value = None

    if "tariff_engine_result" in request:
        _tariff_engine.price_value = request["tariff_engine_result"]
    else:
        _tariff_engine.price_value = None

    # Run quotation flow
    return _quote_api.request_quote(
        shipper_id=request.get("shipper_id", "S001"),
        weight_kg=request.get("weight_kg", 500.0),
        distance_km=request.get("distance_km", 100.0),
        declared_value=request.get("declared_value", 5000.0),
    )