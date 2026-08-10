import uuid
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP

ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

VALIDATION_RULES = {
    "weight_kg": {"min": 3, "max": 19400},
    "distance_km": {"min": 25, "max": 7150},
    "declared_value": {"min": 50, "max": 83000},
}


class ScreeningService:
    def screen(self, shipper_id: str, screening_result: Optional[int] = None, screening_status: Optional[str] = None) -> int:
        if screening_status == "unavailable":
            raise Exception("screening_unavailable")
        if screening_result is not None:
            return screening_result
        return 0


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        base = Decimal(str(0.87 * weight_kg + 1.13 * distance_km))
        if weight_kg > 1244:
            base += Decimal("316.00")
        if distance_km >= 4912:
            base *= Decimal("1.19")
        result = float(base)
        return round(result, 2)


class QuoteStore:
    def __init__(self):
        self.quotes = {}

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float, store_status: Optional[str] = None) -> str:
        if store_status == "unavailable":
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

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        if quote_id not in self.quotes:
            raise Exception(f"quote_not_found: {quote_id}")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        return self.quotes[quote_id]


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float, notification_status: Optional[str] = None) -> str:
        if notification_status == "error":
            raise Exception("notification_error")
        return f"quote_document_sent_to_{shipper_id}"

    def send_refusal_notice(self, shipper_id: str, quote_id: str, notification_status: Optional[str] = None) -> str:
        if notification_status == "error":
            raise Exception("notification_error")
        return f"refusal_notice_sent_to_{shipper_id}"


class QuoteAPI:
    def __init__(self, screening_service: ScreeningService, tariff_engine: TariffEngine, quote_store: QuoteStore, notification_service: NotificationService):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service

    def validate_request(self, request: dict) -> tuple[bool, Optional[str]]:
        if "shipper_id" not in request or not request["shipper_id"]:
            return False, "shipper_id missing or empty"
        for field in ["weight_kg", "distance_km", "declared_value"]:
            if field not in request:
                return False, f"{field} missing"
            value = request[field]
            rules = VALIDATION_RULES[field]
            if value < rules["min"] or value > rules["max"]:
                return False, f"{field} out of range"
        return True, None

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float, 
                      screening_result: Optional[int] = None, screening_status: Optional[str] = None,
                      store_status: Optional[str] = None, notification_status: Optional[str] = None) -> dict:
        request = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
        }

        valid, error = self.validate_request(request)
        if not valid:
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value, store_status)
        except Exception as e:
            if "store_unavailable" in str(e):
                return {"status": "error: store_unavailable"}
            raise

        try:
            risk_index = self.screening_service.screen(shipper_id, screening_result, screening_status)
        except Exception as e:
            if "screening_unavailable" in str(e):
                price = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, "held_unscreened", price)
                return {
                    "status": "held_unscreened",
                    "quote_id": quote_id,
                    "price": price,
                    "hold": True,
                }
            raise

        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price, notification_status)
            except Exception:
                pass
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        else:
            self.quote_store.update_quote(quote_id, "refused_screening")
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id, notification_status)
            except Exception:
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }


_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_quote_store = QuoteStore()
_notification_service = NotificationService()
_api = QuoteAPI(_screening_service, _tariff_engine, _quote_store, _notification_service)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "test-shipper")
    weight_kg = request.get("weight_kg", 500)
    distance_km = request.get("distance_km", 1000)
    declared_value = request.get("declared_value", 10000)

    screening_result = request.get("screening_result")
    screening_status = request.get("screening_status")
    store_status = request.get("store_status")
    notification_status = request.get("notification_status")

    try:
        result = _api.request_quote(
            shipper_id,
            weight_kg,
            distance_km,
            declared_value,
            screening_result=screening_result,
            screening_status=screening_status,
            store_status=store_status,
            notification_status=notification_status,
        )
        return result
    except Exception as e:
        return {"status": f"error: {str(e)}"}