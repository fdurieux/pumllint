import json
from enum import Enum
from typing import Optional


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


class ResponseOutcome(Enum):
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"
    REJECTED_INVALID_REQUEST = "rejected_invalid_request"
    STORE_UNAVAILABLE_ERROR = "store_unavailable_error"


ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71


class ValidationBounds:
    MIN_WEIGHT_KG = 100
    MAX_WEIGHT_KG = 25000
    MIN_DISTANCE_KM = 10
    MAX_DISTANCE_KM = 3000
    MIN_DECLARED_VALUE = 100
    MAX_DECLARED_VALUE = 500000


def validate_request(shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
    if not shipper_id or len(shipper_id) == 0:
        return False
    if weight_kg < ValidationBounds.MIN_WEIGHT_KG or weight_kg > ValidationBounds.MAX_WEIGHT_KG:
        return False
    if distance_km < ValidationBounds.MIN_DISTANCE_KM or distance_km > ValidationBounds.MAX_DISTANCE_KM:
        return False
    if declared_value < ValidationBounds.MIN_DECLARED_VALUE or declared_value > ValidationBounds.MAX_DECLARED_VALUE:
        return False
    return True


class ScreeningService:
    def screen(self, shipper_id: str) -> Optional[int]:
        raise NotImplementedError("External service mock must be injected")


class DefaultScreeningService(ScreeningService):
    def __init__(self, risk_index: Optional[int] = None, status: str = "ok"):
        self.risk_index = risk_index
        self.status = status

    def screen(self, shipper_id: str) -> Optional[int]:
        if self.status == "error":
            return None
        return self.risk_index if self.risk_index is not None else 25


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        raise NotImplementedError("External service mock must be injected")


class DefaultTariffEngine(TariffEngine):
    def __init__(self, price_amount: Optional[float] = None):
        self.price_amount = price_amount

    def price(self, weight_kg: float, distance_km: float) -> float:
        if self.price_amount is not None:
            return self.price_amount
        base_rate = 0.5
        weight_surcharge = weight_kg * 0.01
        distance_surcharge = distance_km * 0.05
        return base_rate * weight_kg * distance_km + weight_surcharge + distance_surcharge


class QuoteStore:
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> Optional[str]:
        raise NotImplementedError("External database mock must be injected")

    def update_quote(self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None) -> Optional[str]:
        raise NotImplementedError("External database mock must be injected")


class DefaultQuoteStore(QuoteStore):
    def __init__(self, store_status: str = "ok"):
        self.store_status = store_status
        self.quotes = {}
        self.quote_counter = 0

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> Optional[str]:
        if self.store_status == "error":
            return None
        self.quote_counter += 1
        quote_id = f"Q-{self.quote_counter:06d}"
        self.quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": QuoteStatus.DRAFT.value,
            "price": None
        }
        return quote_id

    def update_quote(self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None) -> Optional[str]:
        if quote_id not in self.quotes:
            return None
        self.quotes[quote_id]["status"] = status.value
        if price_amount is not None:
            self.quotes[quote_id]["price"] = price_amount
        return quote_id


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> bool:
        raise NotImplementedError("External service mock must be injected")

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> bool:
        raise NotImplementedError("External service mock must be injected")


class DefaultNotificationService(NotificationService):
    def __init__(self, send_status: str = "ok"):
        self.send_status = send_status

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> bool:
        return self.send_status == "ok"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> bool:
        return self.send_status == "ok"


class QuoteAPI:
    def __init__(
        self,
        screening_service: Optional[ScreeningService] = None,
        tariff_engine: Optional[TariffEngine] = None,
        quote_store: Optional[QuoteStore] = None,
        notification_service: Optional[NotificationService] = None
    ):
        self.screening_service = screening_service or DefaultScreeningService()
        self.tariff_engine = tariff_engine or DefaultTariffEngine()
        self.quote_store = quote_store or DefaultQuoteStore()
        self.notification_service = notification_service or DefaultNotificationService()

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        if not validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {
                "status": ResponseOutcome.REJECTED_INVALID_REQUEST.value,
                "quote_id": None,
                "price": None
            }

        quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        if quote_id is None:
            return {
                "status": ResponseOutcome.STORE_UNAVAILABLE_ERROR.value,
                "quote_id": None,
                "price": None
            }

        risk_index = self.screening_service.screen(shipper_id)

        if risk_index is None:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
            return {
                "status": ResponseOutcome.HELD_UNSCREENED.value,
                "quote_id": quote_id,
                "price": price_amount
            }

        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {
                "status": ResponseOutcome.QUOTED.value,
                "quote_id": quote_id,
                "price": price_amount
            }

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {
                "status": ResponseOutcome.REVIEW_HOLD.value,
                "quote_id": quote_id,
                "price": None
            }

        if risk_index >= REFUSE_MIN:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": ResponseOutcome.REFUSED_SCREENING.value,
                "quote_id": quote_id,
                "price": None
            }


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)

    screening_service = DefaultScreeningService(
        risk_index=request.get("screening_service_result"),
        status=request.get("screening_service_status", "ok")
    )

    tariff_engine = DefaultTariffEngine(
        price_amount=request.get("tariff_engine_result")
    )

    quote_store = DefaultQuoteStore(
        store_status=request.get("quote_store_status", "ok")
    )

    notification_service = DefaultNotificationService(
        send_status=request.get("notification_service_status", "ok")
    )

    api = QuoteAPI(
        screening_service=screening_service,
        tariff_engine=tariff_engine,
        quote_store=quote_store,
        notification_service=notification_service
    )

    result = api.request_quote(shipper_id, weight_kg, distance_km, declared_value)

    return {
        "status": result["status"],
        "quote_id": result.get("quote_id"),
        "price": result.get("price")
    }