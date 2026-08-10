import uuid
from typing import Any


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str, screening_result: str | int | None) -> int:
        """
        Request shipper risk index from screening service.
        Returns an integer risk index (higher is worse).
        If screening_result is "unavailable", raises an exception.
        """
        if screening_result == "unavailable":
            raise Exception("screening_unavailable")
        if isinstance(screening_result, int):
            return screening_result
        return 0


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Compute price per DT-P:
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00 (heavy surcharge)
        P3: if distance_km >= 4912, multiply by 1.19 (long-haul factor, applied after P2)
        P4: round to 2 decimals
        """
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        if weight_kg > 1244:
            base += 316.00
        
        if distance_km >= 4912:
            base *= 1.19
        
        return round(base, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""
    
    def __init__(self):
        self.quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, 
                    declared_value: float) -> str:
        """Store a draft quote and return its ID."""
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: float | None = None) -> str:
        """Update quote status and optionally price. Returns quote ID."""
        if quote_id not in self.quotes:
            raise Exception("quote_not_found")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float, 
                           notification_result: str | None) -> str:
        """Send quote document to shipper. Fire-and-forget."""
        if notification_result == "failed":
            raise Exception("notification_failed")
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str, 
                           notification_result: str | None) -> str:
        """Send refusal notice to shipper. Fire-and-forget."""
        if notification_result == "failed":
            raise Exception("notification_failed")
        return "sent"


class QuoteAPI:
    """Orchestrates quote request validation, screening, pricing, and notification."""
    
    def __init__(self, tariff_engine: TariffEngine, quote_store: QuoteStore,
                 screening_service: ScreeningService, notification_service: NotificationService):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service
    
    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, 
                         declared_value: float) -> tuple[bool, str | None]:
        """Validate request per DT-V. Returns (is_valid, error_reason)."""
        # V1: shipper_id present and non-empty
        if not shipper_id or (isinstance(shipper_id, str) and not shipper_id.strip()):
            return False, "invalid_request"
        
        # V2: weight_kg number, 3 <= weight_kg <= 19400
        try:
            w = float(weight_kg)
            if not (3 <= w <= 19400):
                return False, "invalid_request"
        except (TypeError, ValueError):
            return False, "invalid_request"
        
        # V3: distance_km number, 25 <= distance_km <= 7150
        try:
            d = float(distance_km)
            if not (25 <= d <= 7150):
                return False, "invalid_request"
        except (TypeError, ValueError):
            return False, "invalid_request"
        
        # V4: declared_value number, 50 <= declared_value <= 83000
        try:
            v = float(declared_value)
            if not (50 <= v <= 83000):
                return False, "invalid_request"
        except (TypeError, ValueError):
            return False, "invalid_request"
        
        return True, None
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float,
                     declared_value: float, screening_result: Any = None,
                     notification_result: Any = None) -> dict:
        """
        Main quotation flow. Returns response dict with status and optional fields.
        """
        # Step 1: Validate request (DT-V)
        is_valid, error = self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if not is_valid:
            return {"status": "rejected: invalid_request"}
        
        # Step 2: Store draft quote
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception:
            return {"status": "error: store_unavailable"}
        
        # Step 3: Screen the shipper
        risk_index = None
        screening_failed = False
        try:
            risk_index = self.screening_service.screen(shipper_id, screening_result)
        except Exception:
            screening_failed = True
        
        # Step 4 & 5 & 6 & 7: Apply screening decision, price if needed, notify if needed
        response = {"status": None, "quote_id": quote_id}
        
        if screening_failed:
            # Screening outage: price anyway, hold, don't notify (DT-S note 5)
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            response["status"] = "held_unscreened"
            response["price"] = price
            response["hold"] = True
        elif risk_index <= 41:  # ACCEPT_MAX = 41
            # Accept: price and notify (DT-S row accept)
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            response["status"] = "quoted"
            response["price"] = price
            # Fire-and-forget notification
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price, 
                                                             notification_result)
            except Exception:
                pass  # DT-S note 4: notification failure never changes response
        elif 42 <= risk_index <= 66:  # REVIEW_MIN = 42, REVIEW_MAX = 66
            # Review: hold, don't price, don't notify (DT-S row review)
            self.quote_store.update_quote(quote_id, "review_hold")
            response["status"] = "review_hold"
        elif risk_index >= 67:  # REFUSE_MIN = 67
            # Refuse: don't price, do notify (DT-S row refuse)
            self.quote_store.update_quote(quote_id, "refused_screening")
            response["status"] = "refused_screening"
            # Fire-and-forget notification
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id, 
                                                             notification_result)
            except Exception:
                pass  # DT-S note 4: notification failure never changes response
        
        return response


def handle(request: dict) -> dict:
    """
    Run one end-to-end quotation flow.
    
    Input dict keys:
    - shipper_id, weight_kg, distance_km, declared_value: request fields
    - screening_result: int risk index, "unavailable", or None
    - notification_result: "failed", "sent", or None
    
    Returns dict with "status" key and optional quote_id, price, hold.
    """
    # Initialize collaborators
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    
    quote_api = QuoteAPI(tariff_engine, quote_store, screening_service, notification_service)
    
    # Extract request fields
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    screening_result = request.get("screening_result")
    notification_result = request.get("notification_result")
    
    # Execute quotation flow
    response = quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value,
                                      screening_result, notification_result)
    
    return response