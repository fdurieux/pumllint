from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime
import uuid


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
    price_amount: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


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
        self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None
    ) -> Quote:
        if not self.available:
            raise StorageError("Quote store unavailable")
        
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        quote.updated_at = datetime.utcnow()
        return quote


class ScreeningService:
    def __init__(self):
        self.available = True

    def screen(self, shipper_id: str) -> float:
        if not self.available:
            raise ScreeningError("Screening service unavailable")
        return 25.0


class TariffEngine:
    def __init__(self):
        self.available = True

    def price(self, weight_kg: float, distance_km: float) -> float:
        if not self.available:
            raise Exception("Tariff engine unavailable")
        base_rate = 0.50
        weight_factor = 0.02
        distance_factor = 0.001
        return (base_rate + weight_kg * weight_factor + distance_km * distance_factor) * 100


class NotificationService:
    def __init__(self):
        self.available = True

    def send_quote_document(
        self, shipper_id: str, quote_id: str, price_amount: float
    ) -> str:
        if not self.available:
            return "notification_failed"
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if not self.available:
            return "notification_failed"
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 30
    REVIEW_MIN = 31
    REVIEW_MAX = 70
    REFUSE_MIN = 71

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
        if not shipper_id or len(shipper_id) == 0:
            return False
        if weight_kg <= 0 or weight_kg > 30000:
            return False
        if distance_km <= 0 or distance_km > 3000:
            return False
        if declared_value < 0 or declared_value > 1000000:
            return False
        return True

    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {
                "status": "rejected_invalid_request",
                "reason": "Request validation failed",
            }

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageError as e:
            return {"status": "store_unavailable_error", "reason": str(e)}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.HELD_UNSCREENED, price_amount
                )
                return {
                    "status": "held_unscreened",
                    "quote_id": quote_id,
                    "reason": "Screening unavailable; quote held pending review",
                }
            except Exception as e:
                return {"status": "error", "reason": f"Pricing failed: {str(e)}"}

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
                    "price": price_amount,
                }
            except Exception as e:
                return {"status": "error", "reason": f"Pricing failed: {str(e)}"}

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {
                    "status": "review_hold",
                    "quote_id": quote_id,
                    "reason": "Quote held for compliance review",
                }
            except StorageError as e:
                return {"status": "error", "reason": f"Storage failed: {str(e)}"}

        elif risk_index >= self.REFUSE_MIN:
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
                return {
                    "status": "refused_screening",
                    "quote_id": quote_id,
                    "reason": "Shipper failed compliance screening",
                }
            except StorageError as e:
                return {"status": "error", "reason": f"Storage failed: {str(e)}"}

        return {"status": "error", "reason": "Unexpected state"}


def handle(request: dict) -> dict:
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()

    if "quote_store_available" in request:
        quote_store.available = request["quote_store_available"]

    if "screening_service_available" in request:
        screening_service.available = request["screening_service_available"]

    if "tariff_engine_available" in request:
        tariff_engine.available = request["tariff_engine_available"]

    if "notification_service_available" in request:
        notification_service.available = request["notification_service_available"]

    if "screening_result" in request:
        screening_service.screen = lambda _: float(request["screening_result"])

    api = QuoteAPI(
        quote_store, screening_service, tariff_engine, notification_service
    )

    shipper_id = request.get("shipper_id", "shipper_001")
    weight_kg = request.get("weight_kg", 500.0)
    distance_km = request.get("distance_km", 100.0)
    declared_value = request.get("declared_value", 5000.0)

    result = api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    return result