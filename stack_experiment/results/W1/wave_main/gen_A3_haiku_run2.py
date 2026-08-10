import json
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class QuoteRequest:
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float


class ValidationError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningService:
    def screen(self, shipper_id: str) -> int:
        return 0


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
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        return self.quotes[quote_id]


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


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

    def _validate_request(self, req: QuoteRequest) -> None:
        if not req.shipper_id or len(req.shipper_id) == 0:
            raise ValidationError("shipper_id is required and must not be empty")
        if not isinstance(req.weight_kg, (int, float)) or not (3 <= req.weight_kg <= 19400):
            raise ValidationError("weight_kg must be a number between 3 and 19400")
        if not isinstance(req.distance_km, (int, float)) or not (25 <= req.distance_km <= 7150):
            raise ValidationError("distance_km must be a number between 25 and 7150")
        if not isinstance(req.declared_value, (int, float)) or not (50 <= req.declared_value <= 83000):
            raise ValidationError("declared_value must be a number between 50 and 83000")

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        req = QuoteRequest(shipper_id, weight_kg, distance_km, declared_value)

        try:
            self._validate_request(req)
        except ValidationError:
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except Exception:
            return {"status": "error: store_unavailable"}

        risk_index = None
        screening_failed = False
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception:
            screening_failed = True

        if screening_failed:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }

        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }

        if risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }

        return {"status": "error: store_unavailable"}


_quote_store = QuoteStore()
_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_notification_service = NotificationService()
_quote_api = QuoteAPI(
    _quote_store, _screening_service, _tariff_engine, _notification_service
)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    screening_result = request.get("screening_result")
    store_status = request.get("store_status")

    if store_status == "unavailable":
        try:
            raise StoreUnavailableError()
        except StoreUnavailableError:
            pass

    if screening_result is not None:
        original_screen = _quote_api.screening_service.screen
        def mock_screen(sid):
            if isinstance(screening_result, (int, float)):
                return int(screening_result)
            return original_screen(sid)
        _quote_api.screening_service.screen = mock_screen

    if screening_result == "error":
        original_screen = _quote_api.screening_service.screen
        def mock_screen_error(sid):
            raise Exception("Screening service unavailable")
        _quote_api.screening_service.screen = mock_screen_error

    try:
        result = _quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
        return result
    except Exception as e:
        return {"status": f"error: {str(e)}"}