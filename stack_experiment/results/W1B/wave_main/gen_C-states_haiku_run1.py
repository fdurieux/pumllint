import uuid
from typing import Optional


class ScreeningService:
    """External denied-party screening provider."""
    def __init__(self, risk_index: Optional[int] = None, unavailable: bool = False):
        self.risk_index = risk_index
        self.unavailable = unavailable
    
    def screen(self, shipper_id: str) -> int:
        if self.unavailable:
            raise ScreeningUnavailableError()
        return self.risk_index


class ScreeningUnavailableError(Exception):
    pass


class NotificationService:
    """External messaging provider."""
    def __init__(self, failure: bool = False):
        self.failure = failure
        self.sent_messages = []
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        if self.failure:
            raise NotificationFailureError()
        self.sent_messages.append(("quote_document", shipper_id, quote_id, price))
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if self.failure:
            raise NotificationFailureError()
        self.sent_messages.append(("refusal_notice", shipper_id, quote_id))
        return "sent"


class NotificationFailureError(Exception):
    pass


class QuoteStore:
    """PostgreSQL-backed quote storage."""
    def __init__(self, unavailable: bool = False):
        self.quotes = {}
        self.unavailable = unavailable
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if self.unavailable:
            raise StoreUnavailableError()
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        if self.unavailable:
            raise StoreUnavailableError()
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        return self.quotes[quote_id]


class StoreUnavailableError(Exception):
    pass


class TariffEngine:
    """Freight pricing computation."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        if weight_kg > 1244:
            base += 316.00
        
        if distance_km >= 4912:
            base *= 1.19
        
        return round(base, 2)


class QuoteAPI:
    """Main orchestrator for the quotation flow."""
    
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
    
    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float,
                         declared_value: float) -> Optional[str]:
        if not shipper_id or not isinstance(shipper_id, str) or len(shipper_id.strip()) == 0:
            return "rejected: invalid_request"
        
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return "rejected: invalid_request"
        
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return "rejected: invalid_request"
        
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return "rejected: invalid_request"
        
        return None
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float,
                     declared_value: float) -> dict:
        validation_error = self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if validation_error:
            return {"status": validation_error}
        
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}
        
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_available = True
        except ScreeningUnavailableError:
            risk_index = None
            screening_available = False
        
        if screening_available:
            if risk_index <= self.ACCEPT_MAX:
                price = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, "quoted", price)
                try:
                    self.notification_service.send_quote_document(shipper_id, quote_id, price)
                except NotificationFailureError:
                    pass
                return {"status": "quoted", "quote_id": quote_id, "price": price}
            
            elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
                self.quote_store.update_quote(quote_id, "review_hold")
                return {"status": "review_hold", "quote_id": quote_id}
            
            elif risk_index >= self.REFUSE_MIN:
                self.quote_store.update_quote(quote_id, "refused_screening")
                try:
                    self.notification_service.send_refusal_notice(shipper_id, quote_id)
                except NotificationFailureError:
                    pass
                return {"status": "refused_screening", "quote_id": quote_id}
        else:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {"status": "held_unscreened", "quote_id": quote_id, "price": price, "hold": True}


def handle(request: dict) -> dict:
    """
    Handle a quote request end-to-end.
    
    Request dict keys:
    - shipper_id, weight_kg, distance_km, declared_value: quote parameters
    - screening_service_result: risk index (int) or "unavailable"
    - quote_store_available: bool (default True)
    - notification_service_available: bool (default True)
    """
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    screening_result = request.get("screening_service_result")
    screening_unavailable = screening_result == "unavailable"
    
    store_available = request.get("quote_store_available", True)
    notification_available = request.get("notification_service_available", True)
    
    risk_index = None if screening_unavailable else screening_result
    
    screening_service = ScreeningService(risk_index=risk_index, unavailable=screening_unavailable)
    quote_store = QuoteStore(unavailable=not store_available)
    notification_service = NotificationService(failure=not notification_available)
    tariff_engine = TariffEngine()
    
    api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)
    
    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)