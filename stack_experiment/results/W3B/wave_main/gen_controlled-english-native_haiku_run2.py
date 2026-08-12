from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ScreeningDecision(Enum):
    ACCEPT = "accept"
    REVIEW = "review"
    REFUSE = "refuse"
    UNAVAILABLE = "unavailable"


@dataclass
class Quote:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: str
    price_amount: Optional[float] = None


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str, risk_index: Optional[int] = None) -> int:
        """Returns shipper risk index."""
        if risk_index is None:
            return 50
        return risk_index


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    def price(self, weight_kg: float, distance_km: float, price_amount: Optional[float] = None) -> float:
        """Returns price amount based on tariff rules."""
        if price_amount is not None:
            return price_amount
        base_rate = 0.5
        weight_factor = weight_kg * 0.01
        distance_factor = distance_km * 0.02
        return base_rate + weight_factor + distance_factor


class QuoteStore:
    """PostgreSQL 16 quote database."""
    
    def __init__(self):
        self._quotes = {}
        self._next_id = 1
    
    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
        stored: bool = True
    ) -> str:
        """Stores draft quote and returns quoteId."""
        if not stored:
            raise StorageError("store_unavailable_error")
        quote_id = f"Q{self._next_id}"
        self._next_id += 1
        self._quotes[quote_id] = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status="draft"
        )
        return quote_id
    
    def update_quote(
        self,
        quote_id: str,
        status: str,
        price_amount: Optional[float] = None,
        updated: bool = True
    ) -> Quote:
        """Updates quote status and price, returns updated quote."""
        if not updated:
            raise StorageError("store_unavailable_error")
        if quote_id not in self._quotes:
            raise StorageError(f"quote_not_found: {quote_id}")
        quote = self._quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote


class NotificationService:
    """External messaging provider."""
    
    def send_quote_document(
        self,
        shipper_id: str,
        quote_id: str,
        price_amount: float,
        sent: bool = True
    ) -> str:
        """Sends quote document asynchronously, fire-and-forget."""
        if not sent:
            return "send_failed"
        return "sent"
    
    def send_refusal_notice(
        self,
        shipper_id: str,
        quote_id: str,
        sent: bool = True
    ) -> str:
        """Sends refusal notice asynchronously, fire-and-forget."""
        if not sent:
            return "send_failed"
        return "sent"


class QuoteAPI:
    """Quote API orchestrating screening and pricing."""
    
    ACCEPT_MAX = 35
    REVIEW_MIN = 36
    REVIEW_MAX = 65
    REFUSE_MIN = 66
    
    WEIGHT_MIN = 0.1
    WEIGHT_MAX = 30000.0
    DISTANCE_MIN = 1.0
    DISTANCE_MAX = 3000.0
    DECLARED_VALUE_MIN = 0.0
    DECLARED_VALUE_MAX = 1000000.0
    
    def __init__(
        self,
        quote_store: QuoteStore,
        screening_service: ScreeningService,
        tariff_engine: TariffEngine,
        notification_service: NotificationService
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
        declared_value: float
    ) -> bool:
        """Validates request bounds (DT-V)."""
        if not shipper_id:
            return False
        if not (self.WEIGHT_MIN <= weight_kg <= self.WEIGHT_MAX):
            return False
        if not (self.DISTANCE_MIN <= distance_km <= self.DISTANCE_MAX):
            return False
        if not (self.DECLARED_VALUE_MIN <= declared_value <= self.DECLARED_VALUE_MAX):
            return False
        return True
    
    def _screening_decision(self, risk_index: int) -> ScreeningDecision:
        """Applies screening decision rules (DT-S)."""
        if risk_index <= self.ACCEPT_MAX:
            return ScreeningDecision.ACCEPT
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            return ScreeningDecision.REVIEW
        elif risk_index >= self.REFUSE_MIN:
            return ScreeningDecision.REFUSE
        return ScreeningDecision.UNAVAILABLE
    
    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
        stored: bool = True,
        screening_result: Optional[int] = None,
        screening_status: Optional[str] = None,
        price_amount: Optional[float] = None,
        updated: bool = True,
        notification_sent: bool = True
    ) -> dict:
        """
        Main quotation flow.
        
        Args:
            shipper_id: Shipper identifier
            weight_kg: Cargo weight in kilograms
            distance_km: Distance in kilometers
            declared_value: Declared cargo value
            stored: Whether quote store accepts the request
            screening_result: Override screening risk index
            screening_status: Override screening status (e.g., "unavailable")
            price_amount: Override tariff engine price
            updated: Whether quote store accepts updates
            notification_sent: Whether notification service accepts sends
        
        Returns:
            dict with "status" key and outcome details
        """
        
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected_invalid_request"}
        
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, stored=stored
            )
        except StorageError as e:
            return {"status": "store_unavailable_error", "error": str(e)}
        
        if screening_status == "unavailable":
            risk_index = None
        else:
            risk_index = self.screening_service.screen(shipper_id, risk_index=screening_result)
        
        if risk_index is None:
            price = self.tariff_engine.price(weight_kg, distance_km, price_amount=price_amount)
            try:
                self.quote_store.update_quote(
                    quote_id, "held_unscreened", price_amount=price, updated=updated
                )
            except StorageError as e:
                return {"status": "error", "error": str(e)}
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price
            }
        
        decision = self._screening_decision(risk_index)
        
        if decision == ScreeningDecision.ACCEPT:
            price = self.tariff_engine.price(weight_kg, distance_km, price_amount=price_amount)
            try:
                self.quote_store.update_quote(
                    quote_id, "quoted", price_amount=price, updated=updated
                )
            except StorageError as e:
                return {"status": "error", "error": str(e)}
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price, sent=notification_sent
            )
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        
        elif decision == ScreeningDecision.REVIEW:
            try:
                self.quote_store.update_quote(
                    quote_id, "review_hold", updated=updated
                )
            except StorageError as e:
                return {"status": "error", "error": str(e)}
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        
        elif decision == ScreeningDecision.REFUSE:
            try:
                self.quote_store.update_quote(
                    quote_id, "refused_screening", updated=updated
                )
            except StorageError as e:
                return {"status": "error", "error": str(e)}
            self.notification_service.send_refusal_notice(
                shipper_id, quote_id, sent=notification_sent
            )
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }
        
        return {"status": "error", "error": "unknown_screening_outcome"}


_quote_store = QuoteStore()
_screening_service = ScreeningService()
_tariff_engine = TariffEngine()
_notification_service = NotificationService()
_quote_api = QuoteAPI(
    _quote_store,
    _screening_service,
    _tariff_engine,
    _notification_service
)


def handle(request: dict) -> dict:
    """
    Runs one end-to-end quotation flow.
    
    Expected request keys:
        - shipper_id: str
        - weight_kg: float
        - distance_km: float
        - declared_value: float
        - quote_store_exists: bool (default True)
        - screening_result: int (optional, overrides screening)
        - screening_status: str (optional, e.g. "unavailable")
        - tariff_result: float (optional, overrides pricing)
        - notification_result: str (optional, overrides notification)
    
    Returns:
        dict with "status" key describing outcome
    """
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)
    
    stored = request.get("quote_store_exists", True)
    screening_result = request.get("screening_result")
    screening_status = request.get("screening_status")
    price_amount = request.get("tariff_result")
    notification_sent = request.get("notification_result", "sent") == "sent"
    updated = request.get("quote_store_updated", True)
    
    return _quote_api.request_quote(
        shipper_id=shipper_id,
        weight_kg=weight_kg,
        distance_km=distance_km,
        declared_value=declared_value,
        stored=stored,
        screening_result=screening_result,
        screening_status=screening_status,
        price_amount=price_amount,
        updated=updated,
        notification_sent=notification_sent
    )