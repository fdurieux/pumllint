from dataclasses import dataclass, field
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


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus = QuoteStatus.DRAFT
    price_amount: Optional[float] = None
    risk_index: Optional[float] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class QuoteStore:
    def __init__(self):
        self.quotes: dict[str, Quote] = {}
        self.available = True

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        if not self.available:
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

    def update_quote(
        self,
        quote_id: str,
        status: QuoteStatus,
        price_amount: Optional[float] = None,
        risk_index: Optional[float] = None,
    ) -> Quote:
        if not self.available:
            raise StorageError("Quote store unavailable")
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        if risk_index is not None:
            quote.risk_index = risk_index
        return quote


class TariffEngine:
    RATE_PER_KG_KM = 0.05

    def price(self, weight_kg: float, distance_km: float) -> float:
        return weight_kg * distance_km * self.RATE_PER_KG_KM


class ScreeningService:
    def __init__(self):
        self.available = True

    def screen(self, shipper_id: str) -> float:
        if not self.available:
            raise ScreeningError("Screening service unavailable")
        return 0.0


class NotificationService:
    def __init__(self):
        self.notifications: list[dict] = []

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        self.notifications.append(
            {
                "type": "quote_document",
                "shipper_id": shipper_id,
                "quote_id": quote_id,
                "price_amount": price_amount,
            }
        )
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        self.notifications.append(
            {"type": "refusal_notice", "shipper_id": shipper_id, "quote_id": quote_id}
        )
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 30.0
    REVIEW_MIN = 30.0
    REVIEW_MAX = 70.0
    REFUSE_MIN = 70.0

    WEIGHT_MIN = 100.0
    WEIGHT_MAX = 30000.0
    DISTANCE_MIN = 1.0
    DISTANCE_MAX = 5000.0
    DECLARED_VALUE_MIN = 0.0
    DECLARED_VALUE_MAX = 1000000.0

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
        if not shipper_id or len(shipper_id.strip()) == 0:
            raise ValidationError("shipper_id is required")
        if weight_kg < self.WEIGHT_MIN or weight_kg > self.WEIGHT_MAX:
            raise ValidationError(
                f"weight_kg must be between {self.WEIGHT_MIN} and {self.WEIGHT_MAX}"
            )
        if distance_km < self.DISTANCE_MIN or distance_km > self.DISTANCE_MAX:
            raise ValidationError(
                f"distance_km must be between {self.DISTANCE_MIN} and {self.DISTANCE_MAX}"
            )
        if (
            declared_value < self.DECLARED_VALUE_MIN
            or declared_value > self.DECLARED_VALUE_MAX
        ):
            raise ValidationError(
                f"declared_value must be between {self.DECLARED_VALUE_MIN} and {self.DECLARED_VALUE_MAX}"
            )

    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": f"rejected_invalid_request: {str(e)}"}

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageError as e:
            return {"status": f"store_unavailable_error: {str(e)}"}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            risk_index = None

        if risk_index is not None:
            if risk_index <= self.ACCEPT_MAX:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.QUOTED, price_amount=price_amount
                )
                self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price": price_amount,
                }
            elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {"status": "review_hold", "quote_id": quote_id}
            elif risk_index >= self.REFUSE_MIN:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
                return {"status": "refused_screening", "quote_id": quote_id}
        else:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, QuoteStatus.HELD_UNSCREENED, price_amount=price_amount
            )
            return {"status": "held_unscreened", "quote_id": quote_id}


def handle(request: dict) -> dict:
    quote_store = QuoteStore()
    tariff_engine = TariffEngine()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    quote_api = QuoteAPI(
        quote_store, tariff_engine, screening_service, notification_service
    )

    if "quote_store_available" in request:
        quote_store.available = request["quote_store_available"]

    if "screening_service_available" in request:
        screening_service.available = request["screening_service_available"]

    if "screening_result" in request:
        screening_result = request["screening_result"]
        if isinstance(screening_result, (int, float)):
            original_screen = screening_service.screen

            def mock_screen(shipper_id: str) -> float:
                if not screening_service.available:
                    raise ScreeningError("Screening service unavailable")
                return float(screening_result)

            screening_service.screen = mock_screen

    shipper_id = request.get("shipper_id", "shipper_001")
    weight_kg = request.get("weight_kg", 1000.0)
    distance_km = request.get("distance_km", 100.0)
    declared_value = request.get("declared_value", 10000.0)

    result = quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    return result