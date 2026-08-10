from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


class PricingError(Exception):
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
        Returns a shipper risk index (float).
        """
        return 0.5


class TariffEngine:
    """Computes freight price from weight and distance."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Returns the price amount as a single float value.
        """
        base_rate = 10.0
        weight_rate = 0.5
        distance_rate = 2.0
        return base_rate + (weight_kg * weight_rate) + (distance_km * distance_rate)


class QuoteStore:
    """PostgreSQL-backed quote storage."""

    def __init__(self):
        self.quotes = {}
        self.counter = 0

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """
        Stores a draft quote and returns the quote_id as a single string value.
        """
        self.counter += 1
        quote_id = f"QUOTE-{self.counter:06d}"
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

    def update_quote(
        self,
        quote_id: str,
        status: QuoteStatus,
        price_amount: Optional[float] = None,
    ) -> Quote:
        """
        Updates a quote's status and optionally price, returns the updated Quote.
        """
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote


class NotificationService:
    """External messaging provider."""

    def send_quote_document(
        self, shipper_id: str, quote_id: str, price_amount: float
    ) -> str:
        """
        Sends a quote document; fire-and-forget.
        Returns a single confirmation string.
        """
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """
        Sends a refusal notice; fire-and-forget.
        Returns a single confirmation string.
        """
        return "sent"


class QuoteAPI:
    """Orchestrates quote requests, validation, screening, pricing, and storage."""

    ACCEPT_MAX = 20.0
    REVIEW_MIN = 20.0
    REVIEW_MAX = 50.0
    REFUSE_MIN = 50.0

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
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> bool:
        """
        Validates request bounds per decision table DT-V.
        Returns True if valid, raises ValidationError if invalid.
        """
        if not shipper_id or len(shipper_id.strip()) == 0:
            raise ValidationError("shipper_id is required")
        if weight_kg <= 0 or weight_kg > 10000:
            raise ValidationError("weight_kg must be between 0 and 10000")
        if distance_km <= 0 or distance_km > 5000:
            raise ValidationError("distance_km must be between 0 and 5000")
        if declared_value < 0 or declared_value > 100000:
            raise ValidationError("declared_value must be between 0 and 100000")
        return True

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        """
        Orchestrates the complete quote flow per quote_flow.yaml.
        Returns a dict with "status" and optionally other fields.
        """
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": "rejected_invalid_request", "reason": str(e)}

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageError as e:
            return {"status": "error: store_unavailable", "reason": str(e)}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError as e:
            risk_index = None

        if risk_index is None:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.HELD_UNSCREENED, price_amount
                )
                return {
                    "status": "held_unscreened",
                    "quote_id": quote_id,
                    "price_amount": price_amount,
                }
            except Exception as e:
                return {"status": "error: pricing_failed", "reason": str(e)}

        if risk_index <= self.ACCEPT_MAX:
            try:
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
            except Exception as e:
                return {"status": "error: pricing_failed", "reason": str(e)}

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {"status": "review_hold", "quote_id": quote_id}

        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(
                quote_id, QuoteStatus.REFUSED_SCREENING
            )
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}

        return {"status": "error: unexpected_state"}


def handle(request: dict) -> dict:
    """
    End-to-end flow handler.
    Accepts a request dict with:
      - shipper_id (str)
      - weight_kg (float)
      - distance_km (float)
      - declared_value (float)
      - Optional: screening_result (float override for risk index)
      - Optional: pricing_result (float override for price)
      - Optional: store_result (str: "stored", "error", etc.)
    Returns a dict with "status" key and optional fields.
    """
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    quote_api = QuoteAPI(
        screening_service, tariff_engine, quote_store, notification_service
    )

    if "screening_result" in request:
        original_screen = screening_service.screen
        screening_service.screen = lambda shipper_id: request["screening_result"]

    if "pricing_result" in request:
        original_price = tariff_engine.price
        tariff_engine.price = lambda weight_kg, distance_km: request["pricing_result"]

    if "store_result" in request and request["store_result"] == "error":
        def error_store(*args, **kwargs):
            raise StorageError("Storage unavailable")
        quote_store.store_draft = error_store

    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0.0)
    distance_km = request.get("distance_km", 0.0)
    declared_value = request.get("declared_value", 0.0)

    return quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)