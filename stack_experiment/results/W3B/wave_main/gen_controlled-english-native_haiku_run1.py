from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


class Status(Enum):
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
    status: Status
    price_amount: Optional[float] = None


class ScreeningService:
    def screen(self, shipper_id: str) -> float:
        return 0.0

    def screen_with_error(self, shipper_id: str) -> float:
        raise ScreeningError("screening_unavailable_error")


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base_rate = 0.5
        distance_factor = 1.0 + (distance_km / 1000.0) * 0.1
        weight_factor = 1.0 + (weight_kg / 1000.0) * 0.05
        return weight_kg * distance_factor * weight_factor * base_rate


class QuoteStore:
    def __init__(self):
        self.quotes = {}
        self.next_id = 1

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        quote_id = f"Q{self.next_id:06d}"
        self.next_id += 1
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=Status.DRAFT,
        )
        self.quotes[quote_id] = quote
        return quote_id

    def update_quote(
        self,
        quote_id: str,
        status: Status,
        price_amount: Optional[float] = None,
    ) -> Quote:
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote

    def get_quote(self, quote_id: str) -> Optional[Quote]:
        return self.quotes.get(quote_id)


class NotificationService:
    def send_quote_document(
        self, shipper_id: str, quote_id: str, price_amount: float
    ) -> str:
        return "notification_sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "notification_sent"

    def send_with_error(
        self, shipper_id: str, quote_id: str, price_amount: Optional[float] = None
    ) -> str:
        raise Exception("notification_service_error")


class QuoteAPI:
    ACCEPT_MAX = 30.0
    REVIEW_MIN = 30.0
    REVIEW_MAX = 70.0
    REFUSE_MIN = 70.0

    WEIGHT_MIN = 0.1
    WEIGHT_MAX = 50000.0
    DISTANCE_MIN = 1.0
    DISTANCE_MAX = 5000.0
    VALUE_MIN = 0.01
    VALUE_MAX = 1000000.0

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
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> bool:
        if not shipper_id or len(shipper_id) == 0:
            return False
        if weight_kg < self.WEIGHT_MIN or weight_kg > self.WEIGHT_MAX:
            return False
        if distance_km < self.DISTANCE_MIN or distance_km > self.DISTANCE_MAX:
            return False
        if declared_value < self.VALUE_MIN or declared_value > self.VALUE_MAX:
            return False
        return True

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        if not self._validate_request(
            shipper_id, weight_kg, distance_km, declared_value
        ):
            return {
                "status": "rejected_invalid_request",
                "reason": "validation_failed",
            }

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageError:
            return {
                "status": "store_unavailable_error",
                "reason": "storage_failed",
            }

        screening_failed = False
        risk_index = 0.0
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            screening_failed = True

        if screening_failed:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, Status.HELD_UNSCREENED, price_amount
                )
                return {
                    "status": "held_unscreened_response",
                    "quote_id": quote_id,
                    "price_amount": price_amount,
                }
            except Exception as e:
                return {
                    "status": "error",
                    "reason": f"pricing_failed: {str(e)}",
                }

        if risk_index <= self.ACCEPT_MAX:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, Status.QUOTED, price_amount
                )
                try:
                    self.notification_service.send_quote_document(
                        shipper_id, quote_id, price_amount
                    )
                except Exception:
                    pass
                return {
                    "status": "quoted_response",
                    "quote_id": quote_id,
                    "price_amount": price_amount,
                }
            except Exception as e:
                return {
                    "status": "error",
                    "reason": f"pricing_failed: {str(e)}",
                }

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, Status.REVIEW_HOLD)
            return {
                "status": "review_hold_response",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }

        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(
                quote_id, Status.REFUSED_SCREENING
            )
            try:
                self.notification_service.send_refusal_notice(
                    shipper_id, quote_id
                )
            except Exception:
                pass
            return {
                "status": "refused_screening_response",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }

        return {
            "status": "error",
            "reason": "unexpected_screening_result",
        }


quote_store = QuoteStore()
screening_service = ScreeningService()
tariff_engine = TariffEngine()
notification_service = NotificationService()
quote_api = QuoteAPI(
    quote_store, screening_service, tariff_engine, notification_service
)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0.0)
    distance_km = request.get("distance_km", 0.0)
    declared_value = request.get("declared_value", 0.0)

    screening_result = request.get("screening_result")
    store_result = request.get("store_result")
    notification_result = request.get("notification_result")

    global quote_store, screening_service, tariff_engine, notification_service, quote_api

    quote_store = QuoteStore()

    if store_result == "error":
        screening_service = ScreeningService()
        tariff_engine = TariffEngine()
        notification_service = NotificationService()

        def mock_store_draft(*args, **kwargs):
            raise StorageError("storage_unavailable_error")

        quote_store.store_draft = mock_store_draft
    else:
        screening_service = ScreeningService()
        tariff_engine = TariffEngine()
        notification_service = NotificationService()

    if screening_result == "error":
        original_screen = screening_service.screen

        def mock_screen(shipper_id):
            raise ScreeningError("screening_unavailable_error")

        screening_service.screen = mock_screen
    elif screening_result == "approved":
        def mock_screen(shipper_id):
            return 25.0

        screening_service.screen = mock_screen
    elif screening_result == "review":
        def mock_screen(shipper_id):
            return 50.0

        screening_service.screen = mock_screen
    elif screening_result == "declined":
        def mock_screen(shipper_id):
            return 75.0

        screening_service.screen = mock_screen

    if notification_result == "error":
        original_send_doc = notification_service.send_quote_document
        original_send_refusal = notification_service.send_refusal_notice

        def mock_send_doc(*args, **kwargs):
            raise Exception("notification_service_error")

        def mock_send_refusal(*args, **kwargs):
            raise Exception("notification_service_error")

        notification_service.send_quote_document = mock_send_doc
        notification_service.send_refusal_notice = mock_send_refusal

    quote_api = QuoteAPI(
        quote_store, screening_service, tariff_engine, notification_service
    )

    result = quote_api.request_quote(
        shipper_id, weight_kg, distance_km, declared_value
    )
    return result