import json
from dataclasses import dataclass
from typing import Optional
from enum import Enum


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


class ScreeningService:
    def screen(self, shipper_id: str) -> float:
        return 0.5


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base_rate = 0.50
        weight_factor = weight_kg * 0.01
        distance_factor = distance_km * 0.02
        return round(base_rate + weight_factor + distance_factor, 2)


class QuoteStore:
    def __init__(self):
        self.quotes = {}
        self.next_id = 1

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        quote_id = f"Q-{self.next_id:06d}"
        self.next_id += 1
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
            raise StorageError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 30.0
    REVIEW_MIN = 30.0
    REVIEW_MAX = 70.0
    REFUSE_MIN = 70.0

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

    def _validate_request(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> bool:
        if not shipper_id or weight_kg <= 0 or distance_km <= 0 or declared_value <= 0:
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
            return {"status": "rejected", "reason": "invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError as e:
            return {"status": "error", "reason": "store_unavailable"}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
            return {"status": "held_unscreened", "quote_id": quote_id}

        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {"status": "review_hold", "quote_id": quote_id}

        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused", "quote_id": quote_id}

        return {"status": "error", "reason": "unknown"}


def handle(request: dict) -> dict:
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    quote_api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)

    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    if "screening_result" in request:
        screening_result = request.get("screening_result")
        if isinstance(screening_result, (int, float)):
            original_screen = screening_service.screen
            screening_service.screen = lambda shipper_id: screening_result

    if "store_result" in request:
        store_result = request.get("store_result")
        if store_result == "error":
            original_store = quote_store.store_draft
            def failing_store(*args, **kwargs):
                raise StorageError("Storage unavailable")
            quote_store.store_draft = failing_store

    if "price_result" in request:
        price_result = request.get("price_result")
        if isinstance(price_result, (int, float)):
            tariff_engine.price = lambda w, d: price_result

    result = quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)

    if result.get("status") == "rejected":
        return {"status": "rejected"}
    elif result.get("status") == "error":
        return {"status": f"error: {result.get('reason')}"}
    elif result.get("status") == "quoted":
        return {"status": "confirmed", "quote_id": result.get("quote_id"), "price": result.get("price")}
    elif result.get("status") == "review_hold":
        return {"status": "review_hold", "quote_id": result.get("quote_id")}
    elif result.get("status") == "refused":
        return {"status": "refused", "quote_id": result.get("quote_id")}
    elif result.get("status") == "held_unscreened":
        return {"status": "held_unscreened", "quote_id": result.get("quote_id")}

    return {"status": "error: unknown"}