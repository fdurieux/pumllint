from dataclasses import dataclass
from datetime import datetime
from typing import Optional


# ============================================================================
# External Systems (outside the system boundary)
# ============================================================================

class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str, screening_result: Optional[str] = None) -> int:
        """
        Returns a risk index (higher is worse).
        In tests, screening_result key overrides with a numeric value or error.
        """
        if screening_result == "error":
            raise Exception("screening_unavailable")
        if isinstance(screening_result, int):
            return screening_result
        # Default: return a moderate risk index (review band)
        return 50


class NotificationService:
    """External messaging provider."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, 
                           price_amount: float) -> str:
        """Fire-and-forget send. Returns confirmation string."""
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Fire-and-forget send. Returns confirmation string."""
        return "sent"


# ============================================================================
# Tariff Engine
# ============================================================================

class TariffEngine:
    """Computes freight price from weight and distance per tariff rules."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Apply DT-P pricing rules:
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00
        P3: if distance_km >= 4912, multiply by 1.19 (after P2)
        P4: round to 2 decimals
        """
        # P1: base calculation
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        # P2: heavy surcharge
        if weight_kg > 1244:
            base += 316.00
        
        # P3: long-haul multiplier (applied after P2)
        if distance_km >= 4912:
            base *= 1.19
        
        # P4: round to 2 decimals
        return round(base, 2)


# ============================================================================
# Quote Store
# ============================================================================

@dataclass
class QuoteRecord:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: str
    price_amount: Optional[float] = None
    created_at: str = None
    updated_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow().isoformat()


class QuoteStore:
    """PostgreSQL-backed quote storage."""
    
    def __init__(self):
        self.quotes = {}  # quote_id -> QuoteRecord
        self._counter = 0
    
    def store_draft(self, shipper_id: str, weight_kg: float, 
                   distance_km: float, declared_value: float,
                   store_result: Optional[str] = None) -> str:
        """
        Store a draft quote request.
        Returns quote_id on success; raises on storage failure.
        """
        if store_result == "error":
            raise Exception("store_unavailable")
        
        self._counter += 1
        quote_id = f"quote_{self._counter:06d}"
        
        record = QuoteRecord(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status="draft"
        )
        self.quotes[quote_id] = record
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, 
                    price_amount: Optional[float] = None) -> dict:
        """
        Update a quote's status and optionally price.
        Returns the updated record as a dict.
        """
        if quote_id not in self.quotes:
            raise Exception(f"quote_not_found: {quote_id}")
        
        record = self.quotes[quote_id]
        record.status = status
        if price_amount is not None:
            record.price_amount = price_amount
        record.updated_at = datetime.utcnow().isoformat()
        
        return {
            "quote_id": record.quote_id,
            "shipper_id": record.shipper_id,
            "weight_kg": record.weight_kg,
            "distance_km": record.distance_km,
            "declared_value": record.declared_value,
            "status": record.status,
            "price_amount": record.price_amount,
            "created_at": record.created_at,
            "updated_at": record.updated_at
        }


# ============================================================================
# Quote API (orchestration)
# ============================================================================

class QuoteAPI:
    """
    Quote request orchestration: validates, screens, prices, stores,
    and notifies per the quotation flow.
    """
    
    # DT-S thresholds
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def __init__(self, store: QuoteStore, screening: ScreeningService,
                 tariff: TariffEngine, notification: NotificationService):
        self.store = store
        self.screening = screening
        self.tariff = tariff
        self.notification = notification
    
    def _validate_request(self, shipper_id: str, weight_kg: float,
                         distance_km: float, declared_value: float) -> tuple:
        """
        DT-V: validate request bounds.
        Returns (is_valid, error_msg) tuple.
        """
        # V1: shipper_id present and non-empty
        if not shipper_id or shipper_id == "":
            return (False, "shipper_id_empty")
        
        # V2: weight_kg in [3, 19400]
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return (False, "weight_kg_invalid")
        
        # V3: distance_km in [25, 7150]
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return (False, "distance_km_invalid")
        
        # V4: declared_value in [50, 83000]
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return (False, "declared_value_invalid")
        
        return (True, None)
    
    def request_quote(self, shipper_id: str, weight_kg: float,
                     distance_km: float, declared_value: float,
                     store_result: Optional[str] = None,
                     screening_result: Optional[int] = None) -> dict:
        """
        Main quotation flow per behavior/quote_flow.puml and decision tables.
        
        Args:
            shipper_id, weight_kg, distance_km, declared_value: request fields
            store_result: inject "error" to simulate store unavailability
            screening_result: inject risk index or "error" to override screening
        
        Returns:
            dict with "status" key and outcome details
        """
        
        # ====== Validation (DT-V) ======
        is_valid, error_msg = self._validate_request(
            shipper_id, weight_kg, distance_km, declared_value
        )
        if not is_valid:
            return {"status": "rejected: invalid_request", "error": error_msg}
        
        # ====== Store draft ======
        try:
            quote_id = self.store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value,
                store_result=store_result
            )
        except Exception as e:
            if "store_unavailable" in str(e):
                return {"status": "error: store_unavailable"}
            raise
        
        # ====== Screening (DT-S) ======
        risk_index = None
        screening_failed = False
        try:
            risk_index = self.screening.screen(shipper_id, screening_result=screening_result)
        except Exception as e:
            if "screening_unavailable" in str(e):
                screening_failed = True
            else:
                raise
        
        # ====== Decision tree based on risk index ======
        
        if screening_failed:
            # Screening outage path (DT-S note 5):
            # Price anyway, store as held_unscreened, don't notify
            price_amount = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price_amount": price_amount,
                "hold": True
            }
        
        elif risk_index <= self.ACCEPT_MAX:
            # Accept path (DT-S row accept):
            # Price, store as quoted, notify with quote document
            price_amount = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "quoted", price_amount)
            # Fire-and-forget notification (DT-S note 4)
            try:
                self.notification.send_quote_document(shipper_id, quote_id, price_amount)
            except Exception:
                pass  # Delivery failure never changes the response
            
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price_amount": price_amount
            }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review hold path (DT-S row review):
            # No pricing, no notification, store as review_hold
            self.store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        
        elif risk_index >= self.REFUSE_MIN:
            # Refuse path (DT-S row refuse):
            # No pricing, store as refused_screening, notify refusal
            self.store.update_quote(quote_id, "refused_screening")
            # Fire-and-forget notification (DT-S note 2)
            try:
                self.notification.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass  # Delivery failure never changes the response
            
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }
        
        # Should not reach here given the conditions above
        return {"status": "error: unknown_state"}


# ============================================================================
# Module-level handle function
# ============================================================================

def handle(request: dict) -> dict:
    """
    Run one end-to-end quotation flow.
    
    Input dict keys:
      - shipper_id, weight_kg, distance_km, declared_value: request fields
      - store_result (optional): "error" for store unavailability
      - screening_result (optional): risk index (int) or "error"
    
    Returns:
      dict with "status" key describing outcome
    """
    
    # Extract request fields
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    # Extract test injection keys
    store_result = request.get("store_result")
    screening_result = request.get("screening_result")
    
    # Instantiate collaborators
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    
    # Instantiate and run API
    api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)
    
    return api.request_quote(
        shipper_id=shipper_id,
        weight_kg=weight_kg,
        distance_km=distance_km,
        declared_value=declared_value,
        store_result=store_result,
        screening_result=screening_result
    )