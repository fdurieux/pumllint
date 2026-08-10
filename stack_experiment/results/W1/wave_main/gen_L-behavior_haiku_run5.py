import uuid
from typing import Optional


class ScreeningService:
    def __init__(self):
        self.risk_index: Optional[int] = None
        self.available = True

    def get_risk_index(self, shipper_id: str) -> int:
        if not self.available:
            raise RuntimeError("screening_unavailable")
        if self.risk_index is None:
            raise RuntimeError("screening_not_configured")
        return self.risk_index


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

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if not self.available:
            raise RuntimeError("store_unavailable")
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

    def update_status(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        if quote_id in self.quotes:
            self.quotes[quote_id]["status"] = status
            if price is not None:
                self.quotes[quote_id]["price"] = price


class NotificationService:
    def __init__(self):
        self.available = True
        self.notifications_sent = []

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        if not self.available:
            raise RuntimeError("notification_unavailable")
        self.notifications_sent.append(("quote_document", shipper_id, quote_id, price))
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if not self.available:
            raise RuntimeError("notification_unavailable")
        self.notifications_sent.append(("refusal_notice", shipper_id, quote_id))
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def __init__(self, screening_service: ScreeningService, tariff_engine: TariffEngine,
                 quote_store: QuoteStore, notification_service: NotificationService):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service

    def _validate_request(self, request: dict) -> tuple[bool, Optional[str]]:
        if "shipper_id" not in request or not request["shipper_id"]:
            return False, "shipper_id missing or empty"
        if "weight_kg" not in request:
            return False, "weight_kg missing"
        weight_kg = request["weight_kg"]
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False, "weight_kg out of range"
        if "distance_km" not in request:
            return False, "distance_km missing"
        distance_km = request["distance_km"]
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False, "distance_km out of range"
        if "declared_value" not in request:
            return False, "declared_value missing"
        declared_value = request["declared_value"]
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False, "declared_value out of range"
        return True, None

    def request_quote(self, request: dict) -> dict:
        valid, error_msg = self._validate_request(request)
        if not valid:
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except RuntimeError as e:
            if "store_unavailable" in str(e):
                return {"status": "error: store_unavailable"}
            raise

        screening_available = True
        risk_index = None
        try:
            risk_index = self.screening_service.get_risk_index(shipper_id)
        except RuntimeError as e:
            if "screening_unavailable" in str(e):
                screening_available = False
            else:
                raise

        if not screening_available:
            price = self.tariff_engine.compute_price(weight_kg, distance_km)
            self.quote_store.update_status(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }

        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.compute_price(weight_kg, distance_km)
            self.quote_store.update_status(quote_id, "quoted", price)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except RuntimeError:
                pass
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_status(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_status(quote_id, "refused_screening")
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except RuntimeError:
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }

        return {"status": "error: unknown_screening_result"}


_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_quote_store = QuoteStore()
_notification_service = NotificationService()
_quote_api = QuoteAPI(_screening_service, _tariff_engine, _quote_store, _notification_service)


def handle(request: dict) -> dict:
    _screening_service.available = True
    _quote_store.available = True
    _notification_service.available = True
    _screening_service.risk_index = None

    if "screening_result" in request:
        if request["screening_result"] == "unavailable":
            _screening_service.available = False
        else:
            try:
                _screening_service.risk_index = int(request["screening_result"])
            except (ValueError, TypeError):
                pass

    if "store_result" in request and request["store_result"] == "unavailable":
        _quote_store.available = False

    if "notification_result" in request and request["notification_result"] == "failed":
        _notification_service.available = False

    request_payload = {
        "shipper_id": request.get("shipper_id", "TEST-SHIPPER"),
        "weight_kg": request.get("weight_kg", 600),
        "distance_km": request.get("distance_km", 1200),
        "declared_value": request.get("declared_value", 5000)
    }

    return _quote_api.request_quote(request_payload)