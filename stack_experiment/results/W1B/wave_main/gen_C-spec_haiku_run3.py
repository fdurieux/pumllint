from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class QuoteRequest:
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


class ScreeningService:
    def screen(self, shipper_id: str) -> int:
        return 0


class NotificationService:
    def send_quote_document(
        self, shipper_id: str, quote_id: str, price_amount: float
    ) -> str:
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            base += 316.00
        if distance_km >= 4912:
            base *= 1.19
        return round(base, 2)


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
        quote_id = f"Q{self.next_id}"
        self.next_id += 1
        self.quotes[quote_id] = {
            "quote_id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
            "created_at": datetime.now().isoformat(),
        }
        return quote_id

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None):
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        return self.quotes[quote_id]


class QuoteAPI:
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

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

    def _validate_request(self, request: QuoteRequest) -> None:
        if not request.shipper_id or request.shipper_id.strip() == "":
            raise ValidationError("shipper_id is required and non-empty")
        if request.weight_kg < 3 or request.weight_kg > 19400:
            raise ValidationError("weight_kg must be between 3 and 19400")
        if request.distance_km < 25 or request.distance_km > 7150:
            raise ValidationError("distance_km must be between 25 and 7150")
        if request.declared_value < 50 or request.declared_value > 83000:
            raise ValidationError("declared_value must be between 50 and 83000")

    def request_quote(self, request: QuoteRequest) -> dict:
        try:
            self._validate_request(request)
        except ValidationError:
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(
                request.shipper_id,
                request.weight_kg,
                request.distance_km,
                request.declared_value,
            )
        except StorageError:
            return {"status": "error: store_unavailable"}

        try:
            risk_index = self.screening_service.screen(request.shipper_id)
        except ScreeningError:
            price = self.tariff_engine.price(request.weight_kg, request.distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(request.weight_kg, request.distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(
                request.shipper_id, quote_id, price
            )
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(request.shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)

    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()

    quote_api = QuoteAPI(
        quote_store, screening_service, tariff_engine, notification_service
    )

    if "store_result" in request:
        if request["store_result"] != "stored":
            quote_store.store_draft = lambda *args, **kwargs: (_ for _ in ()).throw(
                StorageError("Store unavailable")
            )

    if "screening_result" in request:
        screening_service.screen = lambda *args, **kwargs: int(
            request["screening_result"]
        )
    elif "screening_status" in request:
        if request["screening_status"] != "assessed":
            screening_service.screen = lambda *args, **kwargs: (_ for _ in ()).throw(
                ScreeningError("Screening unavailable")
            )

    if "notification_result" in request:
        if request["notification_result"] != "sent":
            notification_service.send_quote_document = lambda *args, **kwargs: (
                _ for _ in ()
            ).throw(Exception("Notification failed"))
            notification_service.send_refusal_notice = lambda *args, **kwargs: (
                _ for _ in ()
            ).throw(Exception("Notification failed"))

    quote_request = QuoteRequest(
        shipper_id=shipper_id,
        weight_kg=weight_kg,
        distance_km=distance_km,
        declared_value=declared_value,
    )

    try:
        result = quote_api.request_quote(quote_request)
        return result
    except Exception as e:
        return {"status": f"error: {str(e)}"}