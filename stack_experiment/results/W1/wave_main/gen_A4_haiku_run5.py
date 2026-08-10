import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


class ScreeningService:
    def __init__(self, result: Optional[int] = None, status: Optional[str] = None):
        self.result = result
        self.status = status

    def screen(self, shipper_id: str) -> int:
        if self.status == "unavailable":
            raise ScreeningUnavailableError("Screening service unavailable")
        if self.result is not None:
            return self.result
        return 10


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base = Decimal("0.87") * Decimal(str(weight_kg)) + Decimal("1.13") * Decimal(str(distance_km))
        if weight_kg > 1244:
            base += Decimal("316.00")
        if distance_km >= 4912:
            base *= Decimal("1.19")
        result = base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(result)


class QuoteStore:
    def __init__(self, store_status: Optional[str] = None):
        self.store_status = store_status
        self.quotes = {}

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if self.store_status == "unavailable":
            raise StoreUnavailableError("Quote store unavailable")
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
        if quote_id in self.quotes:
            self.quotes[quote_id]["status"] = status
            if price is not None:
                self.quotes[quote_id]["price"] = price
            return self.quotes[quote_id]
        return {}


class NotificationService:
    def __init__(self, delivery_status: Optional[str] = None):
        self.delivery_status = delivery_status
        self.notifications = []

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        if self.delivery_status == "error":
            raise NotificationError("Notification delivery failed")
        self.notifications.append({
            "type": "quote_document",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
            "price": price,
        })
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if self.delivery_status == "error":
            raise NotificationError("Notification delivery failed")
        self.notifications.append({
            "type": "refusal_notice",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
        })
        return "sent"


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

    def validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        if not shipper_id or shipper_id == "":
            return False
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False
        return True

    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        if not self.validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        screening_available = True
        risk_index = None

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            screening_available = False

        if not screening_available:
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
            except NotificationError:
                pass
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }

        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }

        if risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except NotificationError:
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }

        return {"status": "error: unknown_screening_result"}


class ScreeningUnavailableError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class NotificationError(Exception):
    pass


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)

    screening_result = request.get("screening_service_result")
    screening_status = request.get("screening_service_status")
    store_status = request.get("quote_store_status")
    notification_status = request.get("notification_service_status")

    screening_service = ScreeningService(result=screening_result, status=screening_status)
    tariff_engine = TariffEngine()
    quote_store = QuoteStore(store_status=store_status)
    notification_service = NotificationService(delivery_status=notification_status)

    quote_api = QuoteAPI(
        screening_service=screening_service,
        tariff_engine=tariff_engine,
        quote_store=quote_store,
        notification_service=notification_service,
    )

    return quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)