import uuid
from datetime import datetime
from typing import Optional


class ScreeningService:
    def __init__(self):
        self.unavailable = False
        self.risk_index = 0

    def screen(self, shipper_id: str) -> int:
        if self.unavailable:
            raise ScreeningUnavailableError("Screening service unavailable")
        return self.risk_index


class ScreeningUnavailableError(Exception):
    pass


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
        self.unavailable = False

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        if self.unavailable:
            raise StoreUnavailableError("Quote store unavailable")
        
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "quote_id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
            "created_at": datetime.now().isoformat(),
        }
        return quote_id

    def update_quote(
        self,
        quote_id: str,
        status: str,
        price: Optional[float] = None,
    ) -> dict:
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        self.quotes[quote_id]["updated_at"] = datetime.now().isoformat()
        
        return self.quotes[quote_id]


class StoreUnavailableError(Exception):
    pass


class NotificationService:
    def __init__(self):
        self.failed = False
        self.notifications = []

    def send_quote_document(
        self, shipper_id: str, quote_id: str, price: float
    ) -> str:
        if self.failed:
            return "delivery_failed"
        
        self.notifications.append({
            "type": "quote_document",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
            "price": price,
        })
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if self.failed:
            return "delivery_failed"
        
        self.notifications.append({
            "type": "refusal_notice",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
        })
        return "sent"


class QuoteAPI:
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

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

    def _validate_request(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> tuple[bool, Optional[str]]:
        if not shipper_id or shipper_id == "":
            return False, "shipper_id must be present and non-empty"
        
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False, "weight_kg must be between 3 and 19400"
        
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False, "distance_km must be between 25 and 7150"
        
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False, "declared_value must be between 50 and 83000"
        
        return True, None

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        valid, error_msg = self._validate_request(
            shipper_id, weight_kg, distance_km, declared_value
        )
        
        if not valid:
            return {"status": "rejected: invalid_request"}
        
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}
        
        risk_index = None
        screening_unavailable = False
        
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            screening_unavailable = True
        
        if screening_unavailable:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, "held_unscreened", price
            )
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }
        
        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price
            )
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
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }


_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_quote_store = QuoteStore()
_notification_service = NotificationService()
_api = QuoteAPI(
    _screening_service,
    _tariff_engine,
    _quote_store,
    _notification_service,
)


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    screening_result = request.get("screening_result")
    screening_status = request.get("screening_status")
    store_status = request.get("store_status")
    notification_status = request.get("notification_status")
    
    _screening_service.unavailable = False
    _quote_store.unavailable = False
    _notification_service.failed = False
    
    if screening_result is not None:
        _screening_service.risk_index = screening_result
    
    if screening_status == "unavailable":
        _screening_service.unavailable = True
    
    if store_status == "unavailable":
        _quote_store.unavailable = True
    
    if notification_status == "failed":
        _notification_service.failed = True
    
    response = _api.request_quote(
        shipper_id,
        weight_kg,
        distance_km,
        declared_value,
    )
    
    return response