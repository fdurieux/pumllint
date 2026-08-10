import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str, screening_result: Optional[int] = None, 
               screening_status: Optional[str] = None) -> int:
        """
        Request shipper risk index.
        Returns risk index (int); higher is worse.
        If screening_status is "error" or service unavailable, raises exception.
        """
        if screening_status == "error":
            raise Exception("screening_unavailable")
        if screening_result is not None:
            return screening_result
        raise Exception("screening_unavailable")


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules (DT-P)."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Compute price per DT-P.
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00 (heavy surcharge)
        P3: if distance_km >= 4912, multiply by 1.19 (long-haul, applied after P2)
        P4: round to 2 decimals
        """
        base = Decimal(str(0.87 * weight_kg + 1.13 * distance_km))
        
        if weight_kg > 1244:
            base += Decimal("316.00")
        
        if distance_km >= 4912:
            base *= Decimal("1.19")
        
        result = base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(result)


class QuoteStore:
    """Stores quote requests and their lifecycle status (simulated in-memory)."""
    
    def __init__(self):
        self.quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, 
                    declared_value: float, store_status: Optional[str] = None) -> str:
        """
        Store draft quote, return quote_id.
        If store_status is "error", raise exception.
        """
        if store_status == "error":
            raise Exception("store_unavailable")
        
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        """Update quote status and optionally price."""
        if quote_id in self.quotes:
            self.quotes[quote_id]["status"] = status
            if price is not None:
                self.quotes[quote_id]["price"] = price
            return self.quotes[quote_id]
        raise Exception("quote_not_found")


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float,
                           notification_status: Optional[str] = None) -> str:
        """Send quote document. Returns "sent" or raises on failure."""
        if notification_status == "error":
            raise Exception("notification_failed")
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str,
                           notification_status: Optional[str] = None) -> str:
        """Send refusal notice. Returns "sent" or raises on failure."""
        if notification_status == "error":
            raise Exception("notification_failed")
        return "sent"


class QuoteAPI:
    """Main quotation orchestrator."""
    
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def __init__(self, screening_service: ScreeningService, tariff_engine: TariffEngine,
                 quote_store: QuoteStore, notification_service: NotificationService):
        self.screening = screening_service
        self.tariff = tariff_engine
        self.store = quote_store
        self.notification = notification_service
    
    def validate_request(self, shipper_id: str, weight_kg: float, distance_km: float,
                        declared_value: float) -> bool:
        """DT-V: validate request bounds."""
        if not shipper_id or len(shipper_id.strip()) == 0:
            return False
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False
        return True
    
    def request_quote(self, request: dict) -> dict:
        """
        Main quotation flow orchestrator.
        request: {shipper_id, weight_kg, distance_km, declared_value, 
                  [screening_result, store_status, notification_status]}
        """
        shipper_id = request.get("shipper_id")
        weight_kg = request.get("weight_kg")
        distance_km = request.get("distance_km")
        declared_value = request.get("declared_value")
        
        screening_result = request.get("screening_result")
        screening_status = request.get("screening_status")
        store_status = request.get("store_status")
        notification_status = request.get("notification_status")
        
        # Step 1: Validate request (DT-V)
        if not self.validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}
        
        # Step 2: Store draft quote
        try:
            quote_id = self.store.store_draft(shipper_id, weight_kg, distance_km,
                                             declared_value, store_status)
        except Exception as e:
            if "store_unavailable" in str(e):
                return {"status": "error: store_unavailable"}
            raise
        
        # Step 3: Request screening
        risk_index = None
        screening_failed = False
        try:
            risk_index = self.screening.screen(shipper_id, screening_result, screening_status)
        except Exception as e:
            if "screening_unavailable" in str(e):
                screening_failed = True
            else:
                raise
        
        # Step 4: Handle screening result or outage
        if screening_failed:
            # Screening outage: price anyway, store as held_unscreened, no notification
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }
        
        # Apply screening decision (DT-S)
        if risk_index <= self.ACCEPT_MAX:
            # Accept: price, store as quoted, notify
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "quoted", price)
            try:
                self.notification.send_quote_document(shipper_id, quote_id, price, notification_status)
            except Exception:
                # Fire-and-forget: never changes response
                pass
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review: no price, no notification
            self.store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        
        else:  # risk_index >= REFUSE_MIN
            # Refuse: no price, but do notify
            self.store.update_quote(quote_id, "refused_screening")
            try:
                self.notification.send_refusal_notice(shipper_id, quote_id, notification_status)
            except Exception:
                # Fire-and-forget: never changes response
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }


def handle(request: dict) -> dict:
    """
    End-to-end quotation flow handler.
    
    request keys:
      - shipper_id, weight_kg, distance_km, declared_value (required)
      - screening_result: int (risk index, overrides service call)
      - screening_status: str ("error" for unavailable)
      - store_status: str ("error" for unavailable)
      - notification_status: str ("error" for delivery failure)
    
    Returns dict with status and optional quote_id, price, hold fields.
    """
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    
    api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)
    
    return api.request_quote(request)