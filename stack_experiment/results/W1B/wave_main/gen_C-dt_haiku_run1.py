import uuid
from typing import Optional


class ScreeningService:
    def screen(self, shipper_id: str, screening_result: Optional[int] = None) -> int:
        if screening_result is not None:
            return screening_result
        return 0


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float, tariff_result: Optional[float] = None) -> float:
        if tariff_result is not None:
            return tariff_result
        base_rate = 0.5
        distance_multiplier = 1.0 + (distance_km / 1000.0)
        return weight_kg * base_rate * distance_multiplier


class QuoteStore:
    def __init__(self):
        self.quotes = {}

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, 
                    declared_value: float, store_result: Optional[str] = None) -> str:
        if store_result == "unavailable":
            raise Exception("store_unavailable")
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None
        }
        return quote_id

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        if quote_id in self.quotes:
            self.quotes[quote_id]["status"] = status
            if price is not None:
                self.quotes[quote_id]["price"] = price
            return self.quotes[quote_id]
        raise Exception("quote_not_found")


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float, 
                           notification_result: Optional[str] = None) -> str:
        if notification_result == "error":
            return "failed"
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str, 
                           notification_result: Optional[str] = None) -> str:
        if notification_result == "error":
            return "failed"
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 30
    REVIEW_MIN = 31
    REVIEW_MAX = 70
    REFUSE_MIN = 71

    def __init__(self, screening_service: ScreeningService, tariff_engine: TariffEngine,
                 quote_store: QuoteStore, notification_service: NotificationService):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service

    def validate_request(self, shipper_id: str, weight_kg: float, distance_km: float,
                        declared_value: float) -> tuple[bool, Optional[str]]:
        if not shipper_id or len(shipper_id) < 1:
            return False, "shipper_id required"
        if weight_kg < 3 or weight_kg > 19400:
            return False, "weight_kg out of bounds"
        if distance_km < 25 or distance_km > 7150:
            return False, "distance_km out of bounds"
        if declared_value < 50 or declared_value > 83000:
            return False, "declared_value out of bounds"
        return True, None

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float,
                     declared_value: float, screening_result: Optional[int] = None,
                     tariff_result: Optional[float] = None, store_result: Optional[str] = None,
                     notification_result: Optional[str] = None) -> dict:
        valid, error_msg = self.validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if not valid:
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km,
                                                     declared_value, store_result)
        except Exception:
            return {"status": "error: store_unavailable"}

        screening_available = True
        try:
            risk_index = self.screening_service.screen(shipper_id, screening_result)
        except Exception:
            screening_available = False
            risk_index = None

        if not screening_available:
            price = self.tariff_engine.price(weight_kg, distance_km, tariff_result)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }

        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km, tariff_result)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price,
                                                         notification_result)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id,
                                                         notification_result)
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }

        return {"status": "error: unknown_state"}


def handle(request: dict) -> dict:
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)

    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)

    screening_result = None
    if "screening_service_result" in request:
        screening_result = request["screening_service_result"]

    tariff_result = None
    if "tariff_engine_result" in request:
        tariff_result = request["tariff_engine_result"]

    store_result = None
    if "quote_store_result" in request:
        store_result = request["quote_store_result"]

    notification_result = None
    if "notification_service_result" in request:
        notification_result = request["notification_service_result"]

    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value,
                            screening_result=screening_result,
                            tariff_result=tariff_result,
                            store_result=store_result,
                            notification_result=notification_result)