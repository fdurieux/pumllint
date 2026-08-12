import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass
class QuoteRequest:
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float


@dataclass
class QuoteRecord:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: str
    price: Optional[float] = None


class ScreeningService:
    def screen(self, shipper_id: str) -> int:
        return 0


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base_rate = 0.5
        weight_charge = weight_kg * 0.01
        distance_charge = distance_km * 0.02
        return base_rate + weight_charge + distance_charge


class QuoteStore:
    def __init__(self):
        self.quotes = {}

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = QuoteRecord(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status="draft"
        )
        return quote_id

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> QuoteRecord:
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        record = self.quotes[quote_id]
        record.status = status
        if price is not None:
            record.price = price
        return record


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class QuoteAPI:
    def __init__(self, screening_service: ScreeningService, tariff_engine: TariffEngine,
                 quote_store: QuoteStore, notification_service: NotificationService):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service

    def validate_request(self, req: QuoteRequest) -> tuple[bool, Optional[str]]:
        if not req.shipper_id or len(req.shipper_id) < 1:
            return False, "shipper_id invalid"
        if req.weight_kg < 3 or req.weight_kg > 19400:
            return False, "weight_kg out of bounds"
        if req.distance_km < 25 or req.distance_km > 7150:
            return False, "distance_km out of bounds"
        if req.declared_value < 50 or req.declared_value > 83000:
            return False, "declared_value out of bounds"
        return True, None

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        req = QuoteRequest(shipper_id=shipper_id, weight_kg=weight_kg, distance_km=distance_km, declared_value=declared_value)

        valid, error_reason = self.validate_request(req)
        if not valid:
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception:
            return {"status": "error: store_unavailable"}

        screening_ok = True
        risk_index = None
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception:
            screening_ok = False

        ACCEPT_MAX = 25
        REVIEW_MIN = 26
        REVIEW_MAX = 75
        REFUSE_MIN = 76

        if not screening_ok:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }

        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                pass
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        elif risk_index >= REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }

        return {"status": "error: unknown"}


_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_quote_store = QuoteStore()
_notification_service = NotificationService()
_quote_api = QuoteAPI(_screening_service, _tariff_engine, _quote_store, _notification_service)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    if "screening_result" in request:
        screening_result = request["screening_result"]
        if isinstance(screening_result, (int, float)):
            _screening_service.screen = lambda sid: screening_result
        elif screening_result == "error":
            _screening_service.screen = lambda sid: (_ for _ in ()).throw(Exception("Screening unavailable"))

    if "store_result" in request:
        store_result = request["store_result"]
        if store_result == "error":
            original_store = _quote_store.store_draft
            _quote_store.store_draft = lambda *args, **kwargs: (_ for _ in ()).throw(Exception("Store unavailable"))

    if "notification_result" in request:
        notification_result = request["notification_result"]
        if notification_result == "error":
            _notification_service.send_quote_document = lambda *args, **kwargs: (_ for _ in ()).throw(Exception("Notification failed"))
            _notification_service.send_refusal_notice = lambda *args, **kwargs: (_ for _ in ()).throw(Exception("Notification failed"))

    result = _quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)

    _screening_service.screen = ScreeningService().screen
    _quote_store.store_draft = QuoteStore().store_draft
    _notification_service.send_quote_document = NotificationService().send_quote_document
    _notification_service.send_refusal_notice = NotificationService().send_refusal_notice

    return result