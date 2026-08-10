import json
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ScreeningStatus(Enum):
    APPROVED = "approved"
    REVIEW = "review"
    DECLINED = "declined"


class QuoteStatus(Enum):
    SUBMITTED = "submitted"
    SCREENED = "screened"
    REVIEW = "review"
    ISSUED = "issued"
    REFUSED = "refused"


@dataclass
class QuoteRequest:
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    risk_index: float
    status: QuoteStatus
    price: Optional[float] = None


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen_shipper(self, shipper_id: str) -> float:
        """
        Returns a shipper risk index (0.0 to 1.0).
        0.0-0.3: approved, 0.3-0.7: review, 0.7-1.0: declined.
        """
        return 0.25


class TariffEngine:
    """Computes freight price based on weight, distance, and tariff rules."""
    
    def compute_price(self, weight_kg: float, distance_km: float) -> float:
        """
        Computes price using simple tariff rules:
        Base: 50 EUR, Weight: 0.5 EUR/kg, Distance: 0.1 EUR/km.
        """
        base_price = 50.0
        weight_charge = weight_kg * 0.5
        distance_charge = distance_km * 0.1
        return base_price + weight_charge + distance_charge


class QuoteStore:
    """Persistent storage for quote requests and statuses."""
    
    def __init__(self):
        self.quotes = {}
        self.counter = 0
    
    def create_quote(self, request: QuoteRequest) -> str:
        """Stores a new quote request, returns quote_id."""
        self.counter += 1
        quote_id = f"QT-{self.counter:06d}"
        quote = Quote(
            quote_id=quote_id,
            shipper_id=request.shipper_id,
            weight_kg=request.weight_kg,
            distance_km=request.distance_km,
            declared_value=request.declared_value,
            risk_index=0.0,
            status=QuoteStatus.SUBMITTED
        )
        self.quotes[quote_id] = quote
        return quote_id
    
    def update_quote_screening(self, quote_id: str, risk_index: float) -> str:
        """Updates quote with screening result, returns confirmation."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self.quotes[quote_id].risk_index = risk_index
        self.quotes[quote_id].status = QuoteStatus.SCREENED
        return quote_id
    
    def update_quote_issued(self, quote_id: str, price: float) -> str:
        """Updates quote as issued with computed price, returns confirmation."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self.quotes[quote_id].price = price
        self.quotes[quote_id].status = QuoteStatus.ISSUED
        return quote_id
    
    def update_quote_review(self, quote_id: str) -> str:
        """Updates quote status to review, returns confirmation."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self.quotes[quote_id].status = QuoteStatus.REVIEW
        return quote_id
    
    def update_quote_refused(self, quote_id: str) -> str:
        """Updates quote status to refused, returns confirmation."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self.quotes[quote_id].status = QuoteStatus.REFUSED
        return quote_id
    
    def get_quote(self, quote_id: str) -> Quote:
        """Retrieves a quote by id."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        return self.quotes[quote_id]


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        """Sends issued quote document to shipper, returns confirmation."""
        return f"quote_{quote_id}_sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Sends refusal notice to shipper, returns confirmation."""
        return f"refusal_{quote_id}_sent"
    
    def send_review_notice(self, shipper_id: str, quote_id: str) -> str:
        """Sends review hold notice to shipper, returns confirmation."""
        return f"review_{quote_id}_sent"


class QuoteAPI:
    """
    Main orchestrator for quote requests.
    Validates requests, coordinates screening, pricing, storage, and notifications.
    """
    
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
    
    def validate_request(self, request_dict: dict) -> QuoteRequest:
        """Validates request structure and values."""
        required_fields = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for field in required_fields:
            if field not in request_dict:
                raise ValueError(f"Missing required field: {field}")
        
        weight = request_dict["weight_kg"]
        distance = request_dict["distance_km"]
        value = request_dict["declared_value"]
        
        if not isinstance(weight, (int, float)) or weight <= 0:
            raise ValueError("weight_kg must be a positive number")
        if not isinstance(distance, (int, float)) or distance <= 0:
            raise ValueError("distance_km must be a positive number")
        if not isinstance(value, (int, float)) or value <= 0:
            raise ValueError("declared_value must be a positive number")
        
        return QuoteRequest(
            shipper_id=request_dict["shipper_id"],
            weight_kg=float(weight),
            distance_km=float(distance),
            declared_value=float(value)
        )
    
    def handle_quote_request(self, request_dict: dict) -> dict:
        """
        Main quotation flow:
        1. Validate request
        2. Store quote record
        3. Screen shipper
        4. Determine outcome based on screening result
        5. If approved: compute price, issue quote, notify
        6. If review: mark for review, notify
        7. If declined: refuse quote, notify
        """
        try:
            validated = self.validate_request(request_dict)
        except ValueError as e:
            return {"status": f"error: {str(e)}"}
        
        try:
            quote_id = self.quote_store.create_quote(validated)
        except Exception as e:
            return {"status": f"error: failed to store quote: {str(e)}"}
        
        try:
            risk_index = self.screening_service.screen_shipper(validated.shipper_id)
        except Exception as e:
            return {"status": f"error: screening failed: {str(e)}"}
        
        try:
            self.quote_store.update_quote_screening(quote_id, risk_index)
        except Exception as e:
            return {"status": f"error: failed to update screening: {str(e)}"}
        
        if risk_index < 0.3:
            screening_outcome = ScreeningStatus.APPROVED
        elif risk_index < 0.7:
            screening_outcome = ScreeningStatus.REVIEW
        else:
            screening_outcome = ScreeningStatus.DECLINED
        
        if screening_outcome == ScreeningStatus.APPROVED:
            try:
                price = self.tariff_engine.compute_price(
                    validated.weight_kg,
                    validated.distance_km
                )
            except Exception as e:
                return {"status": f"error: pricing failed: {str(e)}"}
            
            try:
                self.quote_store.update_quote_issued(quote_id, price)
            except Exception as e:
                return {"status": f"error: failed to mark quote as issued: {str(e)}"}
            
            try:
                self.notification_service.send_quote_document(
                    validated.shipper_id,
                    quote_id,
                    price
                )
            except Exception as e:
                return {"status": f"error: notification failed: {str(e)}"}
            
            return {
                "status": "confirmed",
                "quote_id": quote_id,
                "price": price,
                "risk_index": risk_index
            }
        
        elif screening_outcome == ScreeningStatus.REVIEW:
            try:
                self.quote_store.update_quote_review(quote_id)
            except Exception as e:
                return {"status": f"error: failed to mark quote for review: {str(e)}"}
            
            try:
                self.notification_service.send_review_notice(
                    validated.shipper_id,
                    quote_id
                )
            except Exception as e:
                return {"status": f"error: notification failed: {str(e)}"}
            
            return {
                "status": "review",
                "quote_id": quote_id,
                "risk_index": risk_index
            }
        
        else:
            try:
                self.quote_store.update_quote_refused(quote_id)
            except Exception as e:
                return {"status": f"error: failed to mark quote as refused: {str(e)}"}
            
            try:
                self.notification_service.send_refusal_notice(
                    validated.shipper_id,
                    quote_id
                )
            except Exception as e:
                return {"status": f"error: notification failed: {str(e)}"}
            
            return {
                "status": "rejected",
                "quote_id": quote_id,
                "reason": "denied_party_screening",
                "risk_index": risk_index
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
    Entry point for quote requests.
    
    Supports injection of external system outcomes via special keys:
    - screening_result: override screening risk index
    - screening_status: override screening outcome ("approved", "review", "declined")
    - pricing_result: override computed price
    - store_result: override store operation result
    - notification_result: override notification result
    """
    
    original_screen = _screening_service.screen_shipper
    original_compute = _tariff_engine.compute_price
    original_create = _quote_store.create_quote
    original_update_screening = _quote_store.update_quote_screening
    original_update_issued = _quote_store.update_quote_issued
    original_update_review = _quote_store.update_quote_review
    original_update_refused = _quote_store.update_quote_refused
    original_send_quote = _notification_service.send_quote_document
    original_send_refusal = _notification_service.send_refusal_notice
    original_send_review = _notification_service.send_review_notice
    
    try:
        if "screening_result" in request:
            _screening_service.screen_shipper = lambda sid: request["screening_result"]
        
        if "pricing_result" in request:
            _tariff_engine.compute_price = lambda w, d: request["pricing_result"]
        
        if "store_status" in request and request["store_status"] == "error":
            _quote_store.create_quote = lambda req: (_ for _ in ()).throw(
                Exception("Store operation failed")
            )
        
        if "notification_status" in request and request["notification_status"] == "error":
            _notification_service.send_quote_document = lambda sid, qid, p: (_ for _ in ()).throw(
                Exception("Notification failed")
            )
            _notification_service.send_refusal_notice = lambda sid, qid: (_ for _ in ()).throw(
                Exception("Notification failed")
            )
            _notification_service.send_review_notice = lambda sid, qid: (_ for _ in ()).throw(
                Exception("Notification failed")
            )
        
        return _quote_api.handle_quote_request(request)
    
    finally:
        _screening_service.screen_shipper = original_screen
        _tariff_engine.compute_price = original_compute
        _quote_store.create_quote = original_create
        _quote_store.update_quote_screening = original_update_screening
        _quote_store.update_quote_issued = original_update_issued
        _quote_store.update_quote_review = original_update_review
        _quote_store.update_quote_refused = original_update_refused
        _notification_service.send_quote_document = original_send_quote
        _notification_service.send_refusal_notice = original_send_refusal
        _notification_service.send_review_notice = original_send_review