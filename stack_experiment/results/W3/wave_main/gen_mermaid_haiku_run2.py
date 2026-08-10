import json
from typing import Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


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
    created_at: Optional[str] = None


class QuoteStore:
    def __init__(self):
        self.quotes: dict[str, Quote] = {}
        self.counter = 0

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if not self._is_available():
            raise StorageError("Store unavailable")
        self.counter += 1
        quote_id = f"QUOTE-{self.counter:06d}"
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT,
            created_at=datetime.now().isoformat()
        )
        self.quotes[quote_id] = quote
        return quote_id

    def update_quote(self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None) -> Quote:
        if quote_id not in self.quotes:
            raise StorageError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote

    def _is_available(self) -> bool:
        return True


class ScreeningService:
    def screen(self, shipper_id: str) -> float:
        return 0.5


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class TariffEngine:
    PRICE_PER_KG = 0.50
    PRICE_PER_KM = 0.05
    BASE_PRICE = 50.00

    def price(self, weight_kg: float, distance_km: float) -> float:
        return self.BASE_PRICE + (weight_kg * self.PRICE_PER_KG) + (distance_km * self.PRICE_PER_KM)


class QuoteAPI:
    ACCEPT_MAX = 0.3
    REVIEW_MIN = 0.3
    REVIEW_MAX = 0.7
    REFUSE_MIN = 0.7

    def __init__(
        self,
        quote_store: QuoteStore,
        screening_service: ScreeningService,
        tariff_engine: TariffEngine,
        notification_service: NotificationService
    ):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float
    ) -> dict:
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected_invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError:
            return {"status": "error: store_unavailable"}

        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_failed = False
        except ScreeningError:
            screening_failed = True
            risk_index = None

        if screening_failed:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount
            }

        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount
            }

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }

        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }

    def _validate_request(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float
    ) -> bool:
        if not shipper_id or weight_kg <= 0 or distance_km <= 0 or declared_value <= 0:
            return False
        if weight_kg > 10000 or distance_km > 5000:
            return False
        return True


def handle(request: dict) -> dict:
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    quote_api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)

    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)

    if "screening_result" in request:
        screening_result = request["screening_result"]
        original_screen = screening_service.screen
        if screening_result == "error":
            screening_service.screen = lambda shipper_id: (_ for _ in ()).throw(
                ScreeningError("Service unavailable")
            )
        else:
            try:
                risk_index = float(screening_result)
                screening_service.screen = lambda shipper_id, r=risk_index: r
            except (ValueError, TypeError):
                pass

    if "store_result" in request:
        store_result = request["store_result"]
        if store_result == "error":
            original_store = quote_store.store_draft
            quote_store.store_draft = lambda *args, **kwargs: (_ for _ in ()).throw(
                StorageError("Store unavailable")
            )

    result = quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    return result