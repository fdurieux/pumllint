import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


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
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


class QuoteStore:
    """PostgreSQL 16 database for storing quote records."""

    def __init__(self, available: bool = True):
        self.available = available
        self.quotes: dict[str, Quote] = {}

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        """Store a draft quote and return quoteId."""
        if not self.available:
            raise StorageUnavailableError("Quote store unavailable")

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

    def update_quote(
        self,
        quote_id: str,
        status: QuoteStatus,
        price_amount: Optional[float] = None,
    ) -> Quote:
        """Update a quote's status and optional price."""
        if not self.available:
            raise StorageUnavailableError("Quote store unavailable")

        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")

        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        quote.updated_at = datetime.now()
        return quote


class ScreeningService:
    """External denied-party screening provider."""

    def __init__(self, available: bool = True, result: Optional[float] = None):
        self.available = available
        self.result = result

    def screen(self, shipper_id: str) -> float:
        """Screen a shipper and return riskIndex."""
        if not self.available:
            raise ScreeningUnavailableError("Screening service unavailable")

        if self.result is not None:
            return self.result

        return 0.0


class TariffEngine:
    """Computes freight price from weight and distance."""

    def __init__(self, base_rate: float = 1.0):
        self.base_rate = base_rate

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute price for a consignment."""
        price = (weight_kg * 0.5 + distance_km * 0.1) * self.base_rate
        return round(price, 2)


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def __init__(self, available: bool = True):
        self.available = available
        self.sent_documents: list[dict] = []
        self.sent_refusals: list[dict] = []

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        """Send quote document asynchronously. Fire-and-forget."""
        if self.available:
            self.sent_documents.append({
                "shipper_id": shipper_id,
                "quote_id": quote_id,
                "price_amount": price_amount,
            })
            return "sent"
        return "delivery_failure"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Send refusal notice asynchronously. Fire-and-forget."""
        if self.available:
            self.sent_refusals.append({
                "shipper_id": shipper_id,
                "quote_id": quote_id,
            })
            return "sent"
        return "delivery_failure"


class QuoteAPI:
    """Main quotation service orchestrating screening and pricing."""

    ACCEPT_MAX = 30.0
    REVIEW_MIN = 30.0
    REVIEW_MAX = 70.0
    REFUSE_MIN = 70.0

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
    ) -> bool:
        """Validate request per decision table DT-V."""
        if not shipper_id or shipper_id.strip() == "":
            return False
        if weight_kg <= 0 or weight_kg > 10000:
            return False
        if distance_km <= 0 or distance_km > 5000:
            return False
        if declared_value < 0 or declared_value > 1000000:
            return False
        return True

    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        """Main entry point for quote requests."""

        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {
                "status": "rejected_invalid_request",
                "quote_id": None,
            }

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageUnavailableError:
            return {
                "status": "store_unavailable_error",
                "quote_id": None,
            }

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            risk_index = None

        if risk_index is None:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    QuoteStatus.HELD_UNSCREENED,
                    price_amount,
                )
            except StorageUnavailableError:
                return {
                    "status": "store_unavailable_error",
                    "quote_id": quote_id,
                }

            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price_amount": None,
            }

        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    QuoteStatus.QUOTED,
                    price_amount,
                )
            except StorageUnavailableError:
                return {
                    "status": "store_unavailable_error",
                    "quote_id": quote_id,
                }

            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)

            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price_amount": price_amount,
            }

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            try:
                self.quote_store.update_quote(
                    quote_id,
                    QuoteStatus.REVIEW_HOLD,
                )
            except StorageUnavailableError:
                return {
                    "status": "store_unavailable_error",
                    "quote_id": quote_id,
                }

            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "price_amount": None,
            }

        elif risk_index >= self.REFUSE_MIN:
            try:
                self.quote_store.update_quote(
                    quote_id,
                    QuoteStatus.REFUSED_SCREENING,
                )
            except StorageUnavailableError:
                return {
                    "status": "store_unavailable_error",
                    "quote_id": quote_id,
                }

            self.notification_service.send_refusal_notice(shipper_id, quote_id)

            return {
                "status": "refused_screening",
                "quote_id": quote_id,
                "price_amount": None,
            }

        return {
            "status": "error: unknown_screening_outcome",
            "quote_id": quote_id,
        }


_quote_store = QuoteStore()
_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_notification_service = NotificationService()
_quote_api = QuoteAPI(
    _quote_store,
    _screening_service,
    _tariff_engine,
    _notification_service,
)


def handle(request: dict) -> dict:
    """
    Handle a quote request from input dict.

    Keys:
    - shipper_id: str
    - weight_kg: float
    - distance_km: float
    - declared_value: float
    - quote_store_available: bool (optional, default True)
    - screening_service_available: bool (optional, default True)
    - screening_service_result: float (optional, sets risk index)
    - notification_service_available: bool (optional, default True)
    """

    shipper_id = request.get("shipper_id", "shipper_1")
    weight_kg = request.get("weight_kg", 100.0)
    distance_km = request.get("distance_km", 500.0)
    declared_value = request.get("declared_value", 5000.0)

    if request.get("quote_store_available") is False:
        _quote_store.available = False
    else:
        _quote_store.available = True

    if request.get("screening_service_available") is False:
        _screening_service.available = False
    else:
        _screening_service.available = True

    if "screening_service_result" in request:
        _screening_service.result = request["screening_service_result"]
    else:
        _screening_service.result = None

    if request.get("notification_service_available") is False:
        _notification_service.available = False
    else:
        _notification_service.available = True

    result = _quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)

    return result