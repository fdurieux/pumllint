import uuid
import json
from typing import Optional


class ScreeningService:
    """External denied-party screening provider."""
    
    def get_risk_index(self, shipper_id: str) -> Optional[int]:
        """Returns risk index (int, higher is worse) or None if unavailable."""
        # Stubbed for testing; injected via test harness
        return None


class TariffEngine:
    """Computes freight price per tariff rules (DT-P)."""
    
    def compute_price(self, weight_kg: float, distance_km: float) -> float:
        """Returns price as float, rounded to 2 decimals."""
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


class QuoteStore:
    """Persistent storage of quote records."""
    
    def __init__(self):
        self.quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, 
                    declared_value: float) -> str:
        """Stores a draft quote, returns quote_id. Raises exception on failure."""
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "risk_index": None,
            "price": None,
        }
        return quote_id
    
    def update_status(self, quote_id: str, status: str, risk_index: Optional[int] = None,
                      price: Optional[float] = None) -> None:
        """Updates quote status and optionally risk_index and price."""
        if quote_id in self.quotes:
            self.quotes[quote_id]["status"] = status
            if risk_index is not None:
                self.quotes[quote_id]["risk_index"] = risk_index
            if price is not None:
                self.quotes[quote_id]["price"] = price


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def send_quote_document(self, quote_id: str, shipper_id: str, price: float) -> bool:
        """Sends quote document. Returns True on success, False on failure."""
        # Stubbed; injected via test harness
        return True
    
    def send_refusal_notice(self, quote_id: str, shipper_id: str) -> bool:
        """Sends refusal notice. Returns True on success, False on failure."""
        # Stubbed; injected via test harness
        return True


class QuoteAPI:
    """Main orchestrator for quote requests."""
    
    # DT-S boundary constants
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
    
    def _validate_request(self, request: dict) -> tuple[bool, str]:
        """Validates request per DT-V. Returns (valid, error_message)."""
        # V1: shipper_id present and non-empty
        shipper_id = request.get("shipper_id", "")
        if not isinstance(shipper_id, str) or not shipper_id:
            return False, "rejected: invalid_request"
        
        # V2: weight_kg
        try:
            weight_kg = float(request.get("weight_kg", 0))
            if not (3 <= weight_kg <= 19400):
                return False, "rejected: invalid_request"
        except (TypeError, ValueError):
            return False, "rejected: invalid_request"
        
        # V3: distance_km
        try:
            distance_km = float(request.get("distance_km", 0))
            if not (25 <= distance_km <= 7150):
                return False, "rejected: invalid_request"
        except (TypeError, ValueError):
            return False, "rejected: invalid_request"
        
        # V4: declared_value
        try:
            declared_value = float(request.get("declared_value", 0))
            if not (50 <= declared_value <= 83000):
                return False, "rejected: invalid_request"
        except (TypeError, ValueError):
            return False, "rejected: invalid_request"
        
        return True, ""
    
    def handle_request(self, request: dict) -> dict:
        """Main flow: validate, store, screen, price, notify, return."""
        
        # Step 1: Validate per DT-V
        valid, error = self._validate_request(request)
        if not valid:
            return {"status": error}
        
        shipper_id = request["shipper_id"]
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])
        
        # Step 2: Store draft
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, 
                                                      declared_value)
        except Exception:
            return {"status": "error: store_unavailable"}
        
        # Step 3: Request screening
        risk_index = self.screening_service.get_risk_index(shipper_id)
        
        # Step 4 & 5 & 6: Apply screening decision, price if needed, notify if needed
        response = {"status": None, "quote_id": quote_id}
        
        if risk_index is None:
            # Screening unavailable: price and hold
            price = self.tariff_engine.compute_price(weight_kg, distance_km)
            self.quote_store.update_status(quote_id, "held_unscreened", price=price)
            response["status"] = "held_unscreened"
            response["price"] = price
            response["hold"] = True
        elif risk_index <= self.ACCEPT_MAX:
            # Accept: price and notify
            price = self.tariff_engine.compute_price(weight_kg, distance_km)
            self.quote_store.update_status(quote_id, "quoted", risk_index=risk_index, price=price)
            self.notification_service.send_quote_document(quote_id, shipper_id, price)
            response["status"] = "quoted"
            response["price"] = price
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review: hold without price
            self.quote_store.update_status(quote_id, "review_hold", risk_index=risk_index)
            response["status"] = "review_hold"
        elif risk_index >= self.REFUSE_MIN:
            # Refuse: notify refusal
            self.quote_store.update_status(quote_id, "refused_screening", risk_index=risk_index)
            self.notification_service.send_refusal_notice(quote_id, shipper_id)
            response["status"] = "refused_screening"
        
        return response


# Global instances (in a real system, injected via DI container)
_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_quote_store = QuoteStore()
_notification_service = NotificationService()
_quote_api = QuoteAPI(_screening_service, _tariff_engine, _quote_store, _notification_service)


def handle(request: dict) -> dict:
    """Module-level entry point: processes a quote request end-to-end."""
    # Inject test doubles if provided in request (convention: *_result, *_status keys)
    if "screening_result" in request:
        _screening_service.get_risk_index = lambda shipper_id: request["screening_result"]
    
    if "notification_status" in request:
        if request["notification_status"] == "error":
            _notification_service.send_quote_document = lambda q, s, p: False
            _notification_service.send_refusal_notice = lambda q, s: False
        else:
            _notification_service.send_quote_document = lambda q, s, p: True
            _notification_service.send_refusal_notice = lambda q, s: True
    
    if "store_result" in request:
        if request["store_result"] == "error":
            original_store = _quote_store.store_draft
            def failing_store(*args, **kwargs):
                raise Exception("Store unavailable")
            _quote_store.store_draft = failing_store
    
    # Clean up request to pass only the fields expected by QuoteAPI
    clean_request = {
        "shipper_id": request.get("shipper_id", ""),
        "weight_kg": request.get("weight_kg"),
        "distance_km": request.get("distance_km"),
        "declared_value": request.get("declared_value"),
    }
    
    return _quote_api.handle_request(clean_request)