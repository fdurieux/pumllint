import json
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: str
    price: Optional[float] = None
    created_at: str = ""
    updated_at: str = ""


class ScreeningService:
    def screen(self, shipper_id: str) -> int:
        """External screening service returns a risk index (0-100+)."""
        return 0


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute freight price from weight and distance per tariff rules (DT-P)."""
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        if weight_kg > 1244:
            base += 316.00
        
        if distance_km >= 4912:
            base *= 1.19
        
        result = Decimal(str(base)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return float(result)


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        """Fire-and-forget notification; always succeeds."""
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Fire-and-forget notification; always succeeds."""
        return "sent"


class QuoteStore:
    def __init__(self):
        self.quotes: dict[str, Quote] = {}
        self.counter = 0
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its ID."""
        self.counter += 1
        quote_id = f"Q{self.counter:06d}"
        now = datetime.now().isoformat()
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status="draft",
            created_at=now,
            updated_at=now
        )
        self.quotes[quote_id] = quote
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> Quote:
        """Update a quote's status and optionally price."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote.status = status
        if price is not None:
            quote.price = price
        quote.updated_at = datetime.now().isoformat()
        return quote


class QuoteAPI:
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
    
    def validate_request(self, shipper_id: str, weight_kg: float, 
                        distance_km: float, declared_value: float) -> bool:
        """Validate request per DT-V."""
        if not shipper_id or shipper_id == "":
            return False
        
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False
        
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False
        
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False
        
        return True
    
    def request_quote(self, shipper_id: str, weight_kg: float, 
                     distance_km: float, declared_value: float) -> dict:
        """Main quote request handler."""
        if not self.validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}
        
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception as e:
            return {"status": "error: store_unavailable"}
        
        risk_index = self.screening_service.screen(shipper_id)
        
        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount
            }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        
        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }
        
        return {"status": "error: unknown"}


class ScreeningServiceMock(ScreeningService):
    def __init__(self, result: Optional[int] = None, status: Optional[str] = None):
        self.result = result
        self.status = status
    
    def screen(self, shipper_id: str) -> int:
        if self.status == "error":
            raise Exception("Screening service unavailable")
        if self.result is not None:
            return self.result
        return 0


class TariffEngineMock(TariffEngine):
    def __init__(self, result: Optional[float] = None, status: Optional[str] = None):
        self.result = result
        self.status = status
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        if self.status == "error":
            raise Exception("Tariff engine unavailable")
        if self.result is not None:
            return self.result
        return super().price(weight_kg, distance_km)


class NotificationServiceMock(NotificationService):
    def __init__(self, status: Optional[str] = None):
        self.status = status
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        if self.status == "error":
            return "error"
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if self.status == "error":
            return "error"
        return "sent"


class QuoteStoreMock(QuoteStore):
    def __init__(self, status: Optional[str] = None):
        super().__init__()
        self.store_status = status
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        if self.store_status == "error":
            raise Exception("Store unavailable")
        return super().store_draft(shipper_id, weight_kg, distance_km, declared_value)


def handle(request: dict) -> dict:
    """
    Run one end-to-end flow.
    
    request may contain:
    - shipper_id, weight_kg, distance_km, declared_value (quote parameters)
    - shipper_id_exists, weight_kg_exists, etc. (existence flags)
    - screening_service_result (integer risk index)
    - screening_service_status (string like "error", "unavailable")
    - tariff_engine_result (float price)
    - tariff_engine_status (string like "error")
    - quote_store_status (string like "error")
    - notification_service_status (string like "error")
    
    Returns:
    - dict with "status" key and optional "quote_id", "price" keys
    """
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)
    
    quote_store = QuoteStoreMock(status=request.get("quote_store_status"))
    
    screening_result = request.get("screening_service_result")
    screening_status = request.get("screening_service_status")
    screening_service = ScreeningServiceMock(result=screening_result, status=screening_status)
    
    tariff_result = request.get("tariff_engine_result")
    tariff_status = request.get("tariff_engine_status")
    tariff_engine = TariffEngineMock(result=tariff_result, status=tariff_status)
    
    notification_status = request.get("notification_service_status")
    notification_service = NotificationServiceMock(status=notification_status)
    
    api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)
    
    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)