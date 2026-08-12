import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str, screening_result: Optional[int] = None) -> int:
        """
        Returns a risk index for the shipper.
        In test mode, uses screening_result if provided.
        """
        if screening_result is not None:
            return screening_result
        return 25


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules."""
    
    def price(self, weight_kg: float, distance_km: float, pricing_result: Optional[float] = None) -> float:
        """
        Prices a consignment per DT-P.
        In test mode, uses pricing_result if provided.
        """
        if pricing_result is not None:
            return pricing_result
        
        weight_kg = float(weight_kg)
        distance_km = float(distance_km)
        
        base = Decimal("0.87") * Decimal(str(weight_kg)) + Decimal("1.13") * Decimal(str(distance_km))
        
        if weight_kg > 1244:
            base += Decimal("316.00")
        
        if distance_km >= 4912:
            base *= Decimal("1.19")
        
        price_rounded = float(base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        return price_rounded


class QuoteStore:
    """Stores quote requests and lifecycle status."""
    
    def __init__(self):
        self.quotes = {}
    
    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
        store_result: Optional[str] = None
    ) -> str:
        """
        Stores a draft quote and returns quote_id.
        In test mode, if store_result is "error", raises an exception.
        """
        if store_result == "error":
            raise Exception("store_unavailable")
        
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "quote_id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
            "created_at": datetime.utcnow().isoformat(),
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        """Updates a quote status and optionally its price."""
        if quote_id not in self.quotes:
            raise Exception("quote_not_found")
        
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        
        return self.quotes[quote_id]


class NotificationService:
    """External messaging provider delivering documents and notices."""
    
    def send_quote_document(
        self,
        shipper_id: str,
        quote_id: str,
        price: float,
        notification_result: Optional[str] = None
    ) -> str:
        """Sends a quote document. Fire-and-forget; failure never changes response."""
        if notification_result == "error":
            return "failed"
        return "sent"
    
    def send_refusal_notice(
        self,
        shipper_id: str,
        quote_id: str,
        notification_result: Optional[str] = None
    ) -> str:
        """Sends a refusal notice. Fire-and-forget; failure never changes response."""
        if notification_result == "error":
            return "failed"
        return "sent"


class QuoteAPI:
    """Orchestrates screening, pricing, storage, and notification."""
    
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def __init__(
        self,
        screening_service: ScreeningService,
        tariff_engine: TariffEngine,
        quote_store: QuoteStore,
        notification_service: NotificationService
    ):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service
    
    def validate_request(self, request: dict) -> tuple[bool, Optional[str]]:
        """Validates request per DT-V. Returns (is_valid, error_message)."""
        shipper_id = request.get("shipper_id", "")
        weight_kg = request.get("weight_kg")
        distance_km = request.get("distance_km")
        declared_value = request.get("declared_value")
        
        if not shipper_id or not isinstance(shipper_id, str):
            return False, "invalid shipper_id"
        
        if weight_kg is None or not (3 <= weight_kg <= 19400):
            return False, "weight_kg out of bounds"
        
        if distance_km is None or not (25 <= distance_km <= 7150):
            return False, "distance_km out of bounds"
        
        if declared_value is None or not (50 <= declared_value <= 83000):
            return False, "declared_value out of bounds"
        
        return True, None
    
    def request_quote(self, request: dict) -> dict:
        """Main entry point: orchestrates the quote flow."""
        is_valid, error_msg = self.validate_request(request)
        if not is_valid:
            return {"status": "rejected: invalid_request"}
        
        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]
        
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value,
                store_result=request.get("store_result")
            )
        except Exception as e:
            if "store_unavailable" in str(e):
                return {"status": "error: store_unavailable"}
            raise
        
        response_base = {"status": None, "quote_id": quote_id}
        
        screening_result = request.get("screening_result")
        try:
            risk_index = self.screening_service.screen(shipper_id, screening_result)
        except Exception:
            risk_index = None
        
        if risk_index is None:
            price = self.tariff_engine.price(
                weight_kg, distance_km,
                pricing_result=request.get("pricing_result")
            )
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }
        
        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(
                weight_kg, distance_km,
                pricing_result=request.get("pricing_result")
            )
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price,
                notification_result=request.get("notification_result")
            )
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        
        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(
                shipper_id, quote_id,
                notification_result=request.get("notification_result")
            )
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }


_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_quote_store = QuoteStore()
_notification_service = NotificationService()
_quote_api = QuoteAPI(_screening_service, _tariff_engine, _quote_store, _notification_service)


def handle(request: dict) -> dict:
    """
    Main entry point: runs one end-to-end quotation flow.
    
    Expected keys in request:
    - shipper_id, weight_kg, distance_km, declared_value: quote data
    - store_result: "error" to simulate storage failure
    - screening_result: risk index (int) or None to use default
    - pricing_result: price (float) or None to compute
    - notification_result: "error" to simulate notification failure
    
    Returns a dict with at minimum a "status" key describing the outcome.
    """
    return _quote_api.request_quote(request)