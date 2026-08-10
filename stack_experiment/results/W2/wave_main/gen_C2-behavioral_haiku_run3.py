import uuid
from datetime import datetime
from typing import Optional


class ScreeningService:
    def screen(self, shipper_id: str, risk_index: Optional[int] = None, screening_status: Optional[str] = None) -> Optional[int]:
        if screening_status == "unavailable":
            raise Exception("screening_unavailable")
        if risk_index is not None:
            return risk_index
        return 0


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

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float, store_status: Optional[str] = None) -> str:
        if store_status == "unavailable":
            raise Exception("store_unavailable")
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
            "created_at": datetime.now().isoformat(),
        }
        return quote_id

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        if quote_id not in self.quotes:
            raise Exception("quote_not_found")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        self.quotes[quote_id]["updated_at"] = datetime.now().isoformat()
        return self.quotes[quote_id]


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float, notification_status: Optional[str] = None) -> str:
        if notification_status == "error":
            raise Exception("notification_error")
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str, notification_status: Optional[str] = None) -> str:
        if notification_status == "error":
            raise Exception("notification_error")
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def __init__(self, tariff_engine: TariffEngine, quote_store: QuoteStore, 
                 screening_service: ScreeningService, notification_service: NotificationService):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        if not shipper_id or len(shipper_id) == 0:
            return False
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False
        return True

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float,
                     screening_risk_index: Optional[int] = None, screening_status: Optional[str] = None,
                     store_status: Optional[str] = None, notification_status: Optional[str] = None) -> dict:
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value, store_status)
        except Exception as e:
            if "store_unavailable" in str(e):
                return {"status": "error: store_unavailable"}
            raise

        try:
            risk_index = self.screening_service.screen(shipper_id, screening_risk_index, screening_status)
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

        if risk_index <= self.ACCEPT_MAX:
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
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id, notification_status)
            except Exception:
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }


def handle(request: dict) -> dict:
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    quote_api = QuoteAPI(tariff_engine, quote_store, screening_service, notification_service)

    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    screening_risk_index = None
    if "screening_result" in request:
        screening_risk_index = request.get("screening_result")
    elif "screening_risk_index" in request:
        screening_risk_index = request.get("screening_risk_index")

    screening_status = request.get("screening_status")
    store_status = request.get("store_status")
    notification_status = request.get("notification_status")

    try:
        response = quote_api.request_quote(
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            screening_risk_index=screening_risk_index,
            screening_status=screening_status,
            store_status=store_status,
            notification_status=notification_status,
        )
        return response
    except Exception as e:
        return {"status": f"error: {str(e)}"}