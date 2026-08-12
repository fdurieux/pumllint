import json
from typing import Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


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
    price: float | None = None
    created_at: str = ""


class QuoteStore:
    def __init__(self):
        self.quotes: dict[str, Quote] = {}
        self.counter = 0

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        if not hasattr(self, "_available"):
            self._available = True
        if not self._available:
            raise Exception("store_unavailable")
        self.counter += 1
        quote_id = f"Q{self.counter:06d}"
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT,
            created_at=datetime.now().isoformat(),
        )
        self.quotes[quote_id] = quote
        return quote_id

    def update_quote(self, quote_id: str, status: QuoteStatus, price: float | None = None) -> dict:
        if quote_id not in self.quotes:
            raise Exception("quote_not_found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price is not None:
            quote.price = price
        return {
            "quote_id": quote.quote_id,
            "status": quote.status.value,
            "price": quote.price,
        }


class ScreeningService:
    def screen(self, shipper_id: str) -> int:
        if not hasattr(self, "_available"):
            self._available = True
        if not self._available:
            raise Exception("screening_unavailable")
        return 50


class TariffEngine:
    PRICE_PER_KG = 0.5
    PRICE_PER_KM = 2.0
    BASE_PRICE = 50.0

    def price(self, weight_kg: float, distance_km: float) -> float:
        return self.BASE_PRICE + (weight_kg * self.PRICE_PER_KG) + (distance_km * self.PRICE_PER_KM)


class NotificationService:
    def __init__(self):
        self.deliverable = True

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        if not self.deliverable:
            raise Exception("notification_failed")
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if not self.deliverable:
            raise Exception("notification_failed")
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
    ) -> tuple[bool, str]:
        if not shipper_id or not isinstance(shipper_id, str):
            return False, "shipper_id_invalid"
        if weight_kg is None or weight_kg <= 0 or weight_kg > 10000:
            return False, "weight_kg_invalid"
        if distance_km is None or distance_km <= 0 or distance_km > 5000:
            return False, "distance_km_invalid"
        if declared_value is None or declared_value <= 0 or declared_value > 500000:
            return False, "declared_value_invalid"
        return True, ""

    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        valid, error = self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if not valid:
            return {"status": f"rejected: invalid_request", "reason": error}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception as e:
            if "store_unavailable" in str(e):
                return {"status": "error: store_unavailable"}
            raise

        screening_failed = False
        risk_index = None
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception as e:
            if "screening_unavailable" in str(e):
                screening_failed = True
            else:
                raise

        if screening_failed:
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


_quote_store = QuoteStore()
_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_notification_service = NotificationService()
_quote_api = QuoteAPI(_quote_store, _screening_service, _tariff_engine, _notification_service)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    if "store_available" in request:
        _quote_store._available = request["store_available"]

    if "screening_available" in request:
        _screening_service._available = request["screening_available"]

    if "notification_available" in request:
        _notification_service.deliverable = request["notification_available"]

    if "screening_result" in request:
        risk = request["screening_result"]
        original_screen = _screening_service.screen

        def mock_screen(shipper_id: str) -> int:
            return risk

        _screening_service.screen = mock_screen

    if "tariff_result" in request:
        price = request["tariff_result"]
        original_price = _tariff_engine.price

        def mock_price(weight_kg: float, distance_km: float) -> float:
            return price

        _tariff_engine.price = mock_price

    result = _quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)

    return result