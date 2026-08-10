import json
import uuid
from datetime import datetime
from typing import Optional


class ScreeningService:
    """External denied-party screening provider."""
    
    def get_risk_index(self, shipper_id: str, screening_result: Optional[str] = None, screening_status: Optional[str] = None) -> int:
        """
        Return shipper risk index (higher is worse).
        In test mode, uses screening_result or screening_status to determine outcome.
        """
        if screening_status == "unavailable":
            raise Exception("screening_unavailable")
        if screening_result is not None:
            return int(screening_result)
        return 0


class TariffEngine:
    """Computes freight price per DT-P rules."""
    
    def compute_price(self, weight_kg: float, distance_km: float) -> float:
        """
        Apply pricing rules DT-P:
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
        
        price = round(base, 2)
        return price


class QuoteStore:
    """Stores quote requests and their lifecycle status."""
    
    def __init__(self):
        self.quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """
        Store a draft quote. Return quote_id.
        Raises exception if store is unavailable.
        """
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "created_at": datetime.utcnow().isoformat(),
            "price": None,
            "risk_index": None
        }
        return quote_id
    
    def update_status(self, quote_id: str, status: str, price: Optional[float] = None, risk_index: Optional[int] = None) -> str:
        """Update quote status and optionally price and risk_index. Return confirmation."""
        if quote_id not in self.quotes:
            raise Exception(f"quote_not_found: {quote_id}")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        if risk_index is not None:
            self.quotes[quote_id]["risk_index"] = risk_index
        return quote_id
    
    def get_quote(self, quote_id: str) -> dict:
        """Retrieve a quote."""
        return self.quotes.get(quote_id)


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float, notification_result: Optional[str] = None) -> str:
        """
        Send quote document to shipper. 
        Fire-and-forget: failures never change outcome.
        Returns confirmation.
        """
        if notification_result == "failed":
            return "delivery_failed"
        return f"quote_document_sent_to_{shipper_id}"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str, notification_result: Optional[str] = None) -> str:
        """
        Send refusal notice to shipper.
        Fire-and-forget: failures never change outcome.
        Returns confirmation.
        """
        if notification_result == "failed":
            return "delivery_failed"
        return f"refusal_notice_sent_to_{shipper_id}"


class QuoteAPI:
    """Orchestrates the quotation flow."""
    
    def __init__(self, quote_store: QuoteStore, screening_service: ScreeningService, 
                 tariff_engine: TariffEngine, notification_service: NotificationService):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service
    
    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, 
                         declared_value: float) -> tuple[bool, Optional[str]]:
        """
        Validate request per DT-V.
        Return (is_valid, error_message).
        """
        if not shipper_id or shipper_id == "":
            return False, "shipper_id must be non-empty"
        
        if weight_kg is None or not (3 <= weight_kg <= 19400):
            return False, "weight_kg must be between 3 and 19400"
        
        if distance_km is None or not (25 <= distance_km <= 7150):
            return False, "distance_km must be between 25 and 7150"
        
        if declared_value is None or not (50 <= declared_value <= 83000):
            return False, "declared_value must be between 50 and 83000"
        
        return True, None
    
    def request_quote(self, request: dict, screening_result: Optional[str] = None,
                     screening_status: Optional[str] = None, store_status: Optional[str] = None,
                     notification_result: Optional[str] = None) -> dict:
        """
        Handle a quote request following the flow order:
        1. Validate
        2. Store draft
        3. Screen
        4. Apply screening decision
        5. Price (if applicable)
        6. Notify (if applicable)
        7. Return response
        """
        shipper_id = request.get("shipper_id")
        weight_kg = request.get("weight_kg")
        distance_km = request.get("distance_km")
        declared_value = request.get("declared_value")
        
        is_valid, error_msg = self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if not is_valid:
            return {"status": "rejected: invalid_request"}
        
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception:
            return {"status": "error: store_unavailable"}
        
        screening_succeeded = False
        risk_index = None
        
        try:
            risk_index = self.screening_service.get_risk_index(
                shipper_id, 
                screening_result=screening_result,
                screening_status=screening_status
            )
            screening_succeeded = True
        except Exception as e:
            if "unavailable" in str(e):
                screening_succeeded = False
        
        if not screening_succeeded:
            price = self.tariff_engine.compute_price(weight_kg, distance_km)
            self.quote_store.update_status(quote_id, "held_unscreened", price=price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }
        
        ACCEPT_MAX = 41
        REVIEW_MIN = 42
        REVIEW_MAX = 66
        REFUSE_MIN = 67
        
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.compute_price(weight_kg, distance_km)
            self.quote_store.update_status(quote_id, "quoted", price=price, risk_index=risk_index)
            self.notification_service.send_quote_document(shipper_id, quote_id, price, notification_result)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_status(quote_id, "review_hold", risk_index=risk_index)
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        
        elif risk_index >= REFUSE_MIN:
            self.quote_store.update_status(quote_id, "refused_screening", risk_index=risk_index)
            self.notification_service.send_refusal_notice(shipper_id, quote_id, notification_result)
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }


def handle(request: dict) -> dict:
    """
    End-to-end quote request handler.
    
    Request keys:
    - shipper_id, weight_kg, distance_km, declared_value (core fields)
    - screening_result (int as string, e.g. "12")
    - screening_status (e.g. "unavailable")
    - store_status (e.g. "unavailable") — for testing store failure
    - notification_result (e.g. "failed")
    - <entity>_exists / <entity>_found flags (compatibility, not used here)
    
    Returns dict with at minimum a "status" key.
    """
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)
    
    screening_result = request.get("screening_result")
    screening_status = request.get("screening_status")
    store_status = request.get("store_status")
    notification_result = request.get("notification_result")
    
    if store_status == "unavailable":
        return {"status": "error: store_unavailable"}
    
    quote_request = {
        "shipper_id": request.get("shipper_id"),
        "weight_kg": request.get("weight_kg"),
        "distance_km": request.get("distance_km"),
        "declared_value": request.get("declared_value")
    }
    
    response = api.request_quote(
        quote_request,
        screening_result=screening_result,
        screening_status=screening_status,
        store_status=store_status,
        notification_result=notification_result
    )
    
    return response