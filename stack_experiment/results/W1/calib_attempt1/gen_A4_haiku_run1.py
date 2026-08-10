import json
import uuid
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


class ScreeningService:
    """External screening provider."""
    
    def __init__(self, risk_index: Optional[int] = None, available: bool = True):
        self.risk_index = risk_index
        self.available = available
    
    def screen(self, shipper_id: str) -> tuple[Optional[int], bool]:
        """
        Returns (risk_index, success).
        If unavailable, returns (None, False).
        """
        if not self.available:
            return None, False
        return self.risk_index, True


class NotificationService:
    """External notification provider."""
    
    def __init__(self, available: bool = True):
        self.available = available
        self.sent_messages = []
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> bool:
        """Send quote document. Returns success."""
        if not self.available:
            return False
        self.sent_messages.append({
            "type": "quote_document",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
            "price": price
        })
        return True
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> bool:
        """Send refusal notice. Returns success."""
        if not self.available:
            return False
        self.sent_messages.append({
            "type": "refusal_notice",
            "shipper_id": shipper_id,
            "quote_id": quote_id
        })
        return True


class QuoteStore:
    """PostgreSQL 16 quote storage."""
    
    def __init__(self, available: bool = True):
        self.available = available
        self.quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float,
                    declared_value: float) -> Optional[str]:
        """
        Store a draft quote. Returns quote_id or None if unavailable.
        """
        if not self.available:
            return None
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "quote_id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": QuoteStatus.DRAFT.value,
            "price": None
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: QuoteStatus, price: Optional[float] = None) -> dict:
        """Update quote status and optionally price."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote["status"] = status.value
        if price is not None:
            quote["price"] = price
        return quote


class TariffEngine:
    """Pricing computation per DT-P."""
    
    @staticmethod
    def price(weight_kg: float, distance_km: float) -> float:
        """
        Compute price per DT-P.
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00
        P3: if distance_km >= 4912, multiply by 1.19 (applied after P2)
        P4: round to 2 decimals
        """
        base = Decimal("0.87") * Decimal(str(weight_kg)) + Decimal("1.13") * Decimal(str(distance_km))
        
        if weight_kg > 1244:
            base += Decimal("316.00")
        
        if distance_km >= 4912:
            base *= Decimal("1.19")
        
        price = float(base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        return price


class QuoteValidator:
    """Request validation per DT-V."""
    
    @staticmethod
    def validate(shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> tuple[bool, Optional[str]]:
        """
        Validate request per DT-V.
        Returns (valid, error_message).
        """
        # V1: shipper_id present and non-empty
        if not shipper_id or not isinstance(shipper_id, str):
            return False, "shipper_id missing or invalid"
        
        # V2: weight_kg number, 3 <= weight_kg <= 19400
        try:
            w = float(weight_kg)
            if w < 3 or w > 19400:
                return False, "weight_kg out of bounds"
        except (ValueError, TypeError):
            return False, "weight_kg invalid"
        
        # V3: distance_km number, 25 <= distance_km <= 7150
        try:
            d = float(distance_km)
            if d < 25 or d > 7150:
                return False, "distance_km out of bounds"
        except (ValueError, TypeError):
            return False, "distance_km invalid"
        
        # V4: declared_value number, 50 <= declared_value <= 83000
        try:
            v = float(declared_value)
            if v < 50 or v > 83000:
                return False, "declared_value out of bounds"
        except (ValueError, TypeError):
            return False, "declared_value invalid"
        
        return True, None


class QuoteAPI:
    """Main quotation orchestrator."""
    
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
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float,
                      declared_value: float) -> dict:
        """
        Main quote request flow per the sequence diagram and decision tables.
        Returns response dict with status and optional quote_id, price, hold.
        """
        
        # Step 1: Validate request (DT-V)
        valid, error_msg = QuoteValidator.validate(shipper_id, weight_kg, distance_km, declared_value)
        if not valid:
            return {"status": "rejected: invalid_request"}
        
        # Step 2: Store draft quote
        quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        if quote_id is None:
            return {"status": "error: store_unavailable"}
        
        # Step 3: Request screening
        risk_index, screening_success = self.screening_service.screen(shipper_id)
        
        # Step 4-7: Apply screening decision or handle outage
        if not screening_success:
            # Screening outage (DT-S note 5): price, store as held_unscreened, do not notify
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }
        
        # Screening succeeded: apply risk banding (DT-S)
        if risk_index <= self.ACCEPT_MAX:
            # Accept path: price, update, notify with quote document
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price)
            # Fire-and-forget notification (DT-S note 4)
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review hold path: no pricing, no notification (DT-S note 1)
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        
        elif risk_index >= self.REFUSE_MIN:
            # Refuse path: no pricing, but notify refusal (DT-S note 2)
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            # Fire-and-forget notification
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }


def handle(request: dict) -> dict:
    """
    End-to-end flow handler.
    Accepts request with keys:
      - shipper_id, weight_kg, distance_km, declared_value (required)
      - screening_service_result (optional): risk_index value
      - screening_service_available (optional, default True)
      - notification_service_available (optional, default True)
      - quote_store_available (optional, default True)
    Returns response dict with status and optional quote_id, price, hold.
    """
    
    # Extract test parameters
    risk_index = request.get("screening_service_result")
    screening_available = request.get("screening_service_available", True)
    notification_available = request.get("notification_service_available", True)
    store_available = request.get("quote_store_available", True)
    
    # Instantiate services with test overrides
    screening_service = ScreeningService(risk_index=risk_index, available=screening_available)
    notification_service = NotificationService(available=notification_available)
    quote_store = QuoteStore(available=store_available)
    tariff_engine = TariffEngine()
    
    # Create API and process request
    api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)
    
    response = api.request_quote(
        shipper_id=request.get("shipper_id", ""),
        weight_kg=request.get("weight_kg", 0),
        distance_km=request.get("distance_km", 0),
        declared_value=request.get("declared_value", 0)
    )
    
    return response