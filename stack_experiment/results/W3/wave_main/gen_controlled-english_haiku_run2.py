from dataclasses import dataclass
from enum import Enum
from typing import Optional
import uuid


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


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


@dataclass
class QuoteRecord:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price_amount: Optional[float] = None


class ScreeningService:
    def screen(self, shipper_id: str) -> float:
        return 0.0


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base_price = 50.0
        weight_rate = 0.5
        distance_rate = 0.1
        return base_price + (weight_kg * weight_rate) + (distance_km * distance_rate)


class QuoteStore:
    def __init__(self):
        self.quotes: dict[str, QuoteRecord] = {}

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        quote_id = str(uuid.uuid4())
        record = QuoteRecord(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT,
        )
        self.quotes[quote_id] = record
        return quote_id

    def update_quote(
        self,
        quote_id: str,
        status: QuoteStatus,
        price_amount: Optional[float] = None,
    ) -> QuoteRecord:
        if quote_id not in self.quotes:
            raise StorageError("Quote not found")
        record = self.quotes[quote_id]
        record.status = status
        if price_amount is not None:
            record.price_amount = price_amount
        return record


class NotificationService:
    def send_quote_document(
        self, shipper_id: str, quote_id: str, price_amount: float
    ) -> str:
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 30.0
    REVIEW_MIN = 30.1
    REVIEW_MAX = 70.0
    REFUSE_MIN = 70.1

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
        if not shipper_id or shipper_id.strip() == "":
            return False
        if weight_kg <= 0 or weight_kg > 50000:
            return False
        if distance_km <= 0 or distance_km > 5000:
            return False
        if declared_value < 0 or declared_value > 1000000:
            return False
        return True

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected_invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageError:
            return {"status": "store_unavailable_error"}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            risk_index = None

        if risk_index is None:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.HELD_UNSCREENED, price_amount
                )
                return {
                    "status": "held_unscreened_response",
                    "quote_id": quote_id,
                    "price": price_amount,
                }
            except (PricingError, StorageError):
                return {"status": "error"}

        if risk_index <= self.ACCEPT_MAX:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.QUOTED, price_amount
                )
                try:
                    self.notification_service.send_quote_document(
                        shipper_id, quote_id, price_amount
                    )
                except NotificationError:
                    pass
                return {
                    "status": "quoted_response",
                    "quote_id": quote_id,
                    "price": price_amount,
                }
            except (PricingError, StorageError):
                return {"status": "error"}

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {
                    "status": "review_hold_response",
                    "quote_id": quote_id,
                }
            except StorageError:
                return {"status": "error"}

        elif risk_index >= self.REFUSE_MIN:
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
                try:
                    self.notification_service.send_refusal_notice(shipper_id, quote_id)
                except NotificationError:
                    pass
                return {
                    "status": "refused_screening_response",
                    "quote_id": quote_id,
                }
            except StorageError:
                return {"status": "error"}

        return {"status": "error"}


class MockScreeningService(ScreeningService):
    def __init__(self, result: Optional[float] = None):
        self.result = result

    def screen(self, shipper_id: str) -> float:
        if self.result is None:
            raise ScreeningError("Screening service unavailable")
        return self.result


class MockTariffEngine(TariffEngine):
    def __init__(self, result: Optional[float] = None):
        self.result = result

    def price(self, weight_kg: float, distance_km: float) -> float:
        if self.result is None:
            raise PricingError("Pricing service unavailable")
        return self.result


class MockNotificationService(NotificationService):
    def __init__(self, send_quote_result: str = "sent", send_refusal_result: str = "sent"):
        self.send_quote_result = send_quote_result
        self.send_refusal_result = send_refusal_result

    def send_quote_document(
        self, shipper_id: str, quote_id: str, price_amount: float
    ) -> str:
        if self.send_quote_result == "error":
            raise NotificationError("Notification service unavailable")
        return self.send_quote_result

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if self.send_refusal_result == "error":
            raise NotificationError("Notification service unavailable")
        return self.send_refusal_result


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "shipper_123")
    weight_kg = request.get("weight_kg", 100.0)
    distance_km = request.get("distance_km", 500.0)
    declared_value = request.get("declared_value", 5000.0)

    screening_result = request.get("screening_service_result")
    tariff_result = request.get("tariff_engine_result")
    notification_quote_result = request.get("notification_service_quote_result", "sent")
    notification_refusal_result = request.get("notification_service_refusal_result", "sent")

    quote_store = QuoteStore()

    if screening_result == "error" or screening_result is None:
        screening_service = MockScreeningService(result=None)
    else:
        screening_service = MockScreeningService(result=float(screening_result))

    if tariff_result == "error" or tariff_result is None:
        tariff_engine = MockTariffEngine(result=None)
    else:
        tariff_engine = MockTariffEngine(result=float(tariff_result))

    notification_service = MockNotificationService(
        send_quote_result=notification_quote_result,
        send_refusal_result=notification_refusal_result,
    )

    quote_api = QuoteAPI(
        quote_store, screening_service, tariff_engine, notification_service
    )

    result = quote_api.request_quote(
        shipper_id, weight_kg, distance_km, declared_value
    )

    return result