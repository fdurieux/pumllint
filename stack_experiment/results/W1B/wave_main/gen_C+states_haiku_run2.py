import json
from datetime import datetime
from enum import Enum
from typing import Optional


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


class ScreeningService:
    def screen(self, shipper_id: str) -> int:
        return 0


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base_rate = 0.5
        return weight_kg * distance_km * base_rate


class QuoteStore:
    def __init__(self):
        self.quotes = {}
        self.next_id = 1

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        quote_id = f"Q{self.next_id}"
        self.next_id += 1
        self.quotes[quote_id] = {
            "id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": QuoteStatus.DRAFT.value,
            "price": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        return quote_id

    def update_quote(
        self, quote_id: str, status: QuoteStatus, price: Optional[float] = None
    ) -> dict:
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self.quotes[quote_id]["status"] = status.value
        if price is not None:
            self.quotes[quote_id]["price"] = price
        self.quotes[quote_id]["updated_at"] = datetime.now().isoformat()
        return self.quotes[quote_id]

    def get_quote(self, quote_id: str) -> Optional[dict]:
        return self.quotes.get(quote_id)


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 30
    REVIEW_MIN = 31
    REVIEW_MAX = 70
    REFUSE_MIN = 71

    def __init__(
        self,
        tariff_engine: TariffEngine,
        quote_store: QuoteStore,
        screening_service: ScreeningService,
        notification_service: NotificationService,
    ):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate_request(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> bool:
        if not shipper_id or shipper_id.strip() == "":
            return False
        if weight_kg <= 0 or weight_kg > 10000:
            return False
        if distance_km <= 0 or distance_km > 5000:
            return False
        if declared_value < 0 or declared_value > 1000000:
            return False
        return True

    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected", "reason": "invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except Exception:
            return {"status": "error", "reason": "storage_unavailable"}

        screening_result = self._do_screening(shipper_id)

        if screening_result["available"]:
            risk_index = screening_result["risk_index"]

            if risk_index <= self.ACCEPT_MAX:
                return self._handle_accept(quote_id, shipper_id, weight_kg, distance_km)
            elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
                return self._handle_review(quote_id)
            elif risk_index >= self.REFUSE_MIN:
                return self._handle_refuse(quote_id, shipper_id)
        else:
            return self._handle_screening_unavailable(
                quote_id, shipper_id, weight_kg, distance_km
            )

    def _do_screening(self, shipper_id: str) -> dict:
        try:
            risk_index = self.screening_service.screen(shipper_id)
            return {"available": True, "risk_index": risk_index}
        except Exception:
            return {"available": False}

    def _handle_accept(
        self, quote_id: str, shipper_id: str, weight_kg: float, distance_km: float
    ) -> dict:
        price = self.tariff_engine.price(weight_kg, distance_km)
        self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price)
        self.notification_service.send_quote_document(shipper_id, quote_id, price)
        return {
            "status": "quoted",
            "quote_id": quote_id,
            "price": price,
        }

    def _handle_review(self, quote_id: str) -> dict:
        self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
        return {
            "status": "review_hold",
            "quote_id": quote_id,
        }

    def _handle_refuse(self, quote_id: str, shipper_id: str) -> dict:
        self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
        self.notification_service.send_refusal_notice(shipper_id, quote_id)
        return {
            "status": "refused",
            "quote_id": quote_id,
            "reason": "screening",
        }

    def _handle_screening_unavailable(
        self, quote_id: str, shipper_id: str, weight_kg: float, distance_km: float
    ) -> dict:
        price = self.tariff_engine.price(weight_kg, distance_km)
        self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price)
        return {
            "status": "held_unscreened",
            "quote_id": quote_id,
            "price": price,
        }


_global_store = QuoteStore()
_global_screening = ScreeningService()
_global_tariff = TariffEngine()
_global_notification = NotificationService()
_global_api = QuoteAPI(_global_tariff, _global_store, _global_screening, _global_notification)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)

    if "screening_result" in request:
        screening_result = request["screening_result"]
        if screening_result == "approved":
            _global_screening.screen = lambda x: 20
        elif screening_result == "review":
            _global_screening.screen = lambda x: 50
        elif screening_result == "declined":
            _global_screening.screen = lambda x: 80
        elif screening_result == "error":
            _global_screening.screen = lambda x: (_ for _ in ()).throw(
                Exception("Screening unavailable")
            )
        elif isinstance(screening_result, int):
            _global_screening.screen = lambda x: screening_result

    if "tariff_price" in request:
        _global_tariff.price = lambda w, d: request["tariff_price"]

    if "store_status" in request:
        store_status = request["store_status"]
        if store_status == "error":
            original_store = _global_store.store_draft

            def store_fail(*args, **kwargs):
                raise StorageUnavailableError("Store unavailable")

            _global_store.store_draft = store_fail

    if "notify_status" in request:
        notify_status = request["notify_status"]
        if notify_status == "error":
            _global_notification.send_quote_document = lambda s, q, p: (_ for _ in ()).throw(
                Exception("Notification failed")
            )
            _global_notification.send_refusal_notice = lambda s, q: (_ for _ in ()).throw(
                Exception("Notification failed")
            )

    try:
        result = _global_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
        return result
    except Exception as e:
        return {"status": "error", "reason": str(e)}