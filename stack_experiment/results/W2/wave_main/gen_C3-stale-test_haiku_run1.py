import uuid
import json
from typing import Any


class ScreeningService:
    def screen(self, shipper_id: str, screening_result: Any = None) -> int:
        if screening_result == "unavailable":
            raise Exception("screening_unavailable")
        if screening_result == "error":
            raise Exception("screening_unavailable")
        return screening_result if isinstance(screening_result, int) else 0


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

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float, store_result: Any = None) -> str:
        if store_result == "unavailable":
            raise Exception("store_unavailable")
        if store_result == "error":
            raise Exception("store_unavailable")
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

    def update_quote(self, quote_id: str, status: str, price: float = None) -> dict:
        if quote_id in self.quotes:
            self.quotes[quote_id]["status"] = status
            if price is not None:
                self.quotes[quote_id]["price"] = price
            return self.quotes[quote_id]
        raise Exception("quote_not_found")


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float, notification_result: Any = None) -> str:
        if notification_result == "error":
            raise Exception("notification_failed")
        if notification_result == "failed":
            raise Exception("notification_failed")
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str, notification_result: Any = None) -> str:
        if notification_result == "error":
            raise Exception("notification_failed")
        if notification_result == "failed":
            raise Exception("notification_failed")
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def __init__(self, tariff_engine: TariffEngine, quote_store: QuoteStore, screening_service: ScreeningService, notification_service: NotificationService):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        if not shipper_id or shipper_id.strip() == "":
            return False
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False
        return True

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float, store_result: Any = None, screening_result: Any = None, notification_result: Any = None) -> dict:
        if not self.validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value, store_result)
        except Exception as e:
            if "store_unavailable" in str(e):
                return {"status": "error: store_unavailable"}
            raise

        try:
            risk_index = self.screening_service.screen(shipper_id, screening_result)
        except Exception as e:
            if "screening_unavailable" in str(e):
                try:
                    price = self.tariff_engine.price(weight_kg, distance_km)
                    self.quote_store.update_quote(quote_id, "held_unscreened", price)
                    return {"status": "held_unscreened", "quote_id": quote_id, "price": price, "hold": True}
                except Exception:
                    return {"status": "error: store_unavailable", "quote_id": quote_id}
            raise

        if risk_index <= self.ACCEPT_MAX:
            try:
                price = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, "quoted", price)
                try:
                    self.notification_service.send_quote_document(shipper_id, quote_id, price, notification_result)
                except Exception:
                    pass
                return {"status": "quoted", "quote_id": quote_id, "price": price}
            except Exception as e:
                return {"status": "error: store_unavailable", "quote_id": quote_id}

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            try:
                self.quote_store.update_quote(quote_id, "review_hold")
                return {"status": "review_hold", "quote_id": quote_id}
            except Exception:
                return {"status": "error: store_unavailable", "quote_id": quote_id}

        elif risk_index >= self.REFUSE_MIN:
            try:
                self.quote_store.update_quote(quote_id, "refused_screening")
                try:
                    self.notification_service.send_refusal_notice(shipper_id, quote_id, notification_result)
                except Exception:
                    pass
                return {"status": "refused_screening", "quote_id": quote_id}
            except Exception:
                return {"status": "error: store_unavailable", "quote_id": quote_id}

        return {"status": "error: store_unavailable", "quote_id": quote_id}


_tariff_engine = TariffEngine()
_quote_store = QuoteStore()
_screening_service = ScreeningService()
_notification_service = NotificationService()
_quote_api = QuoteAPI(_tariff_engine, _quote_store, _screening_service, _notification_service)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    store_result = request.get("quote_store_result")
    screening_result = request.get("screening_service_result")
    notification_result = request.get("notification_service_result")

    return _quote_api.request_quote(
        shipper_id,
        weight_kg,
        distance_km,
        declared_value,
        store_result=store_result,
        screening_result=screening_result,
        notification_result=notification_result,
    )