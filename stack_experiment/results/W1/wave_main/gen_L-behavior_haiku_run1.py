import json
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class QuoteRequest:
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float


class ScreeningService:
    def __init__(self, risk_index: Optional[int] = None, available: bool = True):
        self.risk_index = risk_index
        self.available = available

    def get_risk_index(self, shipper_id: str) -> int:
        if not self.available:
            raise ScreeningUnavailableError()
        return self.risk_index


class ScreeningUnavailableError(Exception):
    pass


class TariffEngine:
    def compute_price(self, weight_kg: float, distance_km: float) -> float:
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        if weight_kg > 1244:
            base += 316.00
        
        if distance_km >= 4912:
            base *= 1.19
        
        return round(base, 2)


class QuoteStore:
    def __init__(self):
        self.quotes = {}
        self.available = True

    def store_draft(self, request: QuoteRequest) -> str:
        if not self.available:
            raise StoreUnavailableError()
        
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "shipper_id": request.shipper_id,
            "weight_kg": request.weight_kg,
            "distance_km": request.distance_km,
            "declared_value": request.declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_status(self, quote_id: str, status: str) -> str:
        if quote_id in self.quotes:
            self.quotes[quote_id]["status"] = status
        return quote_id

    def update_price(self, quote_id: str, price: float) -> str:
        if quote_id in self.quotes:
            self.quotes[quote_id]["price"] = price
        return quote_id


class StoreUnavailableError(Exception):
    pass


class NotificationService:
    def __init__(self, delivery_fails: bool = False):
        self.delivery_fails = delivery_fails
        self.notifications = []

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        if self.delivery_fails:
            return "delivery_failed"
        self.notifications.append({
            "type": "quote_document",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
            "price": price,
        })
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if self.delivery_fails:
            return "delivery_failed"
        self.notifications.append({
            "type": "refusal_notice",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
        })
        return "sent"


class QuoteAPI:
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

    def validate_request(self, request: QuoteRequest) -> bool:
        if not request.shipper_id or request.shipper_id == "":
            return False
        if not (3 <= request.weight_kg <= 19400):
            return False
        if not (25 <= request.distance_km <= 7150):
            return False
        if not (50 <= request.declared_value <= 83000):
            return False
        return True

    def request_quote(self, request_dict: dict) -> dict:
        try:
            request = QuoteRequest(
                shipper_id=request_dict.get("shipper_id", ""),
                weight_kg=request_dict.get("weight_kg"),
                distance_km=request_dict.get("distance_km"),
                declared_value=request_dict.get("declared_value"),
            )
        except (TypeError, ValueError):
            return {"status": "rejected: invalid_request"}

        if not self.validate_request(request):
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(request)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        try:
            risk_index = self.screening_service.get_risk_index(request.shipper_id)
        except ScreeningUnavailableError:
            self.quote_store.update_status(quote_id, "held_unscreened")
            price = self.tariff_engine.compute_price(
                request.weight_kg, request.distance_km
            )
            self.quote_store.update_price(quote_id, price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        ACCEPT_MAX = 41
        REVIEW_MIN = 42
        REVIEW_MAX = 66
        REFUSE_MIN = 67

        if risk_index <= ACCEPT_MAX:
            self.quote_store.update_status(quote_id, "quoted")
            price = self.tariff_engine.compute_price(
                request.weight_kg, request.distance_km
            )
            self.quote_store.update_price(quote_id, price)
            self.notification_service.send_quote_document(
                request.shipper_id, quote_id, price
            )
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_status(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        elif risk_index >= REFUSE_MIN:
            self.quote_store.update_status(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(request.shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }

        return {"status": "error: unknown"}


def handle(request: dict) -> dict:
    screening_available = request.get("screening_service_status") != "unavailable"
    screening_result = request.get("screening_service_result")
    risk_index = screening_result if isinstance(screening_result, int) else None

    store_available = request.get("quote_store_status") != "unavailable"
    notification_fails = request.get("notification_service_status") == "fails"

    screening_service = ScreeningService(
        risk_index=risk_index, available=screening_available
    )
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    quote_store.available = store_available
    notification_service = NotificationService(delivery_fails=notification_fails)

    api = QuoteAPI(
        screening_service=screening_service,
        tariff_engine=tariff_engine,
        quote_store=quote_store,
        notification_service=notification_service,
    )

    quote_request = {
        "shipper_id": request.get("shipper_id", ""),
        "weight_kg": request.get("weight_kg"),
        "distance_km": request.get("distance_km"),
        "declared_value": request.get("declared_value"),
    }

    return api.request_quote(quote_request)