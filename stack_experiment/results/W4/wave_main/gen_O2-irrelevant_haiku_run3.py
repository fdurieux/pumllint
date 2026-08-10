import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str) -> Optional[int]:
        """
        Request shipper risk index.
        Returns integer risk index (higher is worse), or None if unavailable.
        """
        return None


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules (DT-P)."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Compute freight price per DT-P.
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00
        P3: if distance_km >= 4912, multiply by 1.19 (applied after P2)
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
    """Stores quote requests and their lifecycle status in a database."""
    
    def __init__(self):
        self.quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, 
                   declared_value: float) -> Optional[str]:
        """
        Store a draft quote.
        Returns quote_id on success, None on storage failure.
        """
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
        """
        Update quote status and optionally price.
        Returns updated quote dict.
        """
        if quote_id not in self.quotes:
            return {}
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        return self.quotes[quote_id]


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> bool:
        """
        Send quote document to shipper.
        Fire-and-forget: returns True on success, False on failure (but failure never changes response).
        """
        return True
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> bool:
        """
        Send refusal notice to shipper.
        Fire-and-forget: returns True on success, False on failure (but failure never changes response).
        """
        return True


class QuoteAPI:
    """
    Orchestrates the quotation flow: validation, screening, pricing, storage, notification.
    """
    
    # DT-S screening decision thresholds
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    # DT-V validation bounds
    WEIGHT_MIN = 3
    WEIGHT_MAX = 19400
    DISTANCE_MIN = 25
    DISTANCE_MAX = 7150
    DECLARED_VALUE_MIN = 50
    DECLARED_VALUE_MAX = 83000
    
    def __init__(self, screening_service: ScreeningService, 
                 tariff_engine: TariffEngine, 
                 quote_store: QuoteStore, 
                 notification_service: NotificationService):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service
    
    def _validate_request(self, request: dict) -> tuple[bool, Optional[str]]:
        """
        Validate request per DT-V.
        Returns (is_valid, error_message).
        """
        shipper_id = request.get("shipper_id")
        weight_kg = request.get("weight_kg")
        distance_km = request.get("distance_km")
        declared_value = request.get("declared_value")
        
        # V1: shipper_id present and non-empty
        if not shipper_id or not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False, "shipper_id required and non-empty"
        
        # V2: weight_kg number in range
        if weight_kg is None or not isinstance(weight_kg, (int, float)):
            return False, "weight_kg must be a number"
        if not (self.WEIGHT_MIN <= weight_kg <= self.WEIGHT_MAX):
            return False, f"weight_kg must be between {self.WEIGHT_MIN} and {self.WEIGHT_MAX}"
        
        # V3: distance_km number in range
        if distance_km is None or not isinstance(distance_km, (int, float)):
            return False, "distance_km must be a number"
        if not (self.DISTANCE_MIN <= distance_km <= self.DISTANCE_MAX):
            return False, f"distance_km must be between {self.DISTANCE_MIN} and {self.DISTANCE_MAX}"
        
        # V4: declared_value number in range
        if declared_value is None or not isinstance(declared_value, (int, float)):
            return False, "declared_value must be a number"
        if not (self.DECLARED_VALUE_MIN <= declared_value <= self.DECLARED_VALUE_MAX):
            return False, f"declared_value must be between {self.DECLARED_VALUE_MIN} and {self.DECLARED_VALUE_MAX}"
        
        return True, None
    
    def request_quote(self, request: dict) -> dict:
        """
        Process a quote request following the quotation flow (quote_flow.puml).
        Returns response dict with status, quote_id, price, hold as applicable.
        """
        # Step 1: Validate request (DT-V)
        is_valid, error_msg = self._validate_request(request)
        if not is_valid:
            return {"status": "rejected: invalid_request"}
        
        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]
        
        # Step 2: Store draft quote
        quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        if quote_id is None:
            return {"status": "error: store_unavailable"}
        
        response = {"status": None, "quote_id": quote_id}
        
        # Step 3: Request screening
        risk_index = self.screening_service.screen(shipper_id)
        
        # Step 4 & 5 & 6: Apply screening decision and conditional processing
        if risk_index is None:
            # Screening unavailable (DT-S note 5): price anyway, hold, no notify
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            response["status"] = "held_unscreened"
            response["price"] = price
            response["hold"] = True
        elif risk_index <= self.ACCEPT_MAX:
            # Accept path (DT-S row accept): price, notify quote document
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
            response["status"] = "quoted"
            response["price"] = price
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review hold path (DT-S row review): no price, no notify
            self.quote_store.update_quote(quote_id, "review_hold")
            response["status"] = "review_hold"
        elif risk_index >= self.REFUSE_MIN:
            # Refuse path (DT-S row refuse): no price, notify refusal
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            response["status"] = "refused_screening"
        
        return response


def handle(request: dict) -> dict:
    """
    End-to-end quotation flow handler.
    
    The test harness injects outcomes via keys like:
      - screening_service_result: integer risk_index or "unavailable"
      - notification_service_status: "sent" or "failed"
      - quote_store_status: "stored" or "error"
    
    Returns a dict with "status" key naming the outcome.
    """
    screening = MockScreeningService(request)
    tariff = TariffEngine()
    store = MockQuoteStore(request)
    notification = MockNotificationService(request)
    
    api = QuoteAPI(screening, tariff, store, notification)
    return api.request_quote(request)


class MockScreeningService(ScreeningService):
    """Test-harness screening service that injects outcomes from request."""
    
    def __init__(self, request: dict):
        self.request = request
    
    def screen(self, shipper_id: str) -> Optional[int]:
        result = self.request.get("screening_service_result")
        if result == "unavailable":
            return None
        if isinstance(result, int):
            return result
        return None


class MockQuoteStore(QuoteStore):
    """Test-harness quote store that injects outcomes from request."""
    
    def __init__(self, request: dict):
        super().__init__()
        self.request = request
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float,
                   declared_value: float) -> Optional[str]:
        status = self.request.get("quote_store_status")
        if status == "error":
            return None
        return super().store_draft(shipper_id, weight_kg, distance_km, declared_value)


class MockNotificationService(NotificationService):
    """Test-harness notification service that injects outcomes from request."""
    
    def __init__(self, request: dict):
        self.request = request
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> bool:
        status = self.request.get("notification_service_status")
        if status == "failed":
            return False
        return True
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> bool:
        status = self.request.get("notification_service_status")
        if status == "failed":
            return False
        return True