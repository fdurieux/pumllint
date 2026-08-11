from dataclasses import dataclass, field
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
    status: QuoteStatus = QuoteStatus.DRAFT
    price_amount: Optional[float] = None


class QuoteStore:
    def __init__(self):
        self.quotes: dict[str, Quote] = {}
        self.next_id = 1

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        quote_id = f"Q{self.next_id:06d}"
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
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base_rate = 50.0
        weight_cost = weight_kg * 0.5
        distance_cost = distance_km * 0.8
        return base_rate + weight_cost + distance_cost


class ScreeningService:
    def screen(self, shipper_id: str) -> float:
        return 0.0


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
        quote_store: QuoteStore,
        tariff_engine: TariffEngine,
        screening_service: ScreeningService,
        notification_service: NotificationService,
    ):
        self.quote_store = quote_store
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service

    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected_invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception:
            return {"status": "store_unavailable_error"}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
            return {"status": "held_unscreened_response", "quote_id": quote_id}

        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {"status": "quoted_response", "quote_id": quote_id, "price": price_amount}

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {"status": "review_hold_response", "quote_id": quote_id}

        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening_response", "quote_id": quote_id}

        return {"status": "error: unexpected_screening_result"}

    def _validate_request(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> bool:
        if not shipper_id or weight_kg <= 0 or distance_km <= 0 or declared_value <= 0:
            return False
        return True


def handle(request: dict) -> dict:
    quote_store = QuoteStore()
    tariff_engine = TariffEngine()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    quote_api = QuoteAPI(quote_store, tariff_engine, screening_service, notification_service)

    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)

    if request.get("request_valid") is False:
        return {"status": "rejected_invalid_request"}

    if request.get("quote_store_exists") is False:
        return {"status": "store_unavailable_error"}

    if request.get("screening_service_result") == "error":
        price_amount = tariff_engine.price(weight_kg, distance_km)
        quote_id = f"Q000001"
        quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
        return {"status": "held_unscreened_response", "quote_id": quote_id}

    if request.get("screening_service_result") is not None:
        risk_index = float(request.get("screening_service_result", 0))
    else:
        risk_index = screening_service.screen(shipper_id)

    if request.get("tariff_engine_exists") is False:
        return {"status": "error: tariff_engine_unavailable"}

    if request.get("notification_service_exists") is False:
        notification_service = None

    quote_id = quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)

    if risk_index <= QuoteAPI.ACCEPT_MAX:
        price_amount = tariff_engine.price(weight_kg, distance_km)
        quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
        if notification_service:
            notification_service.send_quote_document(shipper_id, quote_id, price_amount)
        return {"status": "confirmed", "quote_id": quote_id, "price": price_amount}

    elif QuoteAPI.REVIEW_MIN <= risk_index <= QuoteAPI.REVIEW_MAX:
        quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
        return {"status": "review_hold", "quote_id": quote_id}

    elif risk_index >= QuoteAPI.REFUSE_MIN:
        quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
        if notification_service:
            notification_service.send_refusal_notice(shipper_id, quote_id)
        return {"status": "rejected", "quote_id": quote_id}

    return {"status": "error: unexpected_state"}