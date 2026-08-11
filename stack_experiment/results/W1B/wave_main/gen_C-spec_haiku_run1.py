import json
import uuid
from enum import Enum
from typing import Optional
from dataclasses import dataclass, asdict


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
    def screen(self, shipper_id: str) -> int:
        raise ScreeningError("screening_unavailable")


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            base += 316.00
        if distance_km >= 4912:
            base *= 1.19
        return round(base, 2)


class QuoteStore:
    def __init__(self):
        self.quotes = {}

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT,
        )
        return quote_id

    def update_quote(self, quote_id: str, status: QuoteStatus, price: Optional[float] = None) -> Quote:
        if quote_id not in self.quotes:
            raise StorageError("quote_not_found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price is not None:
            quote.price = price
        return quote

    def get_quote(self, quote_id: str) -> Quote:
        if quote_id not in self.quotes:
            raise StorageError("quote_not_found")
        return self.quotes[quote_id]


class QuoteAPI:
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

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
        if not shipper_id or shipper_id == "":
            raise ValidationError("shipper_id must be present and non-empty")
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            raise ValidationError("weight_kg must be between 3 and 19400")
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            raise ValidationError("distance_km must be between 25 and 7150")
        if (
            not isinstance(declared_value, (int, float))
            or declared_value < 50
            or declared_value > 83000
        ):
            raise ValidationError("declared_value must be between 50 and 83000")

    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError:
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError:
            return {"status": "error: store_unavailable"}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                pass
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
        else:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }


class MockScreeningService(ScreeningService):
    def __init__(self, risk_index: int = 30):
        self.risk_index = risk_index

    def screen(self, shipper_id: str) -> int:
        return self.risk_index


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    quote_store = QuoteStore()
    screening_service = MockScreeningService(request.get("screening_result", 30))
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    quote_api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)

    try:
        result = quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
        if "error" in result.get("status", ""):
            return result
        return result
    except Exception as e:
        return {"status": f"error: {str(e)}"}