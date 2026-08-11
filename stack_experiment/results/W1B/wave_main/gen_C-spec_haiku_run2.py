from dataclasses import dataclass
from typing import Optional
from enum import Enum
import uuid


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: QuoteStatus
    price: Optional[float] = None


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str) -> int:
        """Return risk index for shipper. Higher is worse."""
        raise NotImplementedError("To be mocked in tests")


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """Apply DT-P pricing rules."""
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        if weight_kg > 1244:
            base += 316.00
        
        if distance_km >= 4912:
            base *= 1.19
        
        return round(base, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""
    
    def __init__(self):
        self._quotes = {}
    
    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """Store draft quote; return quote_id."""
        quote_id = str(uuid.uuid4())
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT,
        )
        self._quotes[quote_id] = quote
        return quote_id
    
    def update_quote(
        self,
        quote_id: str,
        status: QuoteStatus,
        price: Optional[float] = None,
    ) -> Quote:
        """Update quote status and optionally price."""
        if quote_id not in self._quotes:
            raise StorageError(f"Quote {quote_id} not found")
        quote = self._quotes[quote_id]
        quote.status = status
        if price is not None:
            quote.price = price
        return quote
    
    def get_quote(self, quote_id: str) -> Quote:
        """Retrieve quote by id."""
        if quote_id not in self._quotes:
            raise StorageError(f"Quote {quote_id} not found")
        return self._quotes[quote_id]


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def send_quote_document(
        self,
        shipper_id: str,
        quote_id: str,
        price: float,
    ) -> str:
        """Send quote document; return confirmation string."""
        raise NotImplementedError("To be mocked in tests")
    
    def send_refusal_notice(
        self,
        shipper_id: str,
        quote_id: str,
    ) -> str:
        """Send refusal notice; return confirmation string."""
        raise NotImplementedError("To be mocked in tests")


class QuoteAPI:
    """Orchestrates quote requests: validation, screening, pricing, notification."""
    
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def __init__(
        self,
        quote_store: QuoteStore,
        screening_service: ScreeningService,
        tariff_engine: TariffEngine,
        notification_service: NotificationService,
    ):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service
    
    def _validate_request(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> None:
        """Validate request per DT-V."""
        if not shipper_id or not isinstance(shipper_id, str):
            raise ValidationError("shipper_id: present and non-empty")
        
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            raise ValidationError("weight_kg: 3 <= weight_kg <= 19400")
        
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            raise ValidationError("distance_km: 25 <= distance_km <= 7150")
        
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            raise ValidationError("declared_value: 50 <= declared_value <= 83000")
    
    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> dict:
        """Main quotation flow."""
        try:
            self._validate_request(
                shipper_id,
                weight_kg,
                distance_km,
                declared_value,
            )
        except ValidationError as e:
            return {"status": "rejected: invalid_request"}
        
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id,
                weight_kg,
                distance_km,
                declared_value,
            )
        except StorageError:
            return {"status": "error: store_unavailable"}
        
        screening_error = False
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            screening_error = True
            risk_index = None
        
        if screening_error:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.HELD_UNSCREENED,
                price,
            )
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }
        
        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.QUOTED,
                price,
            )
            try:
                self.notification_service.send_quote_document(
                    shipper_id,
                    quote_id,
                    price,
                )
            except Exception:
                pass
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.REVIEW_HOLD,
            )
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        
        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(
                quote_id,
                QuoteStatus.REFUSED_SCREENING,
            )
            try:
                self.notification_service.send_refusal_notice(
                    shipper_id,
                    quote_id,
                )
            except Exception:
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }


def handle(request: dict) -> dict:
    """Run one end-to-end flow."""
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    
    class MockScreeningService(ScreeningService):
        def screen(self, shipper_id: str) -> int:
            if "screening_result" in request:
                result = request["screening_result"]
                if result == "error":
                    raise ScreeningError("Screening service unavailable")
                try:
                    return int(result)
                except (ValueError, TypeError):
                    raise ScreeningError(f"Invalid screening result: {result}")
            return 30
    
    class MockNotificationService(NotificationService):
        def send_quote_document(
            self,
            shipper_id: str,
            quote_id: str,
            price: float,
        ) -> str:
            if request.get("notification_status") == "error":
                raise Exception("Notification service unavailable")
            return "sent"
        
        def send_refusal_notice(
            self,
            shipper_id: str,
            quote_id: str,
        ) -> str:
            if request.get("notification_status") == "error":
                raise Exception("Notification service unavailable")
            return "sent"
    
    class MockQuoteStore(QuoteStore):
        def store_draft(
            self,
            shipper_id: str,
            weight_kg: float,
            distance_km: float,
            declared_value: float,
        ) -> str:
            if request.get("store_status") == "error":
                raise StorageError("Store unavailable")
            return super().store_draft(
                shipper_id,
                weight_kg,
                distance_km,
                declared_value,
            )
    
    api = QuoteAPI(
        MockQuoteStore(),
        MockScreeningService(),
        TariffEngine(),
        MockNotificationService(),
    )
    
    return api.request_quote(
        request.get("shipper_id", ""),
        request.get("weight_kg", 0),
        request.get("distance_km", 0),
        request.get("declared_value", 0),
    )