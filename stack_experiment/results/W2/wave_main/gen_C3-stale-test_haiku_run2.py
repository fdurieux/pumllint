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


class StorageError(Exception):
    pass


class ScreeningService:
    def __init__(self, risk_index: Optional[int] = None, available: bool = True):
        self.risk_index = risk_index
        self.available = available

    def screen(self, shipper_id: str) -> int:
        if not self.available:
            raise ScreeningError("screening_unavailable")
        return self.risk_index


class ScreeningError(Exception):
    pass


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base = 0.87 * weight_kg + 1.13 * distance_km

        if weight_kg > 1244:
            base += 316.00

        if distance_km >= 4912:
            base *= 1.19

        return round(base, 2)


class QuoteStore:
    def __init__(self, available: bool = True):
        self.available = available
        self.quotes = {}

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        if not self.available:
            raise StorageError("store_unavailable")

        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "quote_id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(
        self, quote_id: str, status: str, price: Optional[float] = None
    ) -> dict:
        if quote_id not in self.quotes:
            raise StorageError("quote_not_found")

        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price

        return self.quotes[quote_id]


class NotificationService:
    def __init__(self, available: bool = True):
        self.available = available
        self.notifications = []

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        if not self.available:
            return "delivery_failed"
        self.notifications.append(
            {"type": "quote_document", "shipper_id": shipper_id, "quote_id": quote_id, "price": price}
        )
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if not self.available:
            return "delivery_failed"
        self.notifications.append(
            {"type": "refusal_notice", "shipper_id": shipper_id, "quote_id": quote_id}
        )
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

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

    def validate_request(self, request: QuoteRequest) -> None:
        if not request.shipper_id or request.shipper_id.strip() == "":
            raise ValidationError("shipper_id is required and non-empty")

        if not isinstance(request.weight_kg, (int, float)) or not (3 <= request.weight_kg <= 19400):
            raise ValidationError("weight_kg must be between 3 and 19400")

        if not isinstance(request.distance_km, (int, float)) or not (
            25 <= request.distance_km <= 7150
        ):
            raise ValidationError("distance_km must be between 25 and 7150")

        if not isinstance(request.declared_value, (int, float)) or not (
            50 <= request.declared_value <= 83000
        ):
            raise ValidationError("declared_value must be between 50 and 83000")

    def request_quote(self, request: QuoteRequest) -> dict:
        try:
            self.validate_request(request)
        except ValidationError:
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(
                request.shipper_id, request.weight_kg, request.distance_km, request.declared_value
            )
        except StorageError:
            return {"status": "error: store_unavailable"}

        try:
            risk_index = self.screening_service.screen(request.shipper_id)
        except ScreeningError:
            price = self.tariff_engine.price(request.weight_kg, request.distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(request.weight_kg, request.distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(
                request.shipper_id, quote_id, price
            )
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(request.shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    screening_available = request.get("screening_service_available", True)
    screening_result = request.get("screening_service_result")
    store_available = request.get("quote_store_available", True)
    notification_available = request.get("notification_service_available", True)

    quote_request = QuoteRequest(
        shipper_id=shipper_id,
        weight_kg=weight_kg,
        distance_km=distance_km,
        declared_value=declared_value,
    )

    screening_service = ScreeningService(
        risk_index=screening_result, available=screening_available
    )
    tariff_engine = TariffEngine()
    quote_store = QuoteStore(available=store_available)
    notification_service = NotificationService(available=notification_available)

    api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)

    return api.request_quote(quote_request)