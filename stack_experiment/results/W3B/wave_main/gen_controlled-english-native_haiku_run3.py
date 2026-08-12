from dataclasses import dataclass
from enum import Enum
from typing import Optional
from abc import ABC, abstractmethod


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


class ValidationResult(Enum):
    VALID = "valid"
    INVALID = "invalid"


class ScreeningDecision(Enum):
    ACCEPT = "accept"
    REVIEW = "review"
    REFUSE = "refuse"
    UNAVAILABLE = "unavailable"


class StorageResult(Enum):
    SUCCESS = "success"
    UNAVAILABLE = "unavailable"


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
        """Return shipper risk index (0-100, higher is riskier)."""
        return 25.0


class TariffEngine:
    """Computes freight price from weight and distance."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Return price amount in currency units."""
        base_rate = 0.5
        return weight_kg * distance_km * base_rate


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self.quotes = {}
        self.next_id = 1

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """Store draft quote. Return quoteId or raise on storage failure."""
        quote_id = f"Q{self.next_id:06d}"
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
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
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
        """Send quote document asynchronously. Return confirmation status."""
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Send refusal notice asynchronously. Return confirmation status."""
        return "sent"


class QuoteAPI:
    """Orchestrates screening, pricing, and quote lifecycle."""

    ACCEPT_MAX = 30
    REVIEW_MIN = 30
    REVIEW_MAX = 70
    REFUSE_MIN = 70

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
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> ValidationResult:
        """Validate request bounds (decision table DT-V)."""
        if not shipper_id or len(shipper_id.strip()) == 0:
            return ValidationResult.INVALID
        if weight_kg <= 0 or weight_kg > 30000:
            return ValidationResult.INVALID
        if distance_km <= 0 or distance_km > 5000:
            return ValidationResult.INVALID
        if declared_value < 0 or declared_value > 1000000:
            return ValidationResult.INVALID
        return ValidationResult.VALID

    def _apply_screening_decision(self, risk_index: float) -> ScreeningDecision:
        """Determine screening outcome from risk index (decision table DT-S)."""
        if risk_index <= self.ACCEPT_MAX:
            return ScreeningDecision.ACCEPT
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            return ScreeningDecision.REVIEW
        elif risk_index >= self.REFUSE_MIN:
            return ScreeningDecision.REFUSE
        return ScreeningDecision.ACCEPT

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        """Main entry point for quote requests."""
        validation = self._validate_request(
            shipper_id, weight_kg, distance_km, declared_value
        )

        if validation == ValidationResult.INVALID:
            return {"status": "rejected_invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except Exception:
            return {"status": "store_unavailable_error"}

        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_decision = self._apply_screening_decision(risk_index)
        except Exception:
            screening_decision = ScreeningDecision.UNAVAILABLE

        if screening_decision == ScreeningDecision.ACCEPT:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, QuoteStatus.QUOTED, price_amount
            )
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount
            )
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price_amount": price_amount,
            }

        elif screening_decision == ScreeningDecision.REVIEW:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {"status": "review_hold", "quote_id": quote_id}

        elif screening_decision == ScreeningDecision.REFUSE:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}

        elif screening_decision == ScreeningDecision.UNAVAILABLE:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, QuoteStatus.HELD_UNSCREENED, price_amount
            )
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price_amount": price_amount,
            }

        return {"status": "error: unknown_screening_decision"}


_quote_store = QuoteStore()
_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_notification_service = NotificationService()
_quote_api = QuoteAPI(
    _quote_store, _screening_service, _tariff_engine, _notification_service
)


def handle(request: dict) -> dict:
    """End-to-end quote request handler."""
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    screening_result = request.get("screening_service_result")
    if screening_result is not None:
        if isinstance(screening_result, (int, float)):
            original_screen = _screening_service.screen
            _screening_service.screen = lambda sid: float(screening_result)
        elif screening_result == "error":
            _screening_service.screen = lambda sid: (_ for _ in ()).throw(
                Exception("Screening service unavailable")
            )

    storage_result = request.get("quote_store_result")
    if storage_result == "error":
        original_store = _quote_store.store_draft

        def failing_store_draft(*args, **kwargs):
            raise Exception("Storage unavailable")

        _quote_store.store_draft = failing_store_draft

    try:
        result = _quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
        return result
    except Exception as e:
        return {"status": f"error: {str(e)}"}
    finally:
        _screening_service.screen = original_screen if screening_result else _screening_service.screen
        if storage_result == "error":
            _quote_store.store_draft = original_store