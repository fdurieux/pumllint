from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime
import uuid


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


class ValidationError(Exception):
    pass


class StorageUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price_amount: Optional[float] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class QuoteStore:
    def __init__(self):
        self.quotes: dict[str, Quote] = {}
        self._available = True

    def set_available(self, available: bool):
        self._available = available

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        if not self._available:
            raise StorageUnavailableError("Quote store unavailable")

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

    def update_quote(
        self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None
    ) -> Quote:
        if not self._available:
            raise StorageUnavailableError("Quote store unavailable")

        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")

        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        quote.updated_at = datetime.utcnow().isoformat()
        return quote

    def get_quote(self, quote_id: str) -> Optional[Quote]:
        return self.quotes.get(quote_id)


class ScreeningService:
    def __init__(self):
        self._available = True
        self._risk_index_override: Optional[float] = None

    def set_available(self, available: bool):
        self._available = available

    def set_risk_index(self, risk_index: float):
        self._risk_index_override = risk_index

    def screen(self, shipper_id: str) -> float:
        if not self._available:
            raise ScreeningUnavailableError("Screening service unavailable")

        if self._risk_index_override is not None:
            return self._risk_index_override

        return 25.0


class TariffEngine:
    PRICE_PER_KG = 0.5
    PRICE_PER_KM = 0.1
    BASE_PRICE = 50.0

    def __init__(self):
        self._available = True
        self._price_override: Optional[float] = None

    def set_available(self, available: bool):
        self._available = available

    def set_price(self, price: float):
        self._price_override = price

    def price(self, weight_kg: float, distance_km: float) -> float:
        if not self._available:
            raise Exception("Tariff engine unavailable")

        if self._price_override is not None:
            return self._price_override

        return self.BASE_PRICE + (weight_kg * self.PRICE_PER_KG) + (
            distance_km * self.PRICE_PER_KM
        )


class NotificationService:
    def __init__(self):
        self._available = True
        self.sent_messages: list[dict] = []

    def set_available(self, available: bool):
        self._available = available

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        if not self._available:
            return "notification_failed"

        self.sent_messages.append(
            {
                "type": "quote_document",
                "shipper_id": shipper_id,
                "quote_id": quote_id,
                "price_amount": price_amount,
            }
        )
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if not self._available:
            return "notification_failed"

        self.sent_messages.append(
            {
                "type": "refusal_notice",
                "shipper_id": shipper_id,
                "quote_id": quote_id,
            }
        )
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 30.0
    REVIEW_MIN = 31.0
    REVIEW_MAX = 70.0
    REFUSE_MIN = 71.0

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
        if weight_kg <= 0 or weight_kg > 10000:
            return False
        if distance_km <= 0 or distance_km > 5000:
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
            return {"status": "rejected", "reason": "invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageUnavailableError:
            return {"status": "error", "reason": "store_unavailable"}

        risk_index: Optional[float] = None
        screening_failed = False

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            screening_failed = True

        if risk_index is not None:
            if risk_index <= self.ACCEPT_MAX:
                try:
                    price_amount = self.tariff_engine.price(weight_kg, distance_km)
                    self.quote_store.update_quote(
                        quote_id, QuoteStatus.QUOTED, price_amount
                    )
                    self.notification_service.send_quote_document(
                        shipper_id, quote_id, price_amount
                    )
                    return {
                        "status": "confirmed",
                        "quote_id": quote_id,
                        "price": price_amount,
                    }
                except Exception as e:
                    return {"status": "error", "reason": str(e)}

            elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
                return {"status": "review_hold", "quote_id": quote_id}

            elif risk_index >= self.REFUSE_MIN:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
                return {"status": "rejected", "reason": "screening_refused"}

        if screening_failed:
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, QuoteStatus.HELD_UNSCREENED, price_amount
                )
                return {"status": "held_unscreened", "quote_id": quote_id}
            except Exception as e:
                return {"status": "error", "reason": str(e)}

        return {"status": "error", "reason": "unknown_state"}


_global_quote_store = QuoteStore()
_global_screening_service = ScreeningService()
_global_tariff_engine = TariffEngine()
_global_notification_service = NotificationService()
_global_quote_api = QuoteAPI(
    _global_quote_store,
    _global_screening_service,
    _global_tariff_engine,
    _global_notification_service,
)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)

    if "store_available" in request:
        _global_quote_store.set_available(request["store_available"])

    if "screening_available" in request:
        _global_screening_service.set_available(request["screening_available"])

    if "screening_risk_index" in request:
        _global_screening_service.set_risk_index(request["screening_risk_index"])

    if "tariff_price" in request:
        _global_tariff_engine.set_price(request["tariff_price"])

    if "notification_available" in request:
        _global_notification_service.set_available(request["notification_available"])

    result = _global_quote_api.request_quote(
        shipper_id, weight_kg, distance_km, declared_value
    )

    return result