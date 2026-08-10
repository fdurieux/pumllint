import uuid
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP


class ScreeningService:
    """External denied-party screening provider."""
    
    def get_risk_index(self, shipper_id: str) -> Optional[int]:
        """
        Returns the risk index for a shipper, or None if unavailable.
        Higher risk index is worse.
        """
        # This will be mocked in tests via the request dict
        return None


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules."""
    
    def compute_price(self, weight_kg: float, distance_km: float) -> float:
        """
        Compute price per DT-P:
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
        
        # Round to 2 decimals
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
        Raises exception if storage fails.
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
        """Update the status of a stored quote."""
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
        Fire-and-forget: caller ignores result.
        """
        return True
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> bool:
        """
        Send refusal notice to shipper.
        Returns True on success, False on failure.
        Fire-and-forget: caller ignores result.
        """
        return True


class QuoteAPI:
    """
    Orchestrates the quotation flow: validation, storage, screening,
    pricing, notification.
    """
    
    def __init__(self, screening_service: ScreeningService,
                 tariff_engine: TariffEngine,
                 quote_store: QuoteStore,
                 notification_service: NotificationService):
        self.screening = screening_service
        self.tariff = tariff_engine
        self.store = quote_store
        self.notification = notification_service
    
    def request_quote(self, request: dict) -> dict:
        """
        Main entry point. Orchestrates the quotation flow per spec.md.
        """
        # Step 1: Validate request (DT-V)
        validation_error = self._validate_request(request)
        if validation_error:
            return {"status": f"rejected: {validation_error}"}
        
        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]
        
        # Step 2: Store draft quote
        try:
            quote_id = self.store.store_draft(shipper_id, weight_kg, 
                                              distance_km, declared_value)
        except Exception:
            return {"status": "error: store_unavailable"}
        
        # Step 3: Request screening
        risk_index = self.screening.get_risk_index(shipper_id)
        
        # Step 4, 5, 6, 7: Apply screening decision and subsequent actions
        if risk_index is None:
            # Screening unavailable (DT-S note 5)
            self.store.update_status(quote_id, "held_unscreened")
            price = self.tariff.compute_price(weight_kg, distance_km)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }
        
        # Risk index is available
        ACCEPT_MAX = 41
        REVIEW_MIN = 42
        REVIEW_MAX = 66
        REFUSE_MIN = 67
        
        if risk_index <= ACCEPT_MAX:
            # Accept path (DT-S accept row)
            self.store.update_status(quote_id, "quoted")
            price = self.tariff.compute_price(weight_kg, distance_km)
            # Notify (fire-and-forget)
            self.notification.send_quote_document(shipper_id, quote_id, price)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # Review hold path (DT-S review row)
            self.store.update_status(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        
        elif risk_index >= REFUSE_MIN:
            # Refuse path (DT-S refuse row)
            self.store.update_status(quote_id, "refused_screening")
            # Notify (fire-and-forget)
            self.notification.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }
    
    def _validate_request(self, request: dict) -> Optional[str]:
        """
        Validate request per DT-V.
        Returns error name if invalid, None if valid.
        """
        # V1: shipper_id present and non-empty
        if "shipper_id" not in request or not request["shipper_id"]:
            return "invalid_request"
        
        # V2: weight_kg in [3, 19400]
        if "weight_kg" not in request:
            return "invalid_request"
        try:
            weight_kg = float(request["weight_kg"])
            if weight_kg < 3 or weight_kg > 19400:
                return "invalid_request"
        except (TypeError, ValueError):
            return "invalid_request"
        
        # V3: distance_km in [25, 7150]
        if "distance_km" not in request:
            return "invalid_request"
        try:
            distance_km = float(request["distance_km"])
            if distance_km < 25 or distance_km > 7150:
                return "invalid_request"
        except (TypeError, ValueError):
            return "invalid_request"
        
        # V4: declared_value in [50, 83000]
        if "declared_value" not in request:
            return "invalid_request"
        try:
            declared_value = float(request["declared_value"])
            if declared_value < 50 or declared_value > 83000:
                return "invalid_request"
        except (TypeError, ValueError):
            return "invalid_request"
        
        return None


# Singleton instances (can be swapped for mocks in tests)
_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_quote_store = QuoteStore()
_notification_service = NotificationService()
_quote_api = QuoteAPI(_screening_service, _tariff_engine, 
                      _quote_store, _notification_service)


def handle(request: dict) -> dict:
    """
    End-to-end quote request handler.
    
    Accepts a request dict that may include:
    - shipper_id, weight_kg, distance_km, declared_value: quote parameters
    - screening_service_result: mocked risk index (int) or "unavailable"
    - notification_service_result: mocked delivery outcome or "failure"
    - quote_store_result: "stored" or "error" to mock store behavior
    
    Returns a response dict with "status" and optional "quote_id", "price", "hold".
    """
    # Hook in mocked external system results
    original_screening_get = _screening_service.get_risk_index
    original_notification_quote = _notification_service.send_quote_document
    original_notification_refusal = _notification_service.send_refusal_notice
    original_store_store = _quote_store.store_draft
    
    try:
        # Mock screening service
        if "screening_service_result" in request:
            result = request["screening_service_result"]
            if result == "unavailable":
                _screening_service.get_risk_index = lambda _: None
            elif isinstance(result, int):
                _screening_service.get_risk_index = lambda _: result
        
        # Mock notification service
        if "notification_service_result" in request:
            result = request["notification_service_result"]
            if result == "failure":
                _notification_service.send_quote_document = lambda *_: False
                _notification_service.send_refusal_notice = lambda *_: False
        
        # Mock quote store
        if "quote_store_result" in request:
            result = request["quote_store_result"]
            if result == "error":
                def mock_store(*args, **kwargs):
                    raise Exception("Store unavailable")
                _quote_store.store_draft = mock_store
        
        # Build clean request for the API (remove mock flags)
        clean_request = {
            k: v for k, v in request.items()
            if not k.endswith("_result")
        }
        
        return _quote_api.request_quote(clean_request)
    
    finally:
        # Restore originals
        _screening_service.get_risk_index = original_screening_get
        _notification_service.send_quote_document = original_notification_quote
        _notification_service.send_refusal_notice = original_notification_refusal
        _quote_store.store_draft = original_store_store