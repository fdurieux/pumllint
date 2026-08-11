from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime
import uuid


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


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price_amount: Optional[float] = None
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()


class ScreeningService:
    def screen(self, shipper_id: str) -> float:
        return 45.0


class TariffEngine:
    RATE_PER_100KG_KM = 2.5

    def price(self, weight_kg: float, distance_km: float) -> float:
        base_rate = (weight_kg / 100.0) * distance_km * self.RATE_PER_100KG_KM
        return round(base_rate, 2)


class QuoteStore:
    def __init__(self):
        self._quotes: dict[str, Quote] = {}

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
        self._quotes[quote_id] = quote
        return quote_id

    def update_quote(
        self,
        quote_id: str,
        status: QuoteStatus,
        price_amount: Optional[float] = None,
    ) -> Quote:
        if quote_id not in self._quotes:
            raise StorageError(f"Quote {quote_id} not found")
        quote = self._quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        quote.updated_at = datetime.now().isoformat()
        return quote


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 50
    REVIEW_MIN = 51
    REVIEW_MAX = 75
    REFUSE_MIN = 76

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
    ) -> bool:
        if not shipper_id or len(shipper_id) == 0:
            return False
        if weight_kg <= 0 or weight_kg > 30000:
            return False
        if distance_km <= 0 or distance_km > 2000:
            return False
        if declared_value < 0 or declared_value > 1000000:
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
            return {
                "status": "rejected_invalid_request",
                "reason": "Request validation failed",
            }

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageError as e:
            return {"status": "store_unavailable_error", "reason": str(e)}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            risk_index = None

        if risk_index is None:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.HELD_UNSCREENED, price_amount
                )
                return {
                    "status": "held_unscreened_response",
                    "quote_id": quote_id,
                    "price_amount": price_amount,
                }
            except Exception as e:
                return {"status": "error", "reason": str(e)}

        if risk_index <= self.ACCEPT_MAX:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.QUOTED, price_amount
                )
                try:
                    self.notification_service.send_quote_document(
                        shipper_id, quote_id, price_amount
                    )
                except NotificationError:
                    pass
                return {
                    "status": "quoted_response",
                    "quote_id": quote_id,
                    "price_amount": price_amount,
                }
            except Exception as e:
                return {"status": "error", "reason": str(e)}

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {
                    "status": "review_hold_response",
                    "quote_id": quote_id,
                }
            except Exception as e:
                return {"status": "error", "reason": str(e)}

        elif risk_index >= self.REFUSE_MIN:
            try:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
                try:
                    self.notification_service.send_refusal_notice(shipper_id, quote_id)
                except NotificationError:
                    pass
                return {
                    "status": "refused_screening_response",
                    "quote_id": quote_id,
                }
            except Exception as e:
                return {"status": "error", "reason": str(e)}

        return {"status": "error", "reason": "Unknown screening outcome"}


_quote_store = QuoteStore()
_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_notification_service = NotificationService()
_quote_api = QuoteAPI(
    _quote_store,
    _screening_service,
    _tariff_engine,
    _notification_service,
)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    screening_result = request.get("screening_result")
    store_result = request.get("store_result")

    global _quote_api, _quote_store, _screening_service, _tariff_engine, _notification_service

    if store_result == "error":
        _quote_store = QuoteStore()
        _quote_api = QuoteAPI(
            _quote_store,
            _screening_service,
            _tariff_engine,
            _notification_service,
        )

    if screening_result == "approved":
        original_screen = _screening_service.screen
        _screening_service.screen = lambda shipper_id: 30.0
        _quote_api.screening_service = _screening_service
    elif screening_result == "review":
        original_screen = _screening_service.screen
        _screening_service.screen = lambda shipper_id: 60.0
        _quote_api.screening_service = _screening_service
    elif screening_result == "declined":
        original_screen = _screening_service.screen
        _screening_service.screen = lambda shipper_id: 80.0
        _quote_api.screening_service = _screening_service
    elif screening_result == "unavailable":
        _screening_service.screen = lambda shipper_id: None
        _quote_api.screening_service = _screening_service

    result = _quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)

    _screening_service.screen = ScreeningService().screen
    _quote_api.screening_service = _screening_service

    return result