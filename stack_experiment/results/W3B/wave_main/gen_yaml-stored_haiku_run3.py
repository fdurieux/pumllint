import json
from typing import Any
from enum import Enum
from dataclasses import dataclass, asdict


class ValidationError(Exception):
    pass


class StorageUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class ScreeningDecision(Enum):
    ACCEPT = "accept"
    REVIEW = "review"
    REFUSE = "refuse"


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
    status: str
    price_amount: float = None
    risk_index: float = None


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str) -> float:
        """Return shipper risk index as a single float value."""
        return 50.0


class TariffEngine:
    """Computes freight price from weight and distance."""

    ACCEPT_MAX = 30
    REVIEW_MIN = 31
    REVIEW_MAX = 70
    REFUSE_MIN = 71

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Return price amount as a single float value."""
        base_rate = 0.5
        distance_factor = 0.1
        weight_factor = 2.0
        return (weight_kg * weight_factor) + (distance_km * distance_factor) + base_rate


class QuoteStore:
    """PostgreSQL-backed quote storage."""

    def __init__(self):
        self.quotes = {}
        self._counter = 0

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """Store draft quote, return quote_id."""
        self._counter += 1
        quote_id = f"Q{self._counter:06d}"
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT.value,
        )
        self.quotes[quote_id] = quote
        return quote_id

    def update_quote(
        self, quote_id: str, status: str, price_amount: float = None
    ) -> dict:
        """Update quote status and optionally price, return updated quote dict."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return asdict(quote)


class NotificationService:
    """External messaging provider."""

    def send_quote_document(
        self, shipper_id: str, quote_id: str, price_amount: float
    ) -> str:
        """Send quote document, return confirmation."""
        return "notification_sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Send refusal notice, return confirmation."""
        return "notification_sent"


class QuoteAPI:
    """Main orchestration service for quote requests."""

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
    ) -> bool:
        """Validate quote request. Return True if valid, raise ValidationError if not."""
        if not shipper_id:
            raise ValidationError("shipper_id is required")
        if weight_kg <= 0:
            raise ValidationError("weight_kg must be positive")
        if distance_km <= 0:
            raise ValidationError("distance_km must be positive")
        if declared_value < 0:
            raise ValidationError("declared_value must be non-negative")
        return True

    def _get_screening_decision(self, risk_index: float) -> ScreeningDecision:
        """Determine screening decision based on risk index."""
        if risk_index <= self.tariff_engine.ACCEPT_MAX:
            return ScreeningDecision.ACCEPT
        elif self.tariff_engine.REVIEW_MIN <= risk_index <= self.tariff_engine.REVIEW_MAX:
            return ScreeningDecision.REVIEW
        else:
            return ScreeningDecision.REFUSE

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        """Main quote request handler."""
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": "rejected_invalid_request", "error": str(e)}

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except Exception as e:
            return {"status": "store_unavailable_error", "error": str(e)}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception:
            risk_index = None

        if risk_index is None:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.HELD_UNSCREENED.value, price_amount
                )
                return {
                    "status": "held_unscreened",
                    "quote_id": quote_id,
                    "price": price_amount,
                }
            except Exception as e:
                return {"status": "error", "error": f"Pricing failed: {str(e)}"}

        decision = self._get_screening_decision(risk_index)

        if decision == ScreeningDecision.ACCEPT:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.QUOTED.value, price_amount
                )
                self.notification_service.send_quote_document(
                    shipper_id, quote_id, price_amount
                )
                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price": price_amount,
                    "risk_index": risk_index,
                }
            except Exception as e:
                return {"status": "error", "error": f"Pricing failed: {str(e)}"}

        elif decision == ScreeningDecision.REVIEW:
            try:
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.REVIEW_HOLD.value
                )
                return {
                    "status": "review_hold",
                    "quote_id": quote_id,
                    "risk_index": risk_index,
                }
            except Exception as e:
                return {"status": "error", "error": f"Update failed: {str(e)}"}

        elif decision == ScreeningDecision.REFUSE:
            try:
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.REFUSED_SCREENING.value
                )
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
                return {
                    "status": "refused_screening",
                    "quote_id": quote_id,
                    "risk_index": risk_index,
                }
            except Exception as e:
                return {"status": "error", "error": f"Refusal failed: {str(e)}"}

        return {"status": "error", "error": "Unknown screening decision"}


def handle(request: dict) -> dict:
    """End-to-end quote request handler."""
    quote_store = QuoteStore()
    tariff_engine = TariffEngine()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    quote_api = QuoteAPI(
        quote_store, tariff_engine, screening_service, notification_service
    )

    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)

    if "screening_result" in request:
        screening_result = request["screening_result"]
        if screening_result == "error":
            original_screen = screening_service.screen
            screening_service.screen = lambda shipper_id: (_ for _ in ()).throw(
                ScreeningUnavailableError("Screening service unavailable")
            )

    if "store_result" in request:
        store_result = request["store_result"]
        if store_result == "error":
            original_store_draft = quote_store.store_draft
            quote_store.store_draft = lambda *args, **kwargs: (_ for _ in ()).throw(
                StorageUnavailableError("Quote store unavailable")
            )

    if isinstance(request.get("screening_result"), (int, float)):
        original_screen = screening_service.screen
        screening_service.screen = lambda shipper_id: float(request["screening_result"])

    result = quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)

    if "status" not in result:
        return {"status": "error", "error": "No status in result"}

    return result