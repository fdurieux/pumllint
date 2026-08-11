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


class PricingError(Exception):
    pass


class NotificationError(Exception):
    pass


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


SCREENING_ACCEPT_MAX = 20
SCREENING_REVIEW_MIN = 21
SCREENING_REVIEW_MAX = 60
SCREENING_REFUSE_MIN = 61


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price_amount: Optional[float] = None


class QuoteStore:
    def __init__(self):
        self.quotes = {}
        self.next_id = 1
        self.available = True

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if not self.available:
            raise StorageError("storage unavailable")
        quote_id = f"Q{self.next_id:06d}"
        self.next_id += 1
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
        if not self.available:
            raise StorageError("storage unavailable")
        if quote_id not in self.quotes:
            raise StorageError(f"quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote


class TariffEngine:
    def __init__(self):
        self.available = True
        self.base_rate = 0.5

    def price(self, weight_kg: float, distance_km: float) -> float:
        if not self.available:
            raise PricingError("pricing service unavailable")
        return self.base_rate * weight_kg * distance_km


class ScreeningService:
    def __init__(self):
        self.available = True
        self.risk_scores = {}

    def screen(self, shipper_id: str) -> int:
        if not self.available:
            raise ScreeningError("screening service unavailable")
        if shipper_id in self.risk_scores:
            return self.risk_scores[shipper_id]
        return 15


class NotificationService:
    def __init__(self):
        self.available = True
        self.sent_documents = []
        self.sent_refusals = []

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        if not self.available:
            raise NotificationError("notification service unavailable")
        self.sent_documents.append({
            "shipper_id": shipper_id,
            "quote_id": quote_id,
            "price_amount": price_amount
        })
        return "document_sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if not self.available:
            raise NotificationError("notification service unavailable")
        self.sent_refusals.append({
            "shipper_id": shipper_id,
            "quote_id": quote_id
        })
        return "refusal_sent"


class QuoteAPI:
    def __init__(self, quote_store: QuoteStore, tariff_engine: TariffEngine,
                 screening_service: ScreeningService, notification_service: NotificationService):
        self.quote_store = quote_store
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service

    def validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        if not shipper_id or len(shipper_id) == 0:
            return False
        if weight_kg <= 0 or weight_kg > 30000:
            return False
        if distance_km <= 0 or distance_km > 5000:
            return False
        if declared_value < 0 or declared_value > 1000000:
            return False
        return True

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        if not self.validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid request"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError as e:
            return {"status": f"error: {str(e)}"}

        screening_failed = False
        risk_index = None

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError as e:
            screening_failed = True
            risk_index = None

        if screening_failed:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
            except PricingError as e:
                return {"status": f"error: {str(e)}"}

            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
            except StorageError as e:
                return {"status": f"error: {str(e)}"}

            return {"status": "held: screening unavailable", "quote_id": quote_id}

        if risk_index <= SCREENING_ACCEPT_MAX:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
            except PricingError as e:
                return {"status": f"error: {str(e)}"}

            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
            except StorageError as e:
                return {"status": f"error: {str(e)}"}

            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            except NotificationError:
                pass

            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}

        elif SCREENING_REVIEW_MIN <= risk_index <= SCREENING_REVIEW_MAX:
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            except StorageError as e:
                return {"status": f"error: {str(e)}"}

            return {"status": "review_hold", "quote_id": quote_id}

        elif risk_index >= SCREENING_REFUSE_MIN:
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            except StorageError as e:
                return {"status": f"error: {str(e)}"}

            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except NotificationError:
                pass

            return {"status": "refused: screening", "quote_id": quote_id}

        return {"status": "error: unexpected state"}


_quote_store = QuoteStore()
_tariff_engine = TariffEngine()
_screening_service = ScreeningService()
_notification_service = NotificationService()
_quote_api = QuoteAPI(_quote_store, _tariff_engine, _screening_service, _notification_service)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    if "quote_store_available" in request:
        _quote_store.available = request["quote_store_available"]

    if "tariff_engine_available" in request:
        _tariff_engine.available = request["tariff_engine_available"]

    if "screening_service_available" in request:
        _screening_service.available = request["screening_service_available"]

    if "notification_service_available" in request:
        _notification_service.available = request["notification_service_available"]

    if "screening_result" in request:
        risk_index = request["screening_result"]
        if isinstance(risk_index, int):
            _screening_service.risk_scores[shipper_id] = risk_index
        elif risk_index == "error":
            _screening_service.available = False

    result = _quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)

    return result