import uuid
import json
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP


class ScreeningService:
    """External screening provider returning shipper risk index."""
    def __init__(self):
        self.risk_index: Optional[int] = None
        self.available: bool = True

    def assess_shipper(self, shipper_id: str) -> int:
        if not self.available:
            raise ScreeningUnavailableError()
        return self.risk_index


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""
    def __init__(self):
        self.delivery_success: bool = True

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        if not self.delivery_success:
            raise NotificationFailureError()
        return "quote_document_sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if not self.delivery_success:
            raise NotificationFailureError()
        return "refusal_notice_sent"


class QuoteStore:
    """PostgreSQL 16 storage for quote requests and lifecycle status."""
    def __init__(self):
        self.quotes: dict = {}
        self.available: bool = True

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float,
                    declared_value: float) -> str:
        if not self.available:
            raise StoreUnavailableError()
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft"
        }
        return quote_id

    def update_status(self, quote_id: str, status: str) -> str:
        if not self.available:
            raise StoreUnavailableError()
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self.quotes[quote_id]["status"] = status
        return quote_id

    def update_with_price(self, quote_id: str, price: float, status: str) -> str:
        if not self.available:
            raise StoreUnavailableError()
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self.quotes[quote_id]["price"] = price
        self.quotes[quote_id]["status"] = status
        return quote_id


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules (DT-P)."""

    def compute_price(self, weight_kg: float, distance_km: float) -> float:
        base = Decimal(str(0.87 * weight_kg + 1.13 * distance_km))

        if weight_kg > 1244:
            base += Decimal("316.00")

        if distance_km >= 4912:
            base *= Decimal("1.19")

        price = float(base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        return price


class QuoteAPI:
    """Main orchestrator: validates, screens, prices, stores, and notifies."""

    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def __init__(self, quote_store: QuoteStore, screening_service: ScreeningService,
                 tariff_engine: TariffEngine, notification_service: NotificationService):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def validate_request(self, shipper_id: str, weight_kg: float, distance_km: float,
                         declared_value: float) -> bool:
        """DT-V: request validation."""
        if not shipper_id or shipper_id == "":
            return False
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False
        return True

    def apply_screening_decision(self, risk_index: int) -> str:
        """DT-S: determine quote status from risk index."""
        if risk_index <= self.ACCEPT_MAX:
            return "quoted"
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            return "review_hold"
        else:
            return "refused_screening"

    def handle_quote_request(self, shipper_id: str, weight_kg: float, distance_km: float,
                             declared_value: float) -> dict:
        """Main quotation flow."""
        try:
            if not self.validate_request(shipper_id, weight_kg, distance_km, declared_value):
                return {"status": "rejected: invalid_request"}

            try:
                quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
            except StoreUnavailableError:
                return {"status": "error: store_unavailable"}

            try:
                risk_index = self.screening_service.assess_shipper(shipper_id)
            except ScreeningUnavailableError:
                self.quote_store.update_status(quote_id, "held_unscreened")
                price = self.tariff_engine.compute_price(weight_kg, distance_km)
                return {
                    "status": "held_unscreened",
                    "quote_id": quote_id,
                    "price": price,
                    "hold": True
                }

            status = self.apply_screening_decision(risk_index)

            if status == "quoted":
                price = self.tariff_engine.compute_price(weight_kg, distance_km)
                self.quote_store.update_with_price(quote_id, price, status)
                try:
                    self.notification_service.send_quote_document(shipper_id, quote_id, price)
                except NotificationFailureError:
                    pass
                return {
                    "status": status,
                    "quote_id": quote_id,
                    "price": price
                }

            elif status == "review_hold":
                self.quote_store.update_status(quote_id, status)
                return {
                    "status": status,
                    "quote_id": quote_id
                }

            elif status == "refused_screening":
                self.quote_store.update_status(quote_id, status)
                try:
                    self.notification_service.send_refusal_notice(shipper_id, quote_id)
                except NotificationFailureError:
                    pass
                return {
                    "status": status,
                    "quote_id": quote_id
                }

        except Exception as e:
            return {"status": f"error: {str(e)}"}

        return {"status": "error: unknown"}


class ScreeningUnavailableError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class NotificationFailureError(Exception):
    pass


_quote_store = QuoteStore()
_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_notification_service = NotificationService()
_quote_api = QuoteAPI(_quote_store, _screening_service, _tariff_engine, _notification_service)


def handle(request: dict) -> dict:
    """
    End-to-end quote request handler. Translates test request dict to API call.
    
    Input keys:
    - shipper_id, weight_kg, distance_km, declared_value: request fields
    - screening_result: risk index (int) or None for unavailability
    - store_available: boolean (default True)
    - screening_available: boolean (default True)
    - notification_delivery_success: boolean (default True)
    
    Returns response dict with "status" and optionally quote_id, price, hold.
    """
    _quote_store.available = request.get("store_available", True)
    _screening_service.available = request.get("screening_available", True)
    _notification_service.delivery_success = request.get("notification_delivery_success", True)

    if "screening_result" in request and request["screening_result"] is not None:
        _screening_service.risk_index = request["screening_result"]

    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)

    return _quote_api.handle_quote_request(shipper_id, weight_kg, distance_km, declared_value)