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
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class QuoteStore:
    def __init__(self):
        self.quotes: dict[str, Quote] = {}

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
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
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        quote.updated_at = datetime.now()
        return quote


class ScreeningService:
    def screen(self, shipper_id: str) -> float:
        return 50.0


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base_rate = 2.5
        weight_factor = 0.05
        distance_factor = 0.03
        price = (weight_kg * weight_factor) + (distance_km * distance_factor) + base_rate
        return round(price, 2)


class NotificationService:
    def send_quote_document(
        self, shipper_id: str, quote_id: str, price_amount: float
    ) -> str:
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 40
    REVIEW_MIN = 41
    REVIEW_MAX = 70
    REFUSE_MIN = 71

    WEIGHT_MIN = 0.1
    WEIGHT_MAX = 30000
    DISTANCE_MIN = 1
    DISTANCE_MAX = 5000
    VALUE_MIN = 1
    VALUE_MAX = 1000000

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
            declared_value < self.VALUE_MIN
            or declared_value > self.VALUE_MAX
        ):
            raise ValidationError(
                f"declared_value must be between {self.VALUE_MIN} and {self.VALUE_MAX}"
            )

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": "rejected", "reason": str(e)}

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except Exception as e:
            return {"status": "error", "reason": "quote_store_unavailable"}

        screening_failed = False
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            screening_failed = True
            risk_index = None

        if screening_failed:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, QuoteStatus.HELD_UNSCREENED, price_amount
            )
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "reason": "screening_unavailable",
            }

        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount
            )
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
                "reason": "compliance_review_required",
            }
        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused",
                "quote_id": quote_id,
                "reason": "screening_failed",
            }

        return {"status": "error", "reason": "unexpected_state"}


def handle(request: dict) -> dict:
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()

    quote_api = QuoteAPI(
        quote_store, screening_service, tariff_engine, notification_service
    )

    shipper_id = request.get("shipper_id", "shipper_001")
    weight_kg = request.get("weight_kg", 100.0)
    distance_km = request.get("distance_km", 500.0)
    declared_value = request.get("declared_value", 10000.0)

    screening_result = request.get("screening_result")
    if screening_result == "unavailable":
        original_screen = screening_service.screen
        def mock_screen(sid):
            raise ScreeningUnavailableError("Service unavailable")
        screening_service.screen = mock_screen
    elif screening_result:
        risk_map = {
            "approved": 30,
            "review": 60,
            "declined": 80,
        }
        risk_index = risk_map.get(screening_result, 50)
        screening_service.screen = lambda sid: float(risk_index)

    store_available = request.get("store_available", True)
    if not store_available:
        original_store = quote_store.store_draft
        def mock_store(*args, **kwargs):
            raise StorageUnavailableError("Store unavailable")
        quote_store.store_draft = mock_store

    result = quote_api.request_quote(
        shipper_id,
        weight_kg,
        distance_km,
        declared_value,
    )

    return result