import uuid
from decimal import Decimal
from typing import Optional


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str, screening_result: Optional[int] = None, screening_status: Optional[str] = None) -> int:
        """Return risk index for shipper; higher is worse."""
        if screening_status == "error":
            raise ScreeningUnavailableError("Screening service unavailable")
        if screening_result is not None:
            return screening_result
        return 0


class ScreeningUnavailableError(Exception):
    """Raised when screening service is unavailable."""
    pass


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules (DT-P)."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Compute price per DT-P.
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: heavy surcharge if weight_kg > 1244, add 316.00
        P3: long-haul multiplier if distance_km >= 4912, multiply by 1.19 (after P2)
        P4: round to 2 decimals
        """
        base = Decimal("0.87") * Decimal(str(weight_kg)) + Decimal("1.13") * Decimal(str(distance_km))
        
        if weight_kg > 1244:
            base += Decimal("316.00")
        
        if distance_km >= 4912:
            base = base * Decimal("1.19")
        
        price = float(base)
        return round(price, 2)


class QuoteStore:
    """PostgreSQL-backed quote store."""
    
    def __init__(self):
        self._quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float, store_status: Optional[str] = None) -> str:
        """Store draft quote and return quote_id."""
        if store_status == "error":
            raise StoreUnavailableError("Store unavailable")
        
        quote_id = str(uuid.uuid4())
        self._quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        """Update quote status and optional price."""
        if quote_id not in self._quotes:
            raise KeyError(f"Quote {quote_id} not found")
        
        self._quotes[quote_id]["status"] = status
        if price is not None:
            self._quotes[quote_id]["price"] = price
        
        return self._quotes[quote_id]
    
    def get_quote(self, quote_id: str) -> dict:
        """Retrieve quote by id."""
        return self._quotes.get(quote_id)


class StoreUnavailableError(Exception):
    """Raised when quote store is unavailable."""
    pass


class NotificationService:
    """External messaging provider."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float, notification_status: Optional[str] = None) -> str:
        """Send quote document; returns confirmation."""
        if notification_status == "error":
            return "delivery_failed"
        return "quote_document_sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str, notification_status: Optional[str] = None) -> str:
        """Send refusal notice; returns confirmation."""
        if notification_status == "error":
            return "delivery_failed"
        return "refusal_notice_sent"


class QuoteAPI:
    """Main orchestrator for quote requests."""
    
    # DT-S thresholds
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
    
    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> tuple[bool, Optional[str]]:
        """Validate request per DT-V."""
        # V1: shipper_id present and non-empty
        if not shipper_id:
            return False, "shipper_id is required and non-empty"
        
        # V2: weight_kg in [3, 19400]
        if weight_kg is None or weight_kg < 3 or weight_kg > 19400:
            return False, "weight_kg must be between 3 and 19400"
        
        # V3: distance_km in [25, 7150]
        if distance_km is None or distance_km < 25 or distance_km > 7150:
            return False, "distance_km must be between 25 and 7150"
        
        # V4: declared_value in [50, 83000]
        if declared_value is None or declared_value < 50 or declared_value > 83000:
            return False, "declared_value must be between 50 and 83000"
        
        return True, None
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, 
                      declared_value: float, screening_result: Optional[int] = None,
                      screening_status: Optional[str] = None, store_status: Optional[str] = None,
                      notification_status: Optional[str] = None) -> dict:
        """
        Process a quote request end-to-end.
        
        Args:
            shipper_id, weight_kg, distance_km, declared_value: quote request fields
            screening_result: override risk_index from screening service (for testing)
            screening_status: "error" to simulate screening outage
            store_status: "error" to simulate store outage
            notification_status: "error" to simulate notification delivery failure
        
        Returns:
            Response dict with status, quote_id (if stored), price (if priced), hold (if held_unscreened)
        """
        # Step 1: Validate (DT-V)
        valid, error_msg = self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if not valid:
            return {"status": "rejected: invalid_request"}
        
        # Step 2: Store draft
        try:
            quote_id = self.store.store_draft(shipper_id, weight_kg, distance_km, declared_value, store_status)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}
        
        # Step 3: Request screening
        screening_failed = False
        risk_index = None
        try:
            risk_index = self.screening.screen(shipper_id, screening_result, screening_status)
        except ScreeningUnavailableError:
            screening_failed = True
        
        # Step 4 & 5 & 6: Apply screening decision (DT-S) and pricing (DT-P)
        if screening_failed:
            # Screening outage: price anyway, hold, no notification
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }
        
        # Screening succeeded: apply decision bands (DT-S)
        if risk_index <= self.ACCEPT_MAX:
            # Accept band: price and notify
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "quoted", price)
            self.notification.send_quote_document(shipper_id, quote_id, price, notification_status)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review band: hold without pricing or notification
            self.store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        else:  # risk_index >= REFUSE_MIN
            # Refuse band: no pricing, notify refusal
            self.store.update_quote(quote_id, "refused_screening")
            self.notification.send_refusal_notice(shipper_id, quote_id, notification_status)
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }


def handle(request: dict) -> dict:
    """
    Handle a quote request end-to-end.
    
    Args:
        request: dict with shipper_id, weight_kg, distance_km, declared_value,
                 and optionally: screening_result, screening_status, store_status, notification_status
    
    Returns:
        Response dict with status and optional quote_id, price, hold fields.
    """
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    
    api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)
    
    return api.request_quote(
        shipper_id=request.get("shipper_id", ""),
        weight_kg=request.get("weight_kg"),
        distance_km=request.get("distance_km"),
        declared_value=request.get("declared_value"),
        screening_result=request.get("screening_result"),
        screening_status=request.get("screening_status"),
        store_status=request.get("store_status"),
        notification_status=request.get("notification_status"),
    )