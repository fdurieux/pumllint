import json
from typing import Any, Optional
from dataclasses import dataclass
from enum import Enum


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


class PricingError(Exception):
    pass


class RiskBand(Enum):
    ACCEPT = "accept"
    REVIEW = "review"
    REFUSE = "refuse"


@dataclass
class QuoteDraft:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: str


@dataclass
class UpdatedQuote:
    quote_id: str
    status: str
    price_amount: Optional[float] = None


class ScreeningService:
    def __init__(self, screening_result: Optional[str] = None, risk_index: Optional[float] = None):
        self.screening_result = screening_result
        self.risk_index = risk_index

    def screen(self, shipper_id: str) -> float:
        if self.screening_result == "error":
            raise ScreeningError("screening_unavailable")
        if self.risk_index is not None:
            return self.risk_index
        return 25.0


class TariffEngine:
    def __init__(self, pricing_result: Optional[str] = None, price_amount: Optional[float] = None):
        self.pricing_result = pricing_result
        self.price_amount = price_amount

    def price(self, weight_kg: float, distance_km: float) -> float:
        if self.pricing_result == "error":
            raise PricingError("pricing_unavailable")
        if self.price_amount is not None:
            return self.price_amount
        base_rate = 10.0
        weight_factor = weight_kg * 0.5
        distance_factor = distance_km * 0.2
        return base_rate + weight_factor + distance_factor


class NotificationService:
    def __init__(self, notification_result: Optional[str] = None):
        self.notification_result = notification_result

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        if self.notification_result == "error":
            return "notification_error"
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if self.notification_result == "error":
            return "notification_error"
        return "sent"


class QuoteStore:
    def __init__(self, store_result: Optional[str] = None):
        self.store_result = store_result
        self._quote_counter = 0

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if self.store_result == "error":
            raise StorageError("store_unavailable")
        self._quote_counter += 1
        quote_id = f"Q-{self._quote_counter:06d}"
        return quote_id

    def update_quote(self, quote_id: str, status: str, price_amount: Optional[float] = None) -> UpdatedQuote:
        if self.store_result == "error":
            raise StorageError("store_unavailable")
        return UpdatedQuote(quote_id=quote_id, status=status, price_amount=price_amount)


class QuoteAPI:
    ACCEPT_MAX = 50.0
    REVIEW_MIN = 50.0
    REVIEW_MAX = 75.0
    REFUSE_MIN = 75.0

    WEIGHT_MIN = 0.1
    WEIGHT_MAX = 25000.0
    DISTANCE_MIN = 1.0
    DISTANCE_MAX = 3000.0
    VALUE_MIN = 100.0
    VALUE_MAX = 250000.0

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

    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        if not shipper_id or not isinstance(shipper_id, str):
            return False
        if not isinstance(weight_kg, (int, float)) or weight_kg < self.WEIGHT_MIN or weight_kg > self.WEIGHT_MAX:
            return False
        if not isinstance(distance_km, (int, float)) or distance_km < self.DISTANCE_MIN or distance_km > self.DISTANCE_MAX:
            return False
        if not isinstance(declared_value, (int, float)) or declared_value < self.VALUE_MIN or declared_value > self.VALUE_MAX:
            return False
        return True

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected_invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError:
            return {"status": "store_unavailable_error"}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
                return {"status": "held_unscreened", "quote_id": quote_id, "price": price_amount}
            except PricingError:
                return {"status": "pricing_error"}

        if risk_index <= self.ACCEPT_MAX:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
            except PricingError:
                return {"status": "pricing_error"}

            try:
                self.quote_store.update_quote(quote_id, "quoted", price_amount)
            except StorageError:
                return {"status": "store_unavailable_error"}

            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)

            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            try:
                self.quote_store.update_quote(quote_id, "review_hold")
            except StorageError:
                return {"status": "store_unavailable_error"}

            return {"status": "review_hold", "quote_id": quote_id}

        elif risk_index >= self.REFUSE_MIN:
            try:
                self.quote_store.update_quote(quote_id, "refused_screening")
            except StorageError:
                return {"status": "store_unavailable_error"}

            self.notification_service.send_refusal_notice(shipper_id, quote_id)

            return {"status": "refused_screening", "quote_id": quote_id}

        return {"status": "error: unknown_risk_band"}


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "S-001")
    weight_kg = request.get("weight_kg", 500.0)
    distance_km = request.get("distance_km", 100.0)
    declared_value = request.get("declared_value", 5000.0)

    store_result = request.get("store_status")
    screening_result = request.get("screening_status")
    notification_result = request.get("notification_status")
    pricing_result = request.get("pricing_status")

    risk_index = request.get("screening_result")
    price_amount = request.get("pricing_result")

    quote_store = QuoteStore(store_result=store_result)
    screening_service = ScreeningService(screening_result=screening_result, risk_index=risk_index)
    tariff_engine = TariffEngine(pricing_result=pricing_result, price_amount=price_amount)
    notification_service = NotificationService(notification_result=notification_result)

    api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)

    try:
        result = api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
        return result
    except Exception as e:
        return {"status": f"error: {str(e)}"}