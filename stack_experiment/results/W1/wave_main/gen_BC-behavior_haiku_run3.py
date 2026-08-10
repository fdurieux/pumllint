import uuid
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP


class ScreeningService:
    """External denied-party screening provider."""
    
    def get_risk_index(self, shipper_id: str) -> Optional[int]:
        """
        Returns the risk index for a shipper, or None if unavailable.
        Higher index is worse.
        """
        return None


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    def compute_price(self, weight_kg: float, distance_km: float) -> float:
        """
        Apply DT-P pricing rules:
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
        
        price = float(base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        return price


class QuoteStore:
    """Stores quote requests and their lifecycle status."""
    
    def __init__(self):
        self.quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, 
                   distance_km: float, declared_value: float) -> str:
        """
        Store a draft quote. Returns quote_id.
        Raises exception on storage failure.
        """
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft"
        }
        return quote_id
    
    def update_status(self, quote_id: str, status: str) -> None:
        """Update the stored quote status."""
        if quote_id in self.quotes:
            self.quotes[quote_id]["status"] = status
    
    def get_quote(self, quote_id: str) -> Optional[dict]:
        """Retrieve a stored quote."""
        return self.quotes.get(quote_id)


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> bool:
        """
        Send quote document to shipper.
        Returns True on success, False on failure.
        Failure never changes the response or stored outcome.
        """
        return True
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> bool:
        """
        Send refusal notice to shipper.
        Returns True on success, False on failure.
        Failure never changes the response or stored outcome.
        """
        return True


class QuoteAPI:
    """
    Main orchestrator: receives quote requests, validates, screens,
    prices, stores, and notifies.
    """
    
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def __init__(self, screening_service: ScreeningService,
                 tariff_engine: TariffEngine,
                 quote_store: QuoteStore,
                 notification_service: NotificationService):
        self.screening = screening_service
        self.tariff = tariff_engine
        self.store = quote_store
        self.notification = notification_service
    
    def validate_request(self, request: dict) -> tuple[bool, Optional[str]]:
        """
        Validate request against DT-V.
        Returns (valid, error_message).
        """
        if "shipper_id" not in request or not request["shipper_id"]:
            return False, "shipper_id missing or empty"
        
        weight_kg = request.get("weight_kg")
        if weight_kg is None or not (3 <= weight_kg <= 19400):
            return False, f"weight_kg out of range [3, 19400]: {weight_kg}"
        
        distance_km = request.get("distance_km")
        if distance_km is None or not (25 <= distance_km <= 7150):
            return False, f"distance_km out of range [25, 7150]: {distance_km}"
        
        declared_value = request.get("declared_value")
        if declared_value is None or not (50 <= declared_value <= 83000):
            return False, f"declared_value out of range [50, 83000]: {declared_value}"
        
        return True, None
    
    def handle_request(self, request: dict) -> dict:
        """
        Main flow: validate → store → screen → price → notify → return.
        """
        valid, error_msg = self.validate_request(request)
        if not valid:
            return {"status": "rejected: invalid_request"}
        
        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]
        
        try:
            quote_id = self.store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except Exception:
            return {"status": "error: store_unavailable"}
        
        risk_index = self.screening.get_risk_index(shipper_id)
        
        if risk_index is None:
            price = self.tariff.compute_price(weight_kg, distance_km)
            self.store.update_status(quote_id, "held_unscreened")
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }
        
        if risk_index <= self.ACCEPT_MAX:
            self.store.update_status(quote_id, "quoted")
            price = self.tariff.compute_price(weight_kg, distance_km)
            self.notification.send_quote_document(shipper_id, quote_id, price)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.store.update_status(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        
        elif risk_index >= self.REFUSE_MIN:
            self.store.update_status(quote_id, "refused_screening")
            self.notification.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }


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
    End-to-end quote request handler.
    
    Simulates external system outcomes from request keys:
    - "screening_result" (int): risk index to return
    - "screening_status" (str): "unavailable" to simulate outage
    - "store_status" (str): "error" to simulate storage failure
    - "notification_status" (str): "failed" to simulate delivery failure
    """
    global _screening_service, _notification_service
    
    original_screening = _screening_service
    original_notification = _notification_service
    
    try:
        if "screening_status" in request:
            if request["screening_status"] == "unavailable":
                class UnavailableScreening:
                    def get_risk_index(self, shipper_id: str):
                        return None
                _screening_service = UnavailableScreening()
        
        if "screening_result" in request:
            risk_index_value = request["screening_result"]
            class MockScreening:
                def get_risk_index(self, shipper_id: str):
                    return risk_index_value
            _screening_service = MockScreening()
        
        if "notification_status" in request and request["notification_status"] == "failed":
            class FailedNotification:
                def send_quote_document(self, shipper_id: str, quote_id: str, price: float):
                    return False
                def send_refusal_notice(self, shipper_id: str, quote_id: str):
                    return False
            _notification_service = FailedNotification()
        
        if "store_status" in request and request["store_status"] == "error":
            class FailedStore:
                def store_draft(self, shipper_id: str, weight_kg: float,
                               distance_km: float, declared_value: float):
                    raise Exception("storage failure")
                def update_status(self, quote_id: str, status: str):
                    pass
                def get_quote(self, quote_id: str):
                    return None
            _quote_api.store = FailedStore()
        
        _quote_api.screening = _screening_service
        _quote_api.notification = _notification_service
        
        clean_request = {
            k: v for k, v in request.items()
            if not k.endswith("_result") and not k.endswith("_status")
        }
        
        return _quote_api.handle_request(clean_request)
    
    finally:
        _screening_service = original_screening
        _notification_service = original_notification