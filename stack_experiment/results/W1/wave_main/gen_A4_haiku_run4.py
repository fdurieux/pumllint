import uuid
import math
from typing import Optional


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str, screening_status: Optional[str] = None) -> Optional[int]:
        """
        Returns risk index (integer, higher is worse) or raises exception on unavailability.
        If screening_status is provided from test context, use it.
        """
        if screening_status == "unavailable":
            raise Exception("screening_unavailable")
        if screening_status == "error":
            raise Exception("screening_unavailable")
        return 0


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules (DT-P)."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Apply DT-P pricing rules:
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00
        P3: if distance_km >= 4912, multiply by 1.19 (after P2)
        P4: round to 2 decimals
        """
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        if weight_kg > 1244:
            base += 316.00
        
        if distance_km >= 4912:
            base *= 1.19
        
        return round(base, 2)


class QuoteStore:
    """PostgreSQL quote store."""
    
    def __init__(self):
        self.quotes = {}
    
    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
        store_status: Optional[str] = None
    ) -> str:
        """Store draft quote, return quote_id. Raises exception on failure."""
        if store_status == "unavailable" or store_status == "error":
            raise Exception("store_unavailable")
        
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "quote_id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None
        }
        return quote_id
    
    def update_quote(
        self,
        quote_id: str,
        status: str,
        price: Optional[float] = None
    ) -> dict:
        """Update stored quote with new status and optional price."""
        if quote_id not in self.quotes:
            raise Exception("quote_not_found")
        
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        
        return self.quotes[quote_id]


class NotificationService:
    """External messaging provider."""
    
    def send_quote_document(
        self,
        shipper_id: str,
        quote_id: str,
        price: float,
        notification_status: Optional[str] = None
    ) -> str:
        """
        Send quote document. Fire-and-forget: failures do not affect response.
        Returns confirmation or raises (but caller ignores exceptions).
        """
        if notification_status == "failed" or notification_status == "error":
            raise Exception("notification_delivery_failed")
        return "sent"
    
    def send_refusal_notice(
        self,
        shipper_id: str,
        quote_id: str,
        notification_status: Optional[str] = None
    ) -> str:
        """Send refusal notice. Fire-and-forget."""
        if notification_status == "failed" or notification_status == "error":
            raise Exception("notification_delivery_failed")
        return "sent"


class QuoteAPI:
    """Main orchestrator: validates, screens, prices, and notifies."""
    
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
    
    def _validate_request(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float
    ) -> tuple[bool, Optional[str]]:
        """
        Validate per DT-V. Returns (is_valid, error_reason).
        """
        if not shipper_id or shipper_id == "":
            return False, "shipper_id empty"
        
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False, "weight_kg out of bounds"
        
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False, "distance_km out of bounds"
        
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False, "declared_value out of bounds"
        
        return True, None
    
    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
        screening_status: Optional[str] = None,
        store_status: Optional[str] = None,
        notification_status: Optional[str] = None
    ) -> dict:
        """
        Main quotation flow per the sequence diagram and DT-V, DT-S, DT-P.
        Test harness passes optional *_status flags to inject external outcomes.
        """
        is_valid, _ = self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if not is_valid:
            return {"status": "rejected: invalid_request"}
        
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value,
                store_status=store_status
            )
        except Exception as e:
            if "store_unavailable" in str(e):
                return {"status": "error: store_unavailable"}
            raise
        
        risk_index = None
        screening_failed = False
        try:
            risk_index = self.screening_service.screen(shipper_id, screening_status=screening_status)
        except Exception as e:
            if "screening_unavailable" in str(e):
                screening_failed = True
            else:
                raise
        
        if screening_failed:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }
        
        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            try:
                self.notification_service.send_quote_document(
                    shipper_id, quote_id, price,
                    notification_status=notification_status
                )
            except Exception:
                pass
            
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
            try:
                self.notification_service.send_refusal_notice(
                    shipper_id, quote_id,
                    notification_status=notification_status
                )
            except Exception:
                pass
            
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }


def handle(request: dict) -> dict:
    """
    End-to-end flow. Request carries entity ids, amounts, and test flags
    (e.g. "screening_status", "store_status", "notification_status").
    Returns dict with "status" key naming the outcome.
    """
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    
    api = QuoteAPI(
        screening_service,
        tariff_engine,
        quote_store,
        notification_service
    )
    
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    screening_status = request.get("screening_status")
    store_status = request.get("store_status")
    notification_status = request.get("notification_status")
    
    return api.request_quote(
        shipper_id,
        weight_kg,
        distance_km,
        declared_value,
        screening_status=screening_status,
        store_status=store_status,
        notification_status=notification_status
    )