from dataclasses import dataclass
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP
import json


@dataclass
class ValidationError(Exception):
    field: str
    rule: str


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str) -> int:
        """
        Returns shipper risk index (higher is worse).
        In real implementation, calls external REST API.
        In testing, behavior is injected via handle()'s screening_result key.
        """
        raise NotImplementedError("Must be mocked in tests")


class TariffEngine:
    """Computes freight price per DT-P rules."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Pricing per DT-P: base + heavy surcharge (if weight > 1244) + 
        long-haul multiplier (if distance >= 4912).
        """
        weight_kg = float(weight_kg)
        distance_km = float(distance_km)
        
        base = Decimal("0.87") * Decimal(str(weight_kg)) + Decimal("1.13") * Decimal(str(distance_km))
        
        if weight_kg > 1244:
            base += Decimal("316.00")
        
        if distance_km >= 4912:
            base *= Decimal("1.19")
        
        price = base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(price)


class QuoteStore:
    """Stores quote requests and lifecycle status."""
    
    def __init__(self):
        self.quotes = {}
        self.next_id = 1
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, 
                    declared_value: float) -> str:
        """
        Stores a draft quote, returns quote_id.
        In testing, store_unavailable is simulated by raising or by 
        external injection (quote_store_result key).
        """
        quote_id = f"Q{self.next_id}"
        self.next_id += 1
        self.quotes[quote_id] = {
            "quote_id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        """Updates quote status and optionally price; returns updated quote."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote["status"] = status
        if price is not None:
            quote["price"] = price
        return quote


class NotificationService:
    """External messaging provider."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        """
        Fire-and-forget: sends quote document.
        Returns confirmation string; delivery failure never changes response.
        """
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """
        Fire-and-forget: sends refusal notice.
        Returns confirmation string; delivery failure never changes response.
        """
        return "sent"


class QuoteAPI:
    """Main quotation orchestrator."""
    
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def __init__(self, screening_service: ScreeningService, 
                 tariff_engine: TariffEngine,
                 quote_store: QuoteStore,
                 notification_service: NotificationService):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service
    
    def _validate_request(self, shipper_id: str, weight_kg: float, 
                         distance_km: float, declared_value: float) -> None:
        """
        Validates request per DT-V.
        Raises ValidationError on any violation.
        """
        if not shipper_id or shipper_id.strip() == "":
            raise ValidationError("shipper_id", "present and non-empty")
        
        try:
            weight_kg = float(weight_kg)
        except (TypeError, ValueError):
            raise ValidationError("weight_kg", "must be a number")
        if not (3 <= weight_kg <= 19400):
            raise ValidationError("weight_kg", "3 <= weight_kg <= 19400")
        
        try:
            distance_km = float(distance_km)
        except (TypeError, ValueError):
            raise ValidationError("distance_km", "must be a number")
        if not (25 <= distance_km <= 7150):
            raise ValidationError("distance_km", "25 <= distance_km <= 7150")
        
        try:
            declared_value = float(declared_value)
        except (TypeError, ValueError):
            raise ValidationError("declared_value", "must be a number")
        if not (50 <= declared_value <= 83000):
            raise ValidationError("declared_value", "50 <= declared_value <= 83000")
    
    def request_quote(self, shipper_id: str, weight_kg: float, 
                     distance_km: float, declared_value: float) -> dict:
        """
        Main quotation flow per the sequence diagram and decision tables.
        Returns dict with status, quote_id, price (if applicable), hold flag.
        """
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError:
            return {"status": "rejected: invalid_request"}
        
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception:
            return {"status": "error: store_unavailable"}
        
        response = {
            "status": None,
            "quote_id": quote_id,
            "price": None,
            "hold": False,
        }
        
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception:
            risk_index = None
        
        if risk_index is None:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            response["status"] = "held_unscreened"
            response["price"] = price
            response["hold"] = True
            return response
        
        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
            response["status"] = "quoted"
            response["price"] = price
            return response
        
        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            response["status"] = "review_hold"
            return response
        
        if risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            response["status"] = "refused_screening"
            return response
        
        return {"status": "error: unknown_screening_outcome"}


class TestScreeningService(ScreeningService):
    """Test double: returns injected risk index."""
    
    def __init__(self, risk_index: Optional[int] = None, error: bool = False):
        self.risk_index = risk_index
        self.error = error
    
    def screen(self, shipper_id: str) -> int:
        if self.error:
            raise Exception("Screening service unavailable")
        if self.risk_index is None:
            raise Exception("Screening service unavailable")
        return self.risk_index


class TestQuoteStore(QuoteStore):
    """Test double: can be configured to fail."""
    
    def __init__(self, fail: bool = False):
        super().__init__()
        self.fail = fail
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, 
                    declared_value: float) -> str:
        if self.fail:
            raise Exception("Store unavailable")
        return super().store_draft(shipper_id, weight_kg, distance_km, declared_value)


def handle(request: dict) -> dict:
    """
    End-to-end quote request handler.
    
    request keys:
      - shipper_id, weight_kg, distance_km, declared_value: quote request fields
      - quote_store_result: "stored" or "failed" (simulates store outcome)
      - screening_result: integer risk_index, "unavailable", or None
      - notification_result: "sent", "failed", or None
    
    Returns dict with status and optional quote_id, price, hold.
    """
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    store_result = request.get("quote_store_result", "stored")
    screening_result = request.get("screening_result")
    
    screening_service = TestScreeningService(
        risk_index=screening_result if isinstance(screening_result, int) else None,
        error=(screening_result == "unavailable")
    )
    
    quote_store = TestQuoteStore(fail=(store_result == "failed"))
    
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    
    api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)
    
    result = api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    
    clean_result = {k: v for k, v in result.items() if v is not None and (k != "hold" or v)}
    
    return clean_result