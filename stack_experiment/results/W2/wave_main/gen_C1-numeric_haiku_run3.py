import uuid
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP


class ScreeningService:
    def __init__(self):
        self.unavailable = False
        self.risk_index = 0

    def screen(self, shipper_id: str) -> int:
        if self.unavailable:
            raise ScreeningUnavailableError()
        return self.risk_index


class ScreeningUnavailableError(Exception):
    pass


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base = Decimal(str(0.87 * weight_kg + 1.13 * distance_km))
        if weight_kg > 1244:
            base += Decimal("316.00")
        if distance_km >= 4912:
            base *= Decimal("1.19")
        result = base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(result)


class QuoteStore:
    def __init__(self):
        self.unavailable = False
        self.quotes = {}

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        if self.unavailable:
            raise StoreUnavailableError()
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        return self.quotes[quote_id]


class StoreUnavailableError(Exception):
    pass


class NotificationService:
    def __init__(self):
        self.failed = False
        self.last_action = None
        self.last_shipper_id = None

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        self.last_action = "quote_document"
        self.last_shipper_id = shipper_id
        if self.failed:
            raise NotificationFailureError()
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        self.last_action = "refusal_notice"
        self.last_shipper_id = shipper_id
        if self.failed:
            raise NotificationFailureError()
        return "sent"


class NotificationFailureError(Exception):
    pass


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

    def validate_request(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> bool:
        if not shipper_id or len(str(shipper_id).strip()) == 0:
            return False
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False
        if (
            not isinstance(declared_value, (int, float))
            or declared_value < 50
            or declared_value > 83000
        ):
            return False
        return True

    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        if not self.validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        screening_failed = False
        risk_index = None

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            screening_failed = True

        if screening_failed:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except NotificationFailureError:
                pass
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except NotificationFailureError:
                pass
            return {"status": "refused_screening", "quote_id": quote_id}


_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_quote_store = QuoteStore()
_notification_service = NotificationService()
_quote_api = QuoteAPI(
    _screening_service, _tariff_engine, _quote_store, _notification_service
)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)

    if request.get("store_unavailable"):
        _quote_store.unavailable = True
    else:
        _quote_store.unavailable = False

    if request.get("screening_unavailable"):
        _screening_service.unavailable = True
    else:
        _screening_service.unavailable = False
        if "screening_result" in request:
            _screening_service.risk_index = request["screening_result"]

    if request.get("notification_failed"):
        _notification_service.failed = True
    else:
        _notification_service.failed = False

    response = _quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    return response