import uuid
from typing import Any


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str) -> int:
        """Return riskIndex (0-100). Raises ScreeningUnavailableError on failure."""
        return 0


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute priceAmount. Returns float price in currency units."""
        base_rate = 0.5
        return (weight_kg * 0.01 + distance_km * base_rate)


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> None:
        """Deliver quote document. Fire-and-forget; never changes response."""
        pass
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Deliver refusal notice. Fire-and-forget; never changes response."""
        pass


class QuoteStore:
    """PostgreSQL-backed quote store."""
    
    def __init__(self):
        self.quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float,
                    declared_value: float) -> str:
        """Store draft quote; return quoteId. Raises StoreUnavailableError on failure."""
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price_amount": None
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price_amount: float = None) -> dict:
        """Update quote status and optionally price. Returns updated quote."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote["status"] = status
        if price_amount is not None:
            quote["price_amount"] = price_amount
        return quote


class QuoteAPI:
    """Main quotation orchestration service."""
    
    ACCEPT_MAX = 30
    REVIEW_MIN = 31
    REVIEW_MAX = 70
    REFUSE_MIN = 71
    
    def __init__(self, quote_store: QuoteStore, screening_service: ScreeningService,
                 tariff_engine: TariffEngine, notification_service: NotificationService):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float,
                      declared_value: float) -> dict:
        """Execute the quotation flow."""
        
        # Step 1: Validate request (decision table DT-V)
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {
                "status": "rejected_invalid_request",
                "quote_id": None
            }
        
        # Step 1: Store draft
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km,
                                                     declared_value)
        except Exception:
            return {
                "status": "store_unavailable_error",
                "quote_id": None
            }
        
        # Step 2: Screen shipper
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_available = True
        except Exception:
            screening_available = False
            risk_index = None
        
        # Step 3: Apply screening decision (decision table DT-S)
        if screening_available:
            if risk_index <= self.ACCEPT_MAX:
                # Accept: price, store quoted, notify
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, "quoted", price_amount)
                try:
                    self.notification_service.send_quote_document(shipper_id, quote_id,
                                                                   price_amount)
                except Exception:
                    pass
                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price_amount": price_amount
                }
            elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
                # Review hold: no pricing, no notification
                self.quote_store.update_quote(quote_id, "review_hold")
                return {
                    "status": "review_hold",
                    "quote_id": quote_id
                }
            elif risk_index >= self.REFUSE_MIN:
                # Refuse: no pricing, but notify refusal
                self.quote_store.update_quote(quote_id, "refused_screening")
                try:
                    self.notification_service.send_refusal_notice(shipper_id, quote_id)
                except Exception:
                    pass
                return {
                    "status": "refused_screening",
                    "quote_id": quote_id
                }
        else:
            # Screening unavailable: price anyway, hold unscreened, no notification
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price_amount": price_amount
            }
    
    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float,
                          declared_value: float) -> bool:
        """Validate request bounds per DT-V."""
        if not shipper_id or shipper_id.strip() == "":
            return False
        if weight_kg <= 0 or weight_kg > 100000:
            return False
        if distance_km <= 0 or distance_km > 5000:
            return False
        if declared_value < 0 or declared_value > 1000000:
            return False
        return True


def handle(request: dict) -> dict:
    """End-to-end quotation flow handler."""
    
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    
    api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)
    
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)
    
    if "screening_result" in request:
        result = request["screening_result"]
        if result == "approved":
            screening_service.screen = lambda _: 25
        elif result == "review":
            screening_service.screen = lambda _: 50
        elif result == "declined":
            screening_service.screen = lambda _: 80
        elif result == "error":
            screening_service.screen = lambda _: (_ for _ in ()).throw(Exception("Screening unavailable"))
        elif isinstance(result, (int, float)):
            screening_service.screen = lambda _: result
    
    if "price_result" in request:
        result = request["price_result"]
        if isinstance(result, (int, float)):
            tariff_engine.price = lambda w, d: result
    
    if "store_result" in request:
        result = request["store_result"]
        if result == "error":
            quote_store.store_draft = lambda *args, **kwargs: (_ for _ in ()).throw(
                Exception("Store unavailable"))
    
    if "notification_result" in request:
        result = request["notification_result"]
        if result == "error":
            notification_service.send_quote_document = lambda *args, **kwargs: (_ for _ in ()).throw(
                Exception("Notification failed"))
            notification_service.send_refusal_notice = lambda *args, **kwargs: (_ for _ in ()).throw(
                Exception("Notification failed"))
    
    try:
        response = api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
        return response
    except Exception as e:
        return {
            "status": f"error: {str(e)}",
            "quote_id": None
        }