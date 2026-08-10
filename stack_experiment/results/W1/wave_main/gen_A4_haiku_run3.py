import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str, screening_status: Optional[str] = None, risk_index: Optional[int] = None) -> int:
        """
        Screen a shipper and return risk index (higher is worse).
        For testing, accepts screening_status and risk_index from request context.
        """
        if screening_status == "unavailable":
            raise ScreeningUnavailableError("Screening service unavailable")
        if risk_index is not None:
            return risk_index
        return 0


class ScreeningUnavailableError(Exception):
    """Raised when screening service is unavailable."""
    pass


class TariffEngine:
    """Computes freight price per DT-P."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Price a shipment per DT-P (pricing decision table).
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00 (flat)
        P3: if distance_km >= 4912, multiply by 1.19 (applied after P2)
        P4: round to 2 decimals
        """
        base = Decimal(str(0.87 * weight_kg + 1.13 * distance_km))
        
        if weight_kg > 1244:
            base += Decimal("316.00")
        
        if distance_km >= 4912:
            base *= Decimal("1.19")
        
        price_val = base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(price_val)


class QuoteStore:
    """Stores and retrieves quote records."""
    
    def __init__(self):
        self.quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, 
                    declared_value: float, store_status: Optional[str] = None) -> str:
        """
        Store a draft quote; return quote_id.
        If store_status is "unavailable", raise error.
        """
        if store_status == "unavailable":
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
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        """Update quote status and optionally price."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        
        quote = self.quotes[quote_id]
        quote["status"] = status
        if price is not None:
            quote["price"] = price
        return quote


class StoreUnavailableError(Exception):
    """Raised when quote store is unavailable."""
    pass


class NotificationService:
    """External messaging provider."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float, 
                           notification_status: Optional[str] = None) -> str:
        """Send quote document. Fire-and-forget; never changes response."""
        if notification_status == "failed":
            return "delivery_failed"
        return "delivered"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str,
                           notification_status: Optional[str] = None) -> str:
        """Send refusal notice. Fire-and-forget; never changes response."""
        if notification_status == "failed":
            return "delivery_failed"
        return "delivered"


class QuoteAPI:
    """Orchestrates the quotation flow."""
    
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
    
    def validate_request(self, shipper_id: str, weight_kg: float, distance_km: float,
                        declared_value: float) -> tuple[bool, Optional[str]]:
        """
        Validate request per DT-V.
        V1: shipper_id present and non-empty
        V2: weight_kg number, 3 <= weight_kg <= 19400
        V3: distance_km number, 25 <= distance_km <= 7150
        V4: declared_value number, 50 <= declared_value <= 83000
        """
        if not shipper_id or not isinstance(shipper_id, str):
            return False, "invalid_shipper_id"
        
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False, "invalid_weight"
        
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False, "invalid_distance"
        
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False, "invalid_declared_value"
        
        return True, None
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float,
                     declared_value: float, **context) -> dict:
        """
        Execute the quotation flow per the sequence diagram.
        Context may contain: store_status, screening_status, risk_index, notification_status.
        """
        valid, error_reason = self.validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if not valid:
            return {"status": "rejected: invalid_request"}
        
        store_status = context.get("store_status")
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km,
                                                   declared_value, store_status=store_status)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}
        
        screening_status = context.get("screening_status")
        risk_index_override = context.get("risk_index")
        
        try:
            risk_index = self.screening_service.screen(shipper_id, screening_status=screening_status,
                                                       risk_index=risk_index_override)
        except ScreeningUnavailableError:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price=price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }
        
        notification_status = context.get("notification_status")
        
        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price=price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price,
                                                         notification_status=notification_status)
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
            self.notification_service.send_refusal_notice(shipper_id, quote_id,
                                                         notification_status=notification_status)
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }


screening_service = ScreeningService()
tariff_engine = TariffEngine()
quote_store = QuoteStore()
notification_service = NotificationService()
quote_api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)


def handle(request: dict) -> dict:
    """
    Run one end-to-end quotation flow.
    
    Input keys:
    - shipper_id, weight_kg, distance_km, declared_value: core request fields
    - store_status, screening_status, risk_index, notification_status: test context
    
    Returns dict with "status" and optionally quote_id, price, hold.
    """
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    context = {}
    if "store_status" in request:
        context["store_status"] = request["store_status"]
    if "screening_status" in request:
        context["screening_status"] = request["screening_status"]
    if "risk_index" in request:
        context["risk_index"] = request["risk_index"]
    if "notification_status" in request:
        context["notification_status"] = request["notification_status"]
    
    return quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value, **context)