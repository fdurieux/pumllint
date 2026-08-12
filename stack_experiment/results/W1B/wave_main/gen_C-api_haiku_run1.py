import json
from typing import Any
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from enum import Enum


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str, risk_index: int = None) -> int:
        """
        Request shipper risk index from screening service.
        In handle(), screening_result key overrides default behavior.
        """
        return risk_index if risk_index is not None else 30


class TariffEngine:
    """Computes freight price per DT-P rules."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Compute price per DT-P.
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00
        P3: if distance_km >= 4912, multiply by 1.19 (after P2)
        P4: round to 2 decimals
        """
        base = Decimal(str(0.87 * weight_kg + 1.13 * distance_km))
        
        if weight_kg > 1244:
            base += Decimal("316.00")
        
        if distance_km >= 4912:
            base *= Decimal("1.19")
        
        price = base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(price)


class QuoteStore:
    """PostgreSQL-backed quote store."""
    
    def __init__(self):
        self.quotes = {}
        self.counter = 0
    
    def store_draft(self, shipper_id: str, weight_kg: float, 
                    distance_km: float, declared_value: float,
                    store_available: bool = True) -> str:
        """
        Store a draft quote. Returns quote_id.
        Raises exception if store_available=False.
        """
        if not store_available:
            raise Exception("store_unavailable")
        
        self.counter += 1
        quote_id = f"Q{self.counter:06d}"
        self.quotes[quote_id] = {
            "quote_id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": QuoteStatus.DRAFT.value,
            "price": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: float = None) -> dict:
        """Update quote status and optionally price."""
        if quote_id not in self.quotes:
            raise Exception(f"quote_not_found: {quote_id}")
        
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        self.quotes[quote_id]["updated_at"] = datetime.now().isoformat()
        return self.quotes[quote_id]


class NotificationService:
    """External messaging provider."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, 
                           price: float) -> str:
        """Fire-and-forget notification of quote document."""
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Fire-and-forget notification of refusal."""
        return "sent"


class QuoteAPI:
    """Main quotation orchestrator."""
    
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
                        distance_km: float, declared_value: float) -> tuple[bool, str]:
        """
        Validate per DT-V.
        Returns (is_valid, error_message).
        """
        if not shipper_id or shipper_id.strip() == "":
            return False, "shipper_id: empty"
        
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False, "weight_kg: out of range [3, 19400]"
        
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False, "distance_km: out of range [25, 7150]"
        
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False, "declared_value: out of range [50, 83000]"
        
        return True, ""
    
    def request_quote(self, shipper_id: str, weight_kg: float, 
                     distance_km: float, declared_value: float,
                     store_available: bool = True,
                     screening_available: bool = True,
                     screening_result: int = None) -> dict:
        """
        Main quotation flow.
        
        Args:
            shipper_id: shipper identifier
            weight_kg: cargo weight
            distance_km: route distance
            declared_value: cargo declared value
            store_available: whether Quote Store is available
            screening_available: whether Screening Service is available
            screening_result: override screening risk index (for testing)
        
        Returns:
            Response dict with status, quote_id (if stored), price (if priced), hold flag
        """
        is_valid, error_msg = self.validate_request(shipper_id, weight_kg, 
                                                     distance_km, declared_value)
        
        if not is_valid:
            return {"status": "rejected: invalid_request"}
        
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value,
                store_available=store_available
            )
        except Exception as e:
            if "store_unavailable" in str(e):
                return {"status": "error: store_unavailable"}
            raise
        
        response = {"status": None, "quote_id": quote_id}
        
        if screening_available:
            risk_index = self.screening_service.screen(shipper_id, screening_result)
            
            if risk_index <= self.ACCEPT_MAX:
                price = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED.value, price)
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
                response["status"] = "quoted"
                response["price"] = price
            
            elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
                self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD.value)
                response["status"] = "review_hold"
            
            elif risk_index >= self.REFUSE_MIN:
                self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING.value)
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
                response["status"] = "refused_screening"
        
        else:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED.value, price)
            response["status"] = "held_unscreened"
            response["price"] = price
            response["hold"] = True
        
        return response


def handle(request: dict) -> dict:
    """
    End-to-end quotation flow handler.
    
    request keys:
        - shipper_id: string
        - weight_kg: number
        - distance_km: number
        - declared_value: number
        - store_available: bool (optional, default True)
        - screening_available: bool (optional, default True)
        - screening_result: int (optional, overrides service)
    
    Returns:
        Response dict with status, quote_id (if stored), price (if priced), hold flag
    """
    store = QuoteStore()
    screening = ScreeningService()
    tariff = TariffEngine()
    notification = NotificationService()
    api = QuoteAPI(store, screening, tariff, notification)
    
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    store_available = request.get("store_available", True)
    screening_available = request.get("screening_available", True)
    screening_result = request.get("screening_result")
    
    return api.request_quote(
        shipper_id=shipper_id,
        weight_kg=weight_kg,
        distance_km=distance_km,
        declared_value=declared_value,
        store_available=store_available,
        screening_available=screening_available,
        screening_result=screening_result,
    )