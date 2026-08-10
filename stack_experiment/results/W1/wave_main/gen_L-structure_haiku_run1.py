from dataclasses import dataclass
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: str
    price: Optional[float] = None


class QuoteStore:
    def __init__(self):
        self.quotes: dict[str, Quote] = {}
        self._counter = 0
        self._available = True

    def set_available(self, available: bool):
        self._available = available

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if not self._available:
            raise Exception("store_unavailable")
        self._counter += 1
        quote_id = f"Q-{self._counter:06d}"
        self.quotes[quote_id] = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status="draft"
        )
        return quote_id

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> Quote:
        if quote_id not in self.quotes:
            raise Exception("quote_not_found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price is not None:
            quote.price = price
        return quote

    def get_quote(self, quote_id: str) -> Quote:
        return self.quotes.get(quote_id)


class ScreeningService:
    def __init__(self):
        self._available = True
        self._risk_index = None

    def set_available(self, available: bool):
        self._available = available

    def set_risk_index(self, risk_index: int):
        self._risk_index = risk_index

    def screen(self, shipper_id: str) -> int:
        if not self._available:
            raise Exception("screening_unavailable")
        if self._risk_index is None:
            return 0
        return self._risk_index


class TariffEngine:
    def __init__(self):
        self._available = True

    def set_available(self, available: bool):
        self._available = available

    def price(self, weight_kg: float, distance_km: float) -> float:
        if not self._available:
            raise Exception("pricing_unavailable")

        base = Decimal("0.87") * Decimal(str(weight_kg)) + Decimal("1.13") * Decimal(str(distance_km))
        
        if weight_kg > 1244:
            base += Decimal("316.00")
        
        if distance_km >= 4912:
            base *= Decimal("1.19")
        
        price = float(base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        return price


class NotificationService:
    def __init__(self):
        self._available = True
        self.notifications: list[dict] = []

    def set_available(self, available: bool):
        self._available = available

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        if not self._available:
            raise Exception("notification_unavailable")
        self.notifications.append({
            "type": "quote_document",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
            "price": price
        })
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if not self._available:
            raise Exception("notification_unavailable")
        self.notifications.append({
            "type": "refusal_notice",
            "shipper_id": shipper_id,
            "quote_id": quote_id
        })
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def __init__(self, store: QuoteStore, screening: ScreeningService, tariff: TariffEngine, notification: NotificationService):
        self.store = store
        self.screening = screening
        self.tariff = tariff
        self.notification = notification

    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        if not shipper_id or shipper_id == "":
            return False
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False
        return True

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        try:
            quote_id = self.store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception as e:
            if "store_unavailable" in str(e):
                return {"status": "error: store_unavailable"}
            raise

        screening_failed = False
        risk_index = None
        try:
            risk_index = self.screening.screen(shipper_id)
        except Exception as e:
            if "screening_unavailable" in str(e):
                screening_failed = True
            else:
                raise

        if screening_failed:
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }

        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "quoted", price)
            try:
                self.notification.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                pass
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        elif risk_index >= self.REFUSE_MIN:
            self.store.update_quote(quote_id, "refused_screening")
            try:
                self.notification.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }

        return {"status": "error: unknown"}


_store = QuoteStore()
_screening = ScreeningService()
_tariff = TariffEngine()
_notification = NotificationService()
_api = QuoteAPI(_store, _screening, _tariff, _notification)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    if "store_available" in request and not request["store_available"]:
        _store.set_available(False)
    else:
        _store.set_available(True)

    if "screening_available" in request and not request["screening_available"]:
        _screening.set_available(False)
    else:
        _screening.set_available(True)

    if "screening_result" in request:
        _screening.set_risk_index(request["screening_result"])
    elif "risk_index" in request:
        _screening.set_risk_index(request["risk_index"])

    if "notification_available" in request and not request["notification_available"]:
        _notification.set_available(False)
    else:
        _notification.set_available(True)

    try:
        response = _api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
        return response
    except Exception as e:
        return {"status": f"error: {str(e)}"}