from dataclasses import dataclass
from enum import Enum
from typing import Optional
import json


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
    risk_index: Optional[float] = None


class ScreeningService:
    def __init__(self):
        self.screening_result = None

    def screen(self, shipper_id: str) -> float:
        if self.screening_result == "error":
            raise ScreeningError("Screening service unavailable")
        if isinstance(self.screening_result, (int, float)):
            return float(self.screening_result)
        return 50.0


class TariffEngine:
    def __init__(self):
        self.pricing_result = None

    def price(self, weight_kg: float, distance_km: float) -> float:
        if self.pricing_result == "error":
            raise Exception("Pricing service unavailable")
        if isinstance(self.pricing_result, (int, float)):
            return float(self.pricing_result)
        base_rate = 100.0
        weight_factor = weight_kg * 0.5
        distance_factor = distance_km * 0.1
        return base_rate + weight_factor + distance_factor


class QuoteStore:
    def __init__(self):
        self.quotes = {}
        self.quote_counter = 0
        self.storage_available = True
        self.store_result = None

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if not self.storage_available or self.store_result == "error":
            raise StorageError("Quote store unavailable")
        self.quote_counter += 1
        quote_id = f"Q-{self.quote_counter:06d}"
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT
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


class NotificationService:
    def __init__(self):
        self.notification_result = None

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        if self.notification_result == "error":
            return "delivery_failed"
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if self.notification_result == "error":
            return "delivery_failed"
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 30.0
    REVIEW_MIN = 30.0
    REVIEW_MAX = 70.0
    REFUSE_MIN = 70.0

    def __init__(self, tariff_engine: TariffEngine, quote_store: QuoteStore,
                 screening_service: ScreeningService, notification_service: NotificationService):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        if not shipper_id or len(shipper_id) == 0:
            return False
        if weight_kg <= 0 or weight_kg > 100000:
            return False
        if distance_km <= 0 or distance_km > 10000:
            return False
        if declared_value < 0 or declared_value > 1000000:
            return False
        return True

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        if not self.validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {
                "status": "rejected",
                "reason": "invalid_request",
                "message": "Request validation failed"
            }

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError as e:
            return {
                "status": "error",
                "reason": "store_unavailable",
                "message": str(e)
            }

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
                return {
                    "status": "held_unscreened",
                    "quote_id": quote_id,
                    "message": "Quote held pending screening service recovery"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "reason": "pricing_failed",
                    "message": str(e)
                }

        if risk_index <= self.ACCEPT_MAX:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
                self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price": price_amount,
                    "message": "Quote issued"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "reason": "pricing_failed",
                    "message": str(e)
                }

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "message": "Quote held for compliance review"
            }

        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused",
                "quote_id": quote_id,
                "reason": "screening_failed",
                "message": "Quote refused due to screening result"
            }

        return {
            "status": "error",
            "reason": "unknown",
            "message": "Unexpected state in quote processing"
        }


def handle(request: dict) -> dict:
    quote_api = QuoteAPI(
        tariff_engine=TariffEngine(),
        quote_store=QuoteStore(),
        screening_service=ScreeningService(),
        notification_service=NotificationService()
    )

    if "screening_result" in request:
        quote_api.screening_service.screening_result = request["screening_result"]

    if "pricing_result" in request:
        quote_api.tariff_engine.pricing_result = request["pricing_result"]

    if "store_result" in request:
        quote_api.quote_store.store_result = request["store_result"]

    if "quote_store_available" in request:
        quote_api.quote_store.storage_available = request["quote_store_available"]

    if "notification_result" in request:
        quote_api.notification_service.notification_result = request["notification_result"]

    shipper_id = request.get("shipper_id", "SHIPPER-001")
    weight_kg = request.get("weight_kg", 500.0)
    distance_km = request.get("distance_km", 300.0)
    declared_value = request.get("declared_value", 5000.0)

    response = quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    return response