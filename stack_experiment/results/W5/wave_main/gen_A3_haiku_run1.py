import uuid
import json
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class ValidationError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class QuoteStatus(Enum):
    DRAFT = "draft"
    QUOTED = "quoted"
    REVIEW_HOLD = "review_hold"
    REFUSED_SCREENING = "refused_screening"
    HELD_UNSCREENED = "held_unscreened"


@dataclass
class QuoteRecord:
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
        """
        Returns a risk index (integer; higher is worse).
        In real usage, this would call an external REST API.
        """
        return 0


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Implements DT-P pricing rules:
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00
        P3: if distance_km >= 4912, multiply by 1.19 (after P2)
        P4: round to 2 decimal places
        """
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        if weight_kg > 1244:
            base += 316.00
        
        if distance_km >= 4912:
            base *= 1.19
        
        return round(base, 2)


class QuoteStore:
    """PostgreSQL-backed quote storage."""
    
    def __init__(self):
        self.quotes: dict[str, QuoteRecord] = {}
    
    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float
    ) -> str:
        """
        Stores a draft quote. Returns quote_id.
        Raises StoreUnavailableError if storage fails.
        """
        quote_id = str(uuid.uuid4())
        record = QuoteRecord(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT
        )
        self.quotes[quote_id] = record
        return quote_id
    
    def update_quote(
        self,
        quote_id: str,
        status: QuoteStatus,
        price: Optional[float] = None
    ) -> QuoteRecord:
        """
        Updates a stored quote with new status and optional price.
        Returns the updated record.
        """
        record = self.quotes[quote_id]
        record.status = status
        if price is not None:
            record.price = price
        return record


class NotificationService:
    """External messaging provider."""
    
    def send_quote_document(
        self,
        shipper_id: str,
        quote_id: str,
        price: float
    ) -> str:
        """
        Sends a quote document to the shipper.
        Fire-and-forget; returns a confirmation string.
        """
        return "sent"
    
    def send_refusal_notice(
        self,
        shipper_id: str,
        quote_id: str
    ) -> str:
        """
        Sends a refusal notice to the shipper.
        Fire-and-forget; returns a confirmation string.
        """
        return "sent"


class QuoteAPI:
    """
    Quote API orchestrator.
    Receives quote requests, validates, screens, prices, stores, and notifies.
    """
    
    # DT-S screening decision thresholds
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def __init__(
        self,
        store: QuoteStore,
        screening_service: ScreeningService,
        tariff_engine: TariffEngine,
        notification_service: NotificationService
    ):
        self.store = store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service
    
    def _validate_request(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float
    ) -> None:
        """
        Validates request per DT-V.
        Raises ValidationError if any rule is violated.
        """
        if not shipper_id or shipper_id.strip() == "":
            raise ValidationError("shipper_id must be present and non-empty")
        
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            raise ValidationError("weight_kg must be between 3 and 19400")
        
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            raise ValidationError("distance_km must be between 25 and 7150")
        
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            raise ValidationError("declared_value must be between 50 and 83000")
    
    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float
    ) -> dict:
        """
        Main quotation flow per the sequence diagram and DT-V, DT-S, DT-P.
        Returns response dict with status and optional quote_id, price, hold.
        """
        try:
            self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError:
            return {"status": "rejected: invalid_request"}
        
        try:
            quote_id = self.store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}
        
        risk_index = None
        screening_failed = False
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            screening_failed = True
        
        if screening_failed:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }
        
        if isinstance(risk_index, str):
            try:
                risk_index = int(risk_index)
            except (ValueError, TypeError):
                screening_failed = True
        
        if screening_failed:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }
        
        risk_index = int(risk_index)
        
        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, QuoteStatus.QUOTED, price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        elif risk_index >= self.REFUSE_MIN:
            self.store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }


def handle(request: dict) -> dict:
    """
    End-to-end flow handler.
    Reads request dict, instantiates services, and runs quotation.
    
    Request keys:
        - shipper_id, weight_kg, distance_km, declared_value: quote params
        - screening_result: (optional) mocked risk index for screening
        - store_unavailable: (optional) bool to trigger store error
        - screening_unavailable: (optional) bool to trigger screening error
    """
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    store = QuoteStore()
    
    screening_service = ScreeningService()
    original_screen = screening_service.screen
    
    if request.get("screening_unavailable"):
        def mock_screen(sid: str) -> int:
            raise ScreeningUnavailableError()
        screening_service.screen = mock_screen
    elif "screening_result" in request:
        result = request["screening_result"]
        def mock_screen(sid: str):
            return result
        screening_service.screen = mock_screen
    
    if request.get("store_unavailable"):
        original_store = store.store_draft
        def mock_store_draft(sid: str, w: float, d: float, dv: float) -> str:
            raise StoreUnavailableError()
        store.store_draft = mock_store_draft
    
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    
    api = QuoteAPI(store, screening_service, tariff_engine, notification_service)
    
    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)