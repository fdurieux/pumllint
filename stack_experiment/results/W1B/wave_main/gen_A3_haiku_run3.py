import uuid
import json
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


# ============================================================================
# EXTERNAL SYSTEMS (outside the system boundary)
# ============================================================================

class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str, screening_result: Optional[int] = None) -> int:
        """
        Request shipper risk index from screening service.
        Returns the risk index (higher is worse).
        If screening_result key is set, that overrides the default.
        """
        if screening_result is not None:
            return screening_result
        return 30  # Default: safe score


class TariffEngine:
    """Tariff computation engine."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Compute freight price per DT-P.
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00
        P3: if distance_km >= 4912, multiply by 1.19 (after P2)
        P4: round to 2 decimal places
        """
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        if weight_kg > 1244:
            base += 316.00
        
        if distance_km >= 4912:
            base *= 1.19
        
        return round(base, 2)


class QuoteStore:
    """Quote storage (PostgreSQL simulation)."""

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
        """Store draft quote; return quote_id."""
        if store_result == "unavailable":
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
            "created_at": datetime.utcnow().isoformat()
        }
        return quote_id

    def update_quote(
        self,
        quote_id: str,
        status: str,
        price: Optional[float] = None
    ) -> dict:
        """Update quote status and optionally price."""
        if quote_id in self.quotes:
            self.quotes[quote_id]["status"] = status
            if price is not None:
                self.quotes[quote_id]["price"] = price
            return self.quotes[quote_id]
        raise Exception(f"Quote {quote_id} not found")


class NotificationService:
    """External notification provider (fire-and-forget)."""

    def send_quote_document(
        self,
        shipper_id: str,
        quote_id: str,
        price: float,
        notification_result: Optional[str] = None
    ) -> str:
        """Send quote document; returns confirmation or error."""
        if notification_result == "failed":
            return "delivery_failed"
        return "sent"

    def send_refusal_notice(
        self,
        shipper_id: str,
        quote_id: str,
        notification_result: Optional[str] = None
    ) -> str:
        """Send refusal notice; returns confirmation or error."""
        if notification_result == "failed":
            return "delivery_failed"
        return "sent"


# ============================================================================
# QUOTE API (main orchestrator)
# ============================================================================

class QuoteAPI:
    """Main quotation orchestrator."""

    # DT-S boundaries
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
        """
        Validate request per DT-V.
        V1: shipper_id present and non-empty
        V2: weight_kg in [3, 19400]
        V3: distance_km in [25, 7150]
        V4: declared_value in [50, 83000]
        """
        shipper_id = request.get("shipper_id")
        if not shipper_id or not isinstance(shipper_id, str) or len(shipper_id) == 0:
            return False, "shipper_id missing or invalid"

        weight_kg = request.get("weight_kg")
        if weight_kg is None or not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False, "weight_kg out of bounds [3, 19400]"

        distance_km = request.get("distance_km")
        if distance_km is None or not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False, "distance_km out of bounds [25, 7150]"

        declared_value = request.get("declared_value")
        if declared_value is None or not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False, "declared_value out of bounds [50, 83000]"

        return True, None

    def request_quote(self, request: dict) -> dict:
        """
        Main flow: validate → store → screen → apply decision → price → notify → respond.
        """
        # Step 1: Validate
        valid, error_msg = self.validate_request(request)
        if not valid:
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]

        # Step 2: Store draft
        try:
            store_result = request.get("store_result")
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, store_result
            )
        except Exception:
            return {"status": "error: store_unavailable"}

        # Step 3: Screen the shipper
        screening_result = request.get("screening_result")
        try:
            if screening_result is not None:
                risk_index = screening_result
            else:
                risk_index = self.screening_service.screen(shipper_id, screening_result)
            screening_available = True
        except Exception:
            screening_available = False
            risk_index = None

        # Step 4-7: Apply decision based on screening outcome
        if not screening_available:
            # DT-S note 5: screening outage → price anyway, hold, no notify
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }

        # Screening is available; apply DT-S decision
        if risk_index <= self.ACCEPT_MAX:
            # DT-S row: accept
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price, request.get("notification_result"))
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # DT-S row: review (no price, no notify)
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        elif risk_index >= self.REFUSE_MIN:
            # DT-S row: refuse (no price, notify refusal)
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id, request.get("notification_result"))
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }

        # Should not reach here
        return {"status": "error: unexpected_state"}


# ============================================================================
# MODULE-LEVEL HANDLE FUNCTION
# ============================================================================

_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_quote_store = QuoteStore()
_notification_service = NotificationService()
_quote_api = QuoteAPI(
    _screening_service,
    _tariff_engine,
    _quote_store,
    _notification_service
)


def handle(request: dict) -> dict:
    """
    End-to-end quotation flow.
    
    Input: dict with keys:
      - shipper_id, weight_kg, distance_km, declared_value (request fields)
      - screening_result: int (overrides screening service result)
      - store_result: str (e.g. "unavailable" to trigger store failure)
      - notification_result: str (e.g. "failed" for notification failures)
    
    Output: dict with status and optional quote_id, price, hold.
    """
    return _quote_api.request_quote(request)