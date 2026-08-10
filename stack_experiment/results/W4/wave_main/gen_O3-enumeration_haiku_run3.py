import uuid
from abc import ABC, abstractmethod


class ScreeningService(ABC):
    @abstractmethod
    def screen(self, shipper_id: str) -> int:
        pass


class TariffEngine(ABC):
    @abstractmethod
    def price(self, weight_kg: float, distance_km: float) -> float:
        pass


class QuoteStore(ABC):
    @abstractmethod
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        pass

    @abstractmethod
    def update_quote(self, quote_id: str, status: str, price: float = None) -> dict:
        pass


class NotificationService(ABC):
    @abstractmethod
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        pass

    @abstractmethod
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        pass


class DefaultScreeningService(ScreeningService):
    def __init__(self):
        self.result = None
        self.available = True

    def screen(self, shipper_id: str) -> int:
        if not self.available:
            raise Exception("screening_unavailable")
        return self.result if self.result is not None else 0


class DefaultTariffEngine(TariffEngine):
    def price(self, weight_kg: float, distance_km: float) -> float:
        base = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            base += 316.00
        if distance_km >= 4912:
            base *= 1.19
        return round(base, 2)


class DefaultQuoteStore(QuoteStore):
    def __init__(self):
        self.quotes = {}
        self.available = True

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if not self.available:
            raise Exception("store_unavailable")
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "quote_id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id: str, status: str, price: float = None) -> dict:
        if quote_id not in self.quotes:
            raise Exception("quote_not_found")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        return self.quotes[quote_id]


class DefaultNotificationService(NotificationService):
    def __init__(self):
        self.available = True

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        if not self.available:
            raise Exception("notification_unavailable")
        return "quote_document_sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if not self.available:
            raise Exception("notification_unavailable")
        return "refusal_notice_sent"


class QuoteAPI:
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def __init__(
        self,
        screening_service: ScreeningService,
        tariff_engine: TariffEngine,
        quote_store: QuoteStore,
        notification_service: NotificationService,
    ):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service

    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        if not shipper_id or len(shipper_id) == 0:
            return False
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False
        return True

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception as e:
            if "store_unavailable" in str(e):
                return {"status": "error: store_unavailable"}
            raise

        risk_index = None
        screening_failed = False
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception as e:
            if "screening_unavailable" in str(e):
                screening_failed = True
            else:
                raise

        if screening_failed:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {"status": "held_unscreened", "quote_id": quote_id, "price": price, "hold": True}

        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                pass
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass
            return {"status": "refused_screening", "quote_id": quote_id}


_global_screening_service = DefaultScreeningService()
_global_tariff_engine = DefaultTariffEngine()
_global_quote_store = DefaultQuoteStore()
_global_notification_service = DefaultNotificationService()
_global_api = QuoteAPI(
    _global_screening_service,
    _global_tariff_engine,
    _global_quote_store,
    _global_notification_service,
)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    if "screening_result" in request:
        _global_screening_service.result = request["screening_result"]
    if "screening_status" in request and request["screening_status"] == "unavailable":
        _global_screening_service.available = False
    else:
        _global_screening_service.available = True

    if "store_status" in request and request["store_status"] == "unavailable":
        _global_quote_store.available = False
    else:
        _global_quote_store.available = True

    if "notification_status" in request and request["notification_status"] == "failed":
        _global_notification_service.available = False
    else:
        _global_notification_service.available = True

    result = _global_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    return result