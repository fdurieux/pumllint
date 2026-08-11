import json
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

WEIGHT_MIN = 3
WEIGHT_MAX = 19400
DISTANCE_MIN = 25
DISTANCE_MAX = 7150
DECLARED_VALUE_MIN = 50
DECLARED_VALUE_MAX = 83000


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price: Optional[float] = None


class QuoteStore:
    def __init__(self):
        self.quotes = {}

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        quote_id = str(uuid.uuid4())
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

    def update_quote(self, quote_id: str, status: QuoteStatus, price: Optional[float] = None) -> Quote:
        quote = self.quotes[quote_id]
        quote.status = status
        if price is not None:
            quote.price = price
        return quote


class ScreeningService:
    def __init__(self, mock_result: Optional[int] = None):
        self.mock_result = mock_result

    def screen(self, shipper_id: str) -> int:
        if self.mock_result is not None:
            return self.mock_result
        return 25


class TariffEngine:
    def __init__(self, mock_price: Optional[float] = None):
        self.mock_price = mock_price

    def price(self, weight_kg: float, distance_km: float) -> float:
        if self.mock_price is not None:
            return self.mock_price
        base = 50.0
        weight_charge = weight_kg * 0.5
        distance_charge = distance_km * 0.8
        return base + weight_charge + distance_charge


class NotificationService:
    def __init__(self, mock_failure: bool = False):
        self.mock_failure = mock_failure
        self.sent_messages = []

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        if self.mock_failure:
            return "delivery_failed"
        self.sent_messages.append(("quote_document", shipper_id, quote_id, price))
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if self.mock_failure:
            return "delivery_failed"
        self.sent_messages.append(("refusal_notice", shipper_id, quote_id))
        return "sent"


class QuoteAPI:
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

    def validate_request(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> Optional[str]:
        if not shipper_id or len(shipper_id) == 0:
            return "shipper_id required"
        if weight_kg < WEIGHT_MIN or weight_kg > WEIGHT_MAX:
            return f"weight_kg out of bounds [{WEIGHT_MIN}, {WEIGHT_MAX}]"
        if distance_km < DISTANCE_MIN or distance_km > DISTANCE_MAX:
            return f"distance_km out of bounds [{DISTANCE_MIN}, {DISTANCE_MAX}]"
        if declared_value < DECLARED_VALUE_MIN or declared_value > DECLARED_VALUE_MAX:
            return f"declared_value out of bounds [{DECLARED_VALUE_MIN}, {DECLARED_VALUE_MAX}]"
        return None

    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        validation_error = self.validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if validation_error:
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception:
            return {"status": "error: store_unavailable"}

        screening_available = True
        risk_index = None
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception:
            screening_available = False

        response = {"status": None, "quote_id": quote_id}

        if not screening_available:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price)
            response["status"] = "held_unscreened"
            response["price"] = price
            response["hold"] = True
            return response

        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
            response["status"] = "quoted"
            response["price"] = price
            return response

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            response["status"] = "review_hold"
            return response

        if risk_index >= REFUSE_MIN:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            response["status"] = "refused_screening"
            return response

        return response


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    quote_store = QuoteStore()

    screening_result = request.get("screening_service_result")
    screening_available = request.get("screening_service_status") != "unavailable"
    if screening_result is not None and screening_available:
        screening_service = ScreeningService(mock_result=screening_result)
    elif not screening_available:
        screening_service = ScreeningService(mock_result=None)
        screening_service.screen = lambda shipper_id: (_ for _ in ()).throw(Exception("unavailable"))
    else:
        screening_service = ScreeningService()

    tariff_result = request.get("tariff_engine_result")
    tariff_engine = TariffEngine(mock_price=tariff_result)

    notification_failure = request.get("notification_service_status") == "failed"
    notification_service = NotificationService(mock_failure=notification_failure)

    api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)

    result = api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    return result