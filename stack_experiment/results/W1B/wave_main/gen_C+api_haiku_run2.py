import uuid
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
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
    price: Optional[float] = None


class ScreeningService:
    """External denied-party screening provider."""

    def __init__(self, result: Optional[float] = None):
        self.result = result

    def screen(self, shipper_id: str) -> float:
        """
        Returns a shipper risk index (0-100).
        If result is None, simulates a service unavailability.
        """
        if self.result is None:
            raise ScreeningError("Screening service unavailable")
        return self.result


class TariffEngine:
    """Computes freight price from weight and distance."""

    def __init__(self, price_result: Optional[float] = None):
        self.price_result = price_result

    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Returns the freight price amount.
        If price_result is set, returns that; otherwise computes from tariff rules.
        """
        if self.price_result is not None:
            return self.price_result
        base_rate = 10.0
        weight_factor = weight_kg * 0.5
        distance_factor = distance_km * 0.2
        return base_rate + weight_factor + distance_factor


class QuoteStore:
    """PostgreSQL-backed quote store."""

    def __init__(self, storage_available: bool = True):
        self.storage_available = storage_available
        self.quotes: dict[str, Quote] = {}

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """
        Stores a draft quote and returns its quoteId.
        """
        if not self.storage_available:
            raise StorageError("Quote store unavailable")
        quote_id = str(uuid.uuid4())
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

    def update_quote(self, quote_id: str, status: QuoteStatus, price: Optional[float] = None) -> Quote:
        """
        Updates a quote's status and optionally price.
        """
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price is not None:
            quote.price = price
        return quote


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def __init__(self, delivery_succeeds: bool = True):
        self.delivery_succeeds = delivery_succeeds

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        """
        Sends a quote document. Fire-and-forget; failures are the provider's problem.
        Returns a delivery confirmation.
        """
        if not self.delivery_succeeds:
            return "delivery_failed"
        return "delivered"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """
        Sends a refusal notice. Fire-and-forget; failures are the provider's problem.
        Returns a delivery confirmation.
        """
        if not self.delivery_succeeds:
            return "delivery_failed"
        return "delivered"


class QuoteAPI:
    """Orchestrates the quotation flow: validation, screening, pricing, storage, and notification."""

    ACCEPT_MAX = 39
    REVIEW_MIN = 40
    REVIEW_MAX = 69
    REFUSE_MIN = 70

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
    ) -> None:
        """
        Validates request bounds per OpenAPI schema (DT-V decision table).
        """
        if not shipper_id or len(shipper_id) < 1:
            raise ValidationError("shipper_id must be non-empty")
        if weight_kg < 3 or weight_kg > 19400:
            raise ValidationError("weight_kg out of bounds [3, 19400]")
        if distance_km < 25 or distance_km > 7150:
            raise ValidationError("distance_km out of bounds [25, 7150]")
        if declared_value < 50 or declared_value > 83000:
            raise ValidationError("declared_value out of bounds [50, 83000]")

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        """
        Main entry point for quote requests.
        Returns a dict with status and optional quote_id, price, hold.
        """
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError:
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageError:
            return {"status": "error: store_unavailable"}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            risk_index = None

        if risk_index is not None:
            if risk_index <= self.ACCEPT_MAX:
                price = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.QUOTED, price
                )
                self.notification_service.send_quote_document(
                    shipper_id, quote_id, price
                )
                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price": price,
                }
            elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {
                    "status": "review_hold",
                    "quote_id": quote_id,
                }
            elif risk_index >= self.REFUSE_MIN:
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.REFUSED_SCREENING
                )
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
                return {
                    "status": "refused_screening",
                    "quote_id": quote_id,
                }
        else:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, QuoteStatus.HELD_UNSCREENED, price
            )
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }


def handle(request: dict) -> dict:
    """
    End-to-end flow handler.
    request dict keys:
      - shipper_id, weight_kg, distance_km, declared_value: quote parameters
      - screening_service_result: risk index (or None for unavailable)
      - tariff_engine_result: price override (or None for computed)
      - quote_store_available: True/False
      - notification_service_available: True/False
    """
    screening_result = request.get("screening_service_result")
    tariff_result = request.get("tariff_engine_result")
    store_available = request.get("quote_store_available", True)
    notification_available = request.get("notification_service_available", True)

    screening_service = ScreeningService(result=screening_result)
    tariff_engine = TariffEngine(price_result=tariff_result)
    quote_store = QuoteStore(storage_available=store_available)
    notification_service = NotificationService(delivery_succeeds=notification_available)

    api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)

    response = api.request_quote(
        shipper_id=request["shipper_id"],
        weight_kg=request["weight_kg"],
        distance_km=request["distance_km"],
        declared_value=request["declared_value"],
    )

    return response