from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime
import uuid


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


class PricingError(Exception):
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
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


class QuoteStore:
    """PostgreSQL-backed quote storage."""

    def __init__(self):
        self.quotes: dict[str, Quote] = {}

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        """Store a draft quote and return its ID."""
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
        self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None
    ) -> Quote:
        """Update a quote's status and optionally its price."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        quote.updated_at = datetime.utcnow()
        return quote

    def get_quote(self, quote_id: str) -> Optional[Quote]:
        """Retrieve a quote by ID."""
        return self.quotes.get(quote_id)


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str) -> float:
        """
        Screen a shipper and return a risk index (0-100).
        In test/mock scenarios this is overridden via request params.
        """
        return 0.0


class TariffEngine:
    """Computes freight pricing from weight and distance."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Compute freight price based on weight and distance.
        Simple tariff: 0.5 per kg + 0.1 per km.
        In test/mock scenarios this is overridden via request params.
        """
        base_rate = 0.5
        distance_rate = 0.1
        return (weight_kg * base_rate) + (distance_km * distance_rate)


class NotificationService:
    """External notification provider for quote documents and refusals."""

    def send_quote_document(
        self, shipper_id: str, quote_id: str, price_amount: float
    ) -> str:
        """Send quote document to shipper. Returns confirmation."""
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Send refusal notice to shipper. Returns confirmation."""
        return "sent"


class QuoteAPI:
    """Main quotation orchestration engine."""

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
    ) -> None:
        """Validate request bounds per DT-V decision table."""
        if not shipper_id or len(shipper_id) == 0:
            raise ValidationError("shipper_id is required")
        if weight_kg <= 0 or weight_kg > 30000:
            raise ValidationError(f"weight_kg must be in range (0, 30000], got {weight_kg}")
        if distance_km <= 0 or distance_km > 3000:
            raise ValidationError(f"distance_km must be in range (0, 3000], got {distance_km}")
        if declared_value < 0 or declared_value > 100000:
            raise ValidationError(
                f"declared_value must be in range [0, 100000], got {declared_value}"
            )

    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        """
        Main quotation flow per behavior/quote_flow.puml.
        Returns outcome dict with status and optional details.
        """
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": "rejected", "reason": f"invalid_request: {str(e)}"}

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except Exception as e:
            return {"status": "error", "reason": f"store_unavailable: {str(e)}"}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            risk_index = None

        if risk_index is not None:
            if risk_index <= self.ACCEPT_MAX:
                try:
                    price_amount = self.tariff_engine.price(weight_kg, distance_km)
                except PricingError as e:
                    return {"status": "error", "reason": f"pricing_error: {str(e)}"}

                self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)

                try:
                    self.notification_service.send_quote_document(
                        shipper_id, quote_id, price_amount
                    )
                except Exception:
                    pass

                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price": price_amount,
                }

            elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {
                    "status": "review_hold",
                    "quote_id": quote_id,
                    "reason": "high_risk_screening",
                }

            elif risk_index >= self.REFUSE_MIN:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)

                try:
                    self.notification_service.send_refusal_notice(shipper_id, quote_id)
                except Exception:
                    pass

                return {
                    "status": "refused",
                    "quote_id": quote_id,
                    "reason": "screening_refusal",
                }
        else:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
            except PricingError as e:
                return {"status": "error", "reason": f"pricing_error: {str(e)}"}

            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)

            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "reason": "screening_unavailable",
            }


def handle(request: dict) -> dict:
    """
    End-to-end flow handler.
    
    Request keys:
      - shipper_id: string
      - weight_kg: float
      - distance_km: float
      - declared_value: float
      - screening_result: (optional) risk index override (0-100 or "unavailable")
      - tariff_result: (optional) price override
      - store_result: (optional) "stored" or "error"
      - notification_result: (optional) result of notification calls
    
    Returns dict with "status" key and optional details.
    """
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()

    if request.get("store_result") == "error":
        quote_store.store_draft = lambda *args, **kwargs: (_ for _ in ()).throw(
            StorageUnavailableError("store unavailable")
        )

    if request.get("screening_result") == "unavailable":
        screening_service.screen = lambda *args, **kwargs: (_ for _ in ()).throw(
            ScreeningUnavailableError("screening unavailable")
        )
    elif "screening_result" in request:
        screening_result = request["screening_result"]
        if isinstance(screening_result, (int, float)):
            screening_service.screen = lambda *args, **kwargs: float(screening_result)

    if "tariff_result" in request:
        tariff_result = request["tariff_result"]
        if isinstance(tariff_result, (int, float)):
            tariff_engine.price = lambda *args, **kwargs: float(tariff_result)

    if request.get("notification_result") == "error":
        notification_service.send_quote_document = lambda *args, **kwargs: (_ for _ in ()).throw(
            Exception("notification failed")
        )
        notification_service.send_refusal_notice = lambda *args, **kwargs: (_ for _ in ()).throw(
            Exception("notification failed")
        )

    quote_api = QuoteAPI(
        quote_store, screening_service, tariff_engine, notification_service
    )

    return quote_api.request_quote(
        request.get("shipper_id", ""),
        request.get("weight_kg", 0.0),
        request.get("distance_km", 0.0),
        request.get("declared_value", 0.0),
    )