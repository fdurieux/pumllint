import json
from typing import Optional
from datetime import datetime
from enum import Enum


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


class ScreeningService:
    def screen(self, shipper_id: str) -> float:
        return 0.0


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base_rate = 0.5
        return weight_kg * distance_km * base_rate


class QuoteStore:
    def __init__(self):
        self.quotes = {}
        self.next_id = 1

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        quote_id = f"Q{self.next_id:06d}"
        self.next_id += 1
        self.quotes[quote_id] = {
            "id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": QuoteStatus.DRAFT.value,
            "price": None,
            "created_at": datetime.now().isoformat(),
        }
        return quote_id

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        return self.quotes[quote_id]


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 25.0
    REVIEW_MIN = 25.0
    REVIEW_MAX = 75.0
    REFUSE_MIN = 75.0

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

    def validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        if not shipper_id or shipper_id.strip() == "":
            raise ValidationError("shipper_id is required")
        if weight_kg <= 0:
            raise ValidationError("weight_kg must be positive")
        if distance_km <= 0:
            raise ValidationError("distance_km must be positive")
        if declared_value <= 0:
            raise ValidationError("declared_value must be positive")
        return True

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        try:
            self.validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as e:
            return {"status": "rejected_invalid_request", "reason": str(e)}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError as e:
            return {"status": "store_unavailable_error", "reason": str(e)}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED.value, price_amount)
            return {"status": "held_unscreened", "quote_id": quote_id, "price": price_amount}

        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED.value, price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD.value)
            return {"status": "review_hold", "quote_id": quote_id}

        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING.value)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}

        return {"status": "error", "reason": "Unknown screening outcome"}


def handle(request: dict) -> dict:
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()

    api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)

    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    if request.get("screening_result") == "error":
        try:
            raise ScreeningError("Screening service unavailable")
        except:
            screening_service.screen = lambda _: (_ for _ in ()).throw(ScreeningError("Screening service unavailable"))

    if request.get("screening_result") == "approved":
        screening_service.screen = lambda _: 10.0

    elif request.get("screening_result") == "review":
        screening_service.screen = lambda _: 50.0

    elif request.get("screening_result") == "declined":
        screening_service.screen = lambda _: 90.0

    if request.get("store_result") == "error":
        quote_store.store_draft = lambda *_: (_ for _ in ()).throw(StorageError("Storage unavailable"))

    if weight_kg is not None and distance_km is not None:
        tariff_engine.price = lambda w, d: weight_kg * distance_km * 0.5

    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)