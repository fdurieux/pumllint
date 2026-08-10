import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


class QuoteStore:
    """Stores and retrieves quote records."""
    
    def __init__(self):
        self.quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its ID."""
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "quote_id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        """Update a quote's status and optionally its price."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        return self.quotes[quote_id]


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str, result: Optional[int] = None, available: bool = True) -> int:
        """Request shipper risk index. Returns int or raises exception."""
        if not available:
            raise Exception("screening_unavailable")
        if result is not None:
            return result
        return 10


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute price per DT-P."""
        base = Decimal(str(0.87 * weight_kg + 1.13 * distance_km))
        
        if weight_kg > 1244:
            base += Decimal("316.00")
        
        if distance_km >= 4912:
            base *= Decimal("1.19")
        
        result = base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(result)


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float, available: bool = True) -> str:
        """Send quote document. Returns confirmation or raises exception."""
        if not available:
            raise Exception("notification_unavailable")
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str, available: bool = True) -> str:
        """Send refusal notice. Returns confirmation or raises exception."""
        if not available:
            raise Exception("notification_unavailable")
        return "sent"


class QuoteAPI:
    """Main orchestrator for the quotation flow."""
    
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
    
    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        """Validate request per DT-V."""
        if not shipper_id or not isinstance(shipper_id, str):
            return False
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False
        return True
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, 
                     declared_value: float, screening_result: Optional[int] = None,
                     store_available: bool = True, screening_available: bool = True,
                     notification_available: bool = True) -> dict:
        """Main quotation flow orchestrator."""
        
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}
        
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception:
            return {"status": "error: store_unavailable"}
        
        screening_failed = False
        risk_index = None
        
        try:
            risk_index = self.screening_service.screen(shipper_id, screening_result, screening_available)
        except Exception:
            screening_failed = True
        
        if screening_failed:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }
        
        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price, notification_available)
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
                self.notification_service.send_refusal_notice(shipper_id, quote_id, notification_available)
            except Exception:
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }


def handle(request: dict) -> dict:
    """
    Main entry point for quote handling. Processes a quote request dict.
    
    Input keys:
    - shipper_id, weight_kg, distance_km, declared_value: quote request data
    - screening_result: (optional) risk index from screening service
    - store_available: (optional) whether quote store is available (default True)
    - screening_available: (optional) whether screening service is available (default True)
    - notification_available: (optional) whether notification service is available (default True)
    """
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)
    
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    screening_result = request.get("screening_result")
    store_available = request.get("store_available", True)
    screening_available = request.get("screening_available", True)
    notification_available = request.get("notification_available", True)
    
    return api.request_quote(
        shipper_id=shipper_id,
        weight_kg=weight_kg,
        distance_km=distance_km,
        declared_value=declared_value,
        screening_result=screening_result,
        store_available=store_available,
        screening_available=screening_available,
        notification_available=notification_available,
    )