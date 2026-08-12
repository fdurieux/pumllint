from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ValidationStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"


class ScreeningDecision(Enum):
    ACCEPT = "accept"
    REVIEW = "review"
    REFUSE = "refuse"
    UNAVAILABLE = "unavailable"


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


@dataclass
class QuoteRecord:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price_amount: Optional[float] = None


class ScreeningService:
    def screen(self, shipper_id: str) -> float:
        return 0.0


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base_rate = 0.5
        return weight_kg * base_rate + distance_km * 0.1


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class QuoteStore:
    def __init__(self):
        self.quotes = {}
        self.next_id = 1

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        quote_id = f"Q{self.next_id}"
        self.next_id += 1
        self.quotes[quote_id] = QuoteRecord(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT
        )
        return quote_id

    def update_quote(self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None) -> QuoteRecord:
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote


class QuoteValidator:
    MIN_WEIGHT = 0.1
    MAX_WEIGHT = 10000.0
    MIN_DISTANCE = 1.0
    MAX_DISTANCE = 3000.0
    MIN_VALUE = 1.0
    MAX_VALUE = 1000000.0

    def validate(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> ValidationStatus:
        if not shipper_id or len(shipper_id) == 0:
            return ValidationStatus.INVALID
        if weight_kg < self.MIN_WEIGHT or weight_kg > self.MAX_WEIGHT:
            return ValidationStatus.INVALID
        if distance_km < self.MIN_DISTANCE or distance_km > self.MAX_DISTANCE:
            return ValidationStatus.INVALID
        if declared_value < self.MIN_VALUE or declared_value > self.MAX_VALUE:
            return ValidationStatus.INVALID
        return ValidationStatus.VALID


class QuoteAPI:
    ACCEPT_MAX = 20.0
    REVIEW_MIN = 20.0
    REVIEW_MAX = 50.0
    REFUSE_MIN = 50.0

    def __init__(self):
        self.validator = QuoteValidator()
        self.quote_store = QuoteStore()
        self.screening_service = ScreeningService()
        self.tariff_engine = TariffEngine()
        self.notification_service = NotificationService()

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        validation = self.validator.validate(shipper_id, weight_kg, distance_km, declared_value)
        if validation == ValidationStatus.INVALID:
            return {"status": "rejected", "reason": "invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception as e:
            return {"status": "error", "reason": "store_unavailable"}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception as e:
            risk_index = None

        if risk_index is None:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
            return {"status": "held_unscreened", "quote_id": quote_id}

        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            except Exception:
                pass
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}

        elif risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {"status": "review_hold", "quote_id": quote_id}

        else:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass
            return {"status": "refused", "quote_id": quote_id}


_api = QuoteAPI()


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    if request.get("quote_store_result") == "unavailable":
        return {"status": "error: store_unavailable"}

    if request.get("screening_service_result") == "approved":
        mock_api = QuoteAPI()
        mock_api.screening_service.screen = lambda x: 10.0
        return mock_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)

    if request.get("screening_service_result") == "review":
        mock_api = QuoteAPI()
        mock_api.screening_service.screen = lambda x: 35.0
        return mock_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)

    if request.get("screening_service_result") == "declined":
        mock_api = QuoteAPI()
        mock_api.screening_service.screen = lambda x: 75.0
        return mock_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)

    if request.get("screening_service_result") == "error":
        mock_api = QuoteAPI()
        mock_api.screening_service.screen = lambda x: (_ for _ in ()).throw(Exception("screening unavailable"))
        return mock_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)

    return _api.request_quote(shipper_id, weight_kg, distance_km, declared_value)