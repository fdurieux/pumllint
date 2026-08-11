import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4


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


class PricingError(Exception):
    pass


class NotificationError(Exception):
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
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class QuoteStore:
    def __init__(self):
        self.quotes: dict[str, Quote] = {}
        self.store_available = True

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        if not self.store_available:
            raise StorageError("quote store unavailable")
        
        quote_id = str(uuid4())
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
        if quote_id not in self.quotes:
            raise StorageError(f"quote {quote_id} not found")
        
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote


class ScreeningService:
    def __init__(self):
        self.service_available = True
        self.risk_index_override: Optional[float] = None

    def screen(self, shipper_id: str) -> float:
        if not self.service_available:
            raise ScreeningError("screening service unavailable")
        
        if self.risk_index_override is not None:
            return self.risk_index_override
        
        return 25.0


class TariffEngine:
    def __init__(self):
        self.service_available = True
        self.price_override: Optional[float] = None

    def price(self, weight_kg: float, distance_km: float) -> float:
        if not self.service_available:
            raise PricingError("tariff engine unavailable")
        
        if self.price_override is not None:
            return self.price_override
        
        base_price = 50.0
        weight_rate = 0.5
        distance_rate = 0.1
        return base_price + (weight_kg * weight_rate) + (distance_km * distance_rate)


class NotificationService:
    def __init__(self):
        self.service_available = True

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        if not self.service_available:
            raise NotificationError("notification service unavailable")
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if not self.service_available:
            raise NotificationError("notification service unavailable")
        return "sent"


class QuoteAPI:
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
        if not shipper_id or shipper_id.strip() == "":
            raise ValidationError("shipper_id is required")
        if weight_kg <= 0:
            raise ValidationError("weight_kg must be positive")
        if distance_km <= 0:
            raise ValidationError("distance_km must be positive")
        if declared_value < 0:
            raise ValidationError("declared_value must be non-negative")

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
        except StorageError as e:
            return {"status": "error", "reason": str(e)}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
            except PricingError as e:
                return {"status": "error", "reason": str(e)}

            try:
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.HELD_UNSCREENED, price_amount
                )
            except StorageError as e:
                return {"status": "error", "reason": str(e)}

            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "reason": "screening service unavailable",
            }

        if risk_index <= self.ACCEPT_MAX:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
            except PricingError as e:
                return {"status": "error", "reason": str(e)}

            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
            except StorageError as e:
                return {"status": "error", "reason": str(e)}

            try:
                self.notification_service.send_quote_document(
                    shipper_id, quote_id, price_amount
                )
            except NotificationError:
                pass

            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
                "currency": "USD",
            }

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            except StorageError as e:
                return {"status": "error", "reason": str(e)}

            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "reason": "quote held for manual compliance review",
            }

        elif risk_index >= self.REFUSE_MIN:
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            except StorageError as e:
                return {"status": "error", "reason": str(e)}

            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except NotificationError:
                pass

            return {
                "status": "refused",
                "quote_id": quote_id,
                "reason": "shipper failed screening",
            }

        return {"status": "error", "reason": "unexpected state"}


quote_store = QuoteStore()
screening_service = ScreeningService()
tariff_engine = TariffEngine()
notification_service = NotificationService()
quote_api = QuoteAPI(
    quote_store, screening_service, tariff_engine, notification_service
)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)

    if "quote_store_exists" in request:
        quote_store.store_available = request["quote_store_exists"]

    if "screening_service_status" in request:
        if request["screening_service_status"] == "unavailable":
            screening_service.service_available = False
        else:
            screening_service.service_available = True

    if "screening_result" in request:
        risk_result = request["screening_result"]
        if isinstance(risk_result, (int, float)):
            screening_service.risk_index_override = float(risk_result)
        elif risk_result == "approved":
            screening_service.risk_index_override = 15.0
        elif risk_result == "review":
            screening_service.risk_index_override = 50.0
        elif risk_result == "declined":
            screening_service.risk_index_override = 80.0

    if "tariff_engine_status" in request:
        if request["tariff_engine_status"] == "unavailable":
            tariff_engine.service_available = False
        else:
            tariff_engine.service_available = True

    if "pricing_result" in request:
        price_result = request["pricing_result"]
        if isinstance(price_result, (int, float)):
            tariff_engine.price_override = float(price_result)

    if "notification_service_status" in request:
        if request["notification_service_status"] == "unavailable":
            notification_service.service_available = False
        else:
            notification_service.service_available = True

    result = quote_api.request_quote(
        shipper_id=shipper_id,
        weight_kg=weight_kg,
        distance_km=distance_km,
        declared_value=declared_value,
    )

    screening_service.risk_index_override = None
    tariff_engine.price_override = None
    quote_store.store_available = True
    screening_service.service_available = True
    tariff_engine.service_available = True
    notification_service.service_available = True

    return result