import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class ValidationError(Exception):
    pass


class StorageError(Exception):
    pass


class ScreeningError(Exception):
    pass


class PricingError(Exception):
    pass


class NotificationError(Exception):
    pass


class RiskLevel(Enum):
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


class QuoteStore:
    def __init__(self):
        self.quotes: Dict[str, Quote] = {}
        self.next_id = 1000

    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        if not self._is_available():
            raise StorageError("storeUnavailableError")
        
        quote_id = f"Q{self.next_id}"
        self.next_id += 1
        
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status="draft"
        )
        self.quotes[quote_id] = quote
        return quote_id

    def update_quote(self, quote_id: str, status: str, price_amount: Optional[float] = None) -> Quote:
        if quote_id not in self.quotes:
            raise StorageError("quoteNotFound")
        
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        
        return quote

    def _is_available(self) -> bool:
        return True


class ScreeningService:
    def __init__(self):
        self.available = True

    def screen(self, shipper_id: str) -> float:
        if not self.available:
            raise ScreeningError("screeningUnavailableError")
        
        return 25.0

    def set_available(self, available: bool):
        self.available = available


class TariffEngine:
    def __init__(self):
        self.base_rate_per_kg_km = 0.5
        self.min_charge = 50.0

    def price(self, weight_kg: float, distance_km: float) -> float:
        calculated_price = weight_kg * distance_km * self.base_rate_per_kg_km
        return max(calculated_price, self.min_charge)


class NotificationService:
    def __init__(self):
        self.available = True

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        if not self.available:
            raise NotificationError("notificationUnavailableError")
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if not self.available:
            raise NotificationError("notificationUnavailableError")
        return "sent"

    def set_available(self, available: bool):
        self.available = available


class QuoteAPI:
    ACCEPT_MAX = 30
    REVIEW_MIN = 31
    REVIEW_MAX = 70
    REFUSE_MIN = 71

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

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float
    ) -> Dict[str, Any]:
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {
                "status": "rejectedInvalidRequest",
                "reason": "Request validation failed"
            }

        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageError as e:
            return {
                "status": "storeUnavailableError",
                "reason": str(e)
            }

        risk_index = self._get_risk_index(shipper_id)

        if risk_index is None:
            return self._handle_screening_unavailable(quote_id, weight_kg, distance_km)

        return self._apply_screening_decision(
            risk_index, quote_id, shipper_id, weight_kg, distance_km
        )

    def _validate_request(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float
    ) -> bool:
        if not shipper_id or weight_kg <= 0 or distance_km <= 0 or declared_value <= 0:
            return False
        if weight_kg > 30000 or distance_km > 5000:
            return False
        return True

    def _get_risk_index(self, shipper_id: str) -> Optional[float]:
        try:
            return self.screening_service.screen(shipper_id)
        except ScreeningError:
            return None

    def _handle_screening_unavailable(
        self, quote_id: str, weight_kg: float, distance_km: float
    ) -> Dict[str, Any]:
        price_amount = self.tariff_engine.price(weight_kg, distance_km)
        self.quote_store.update_quote(quote_id, "statusHeldUnscreened", price_amount)
        return {
            "status": "heldUnscreenedResponse",
            "quote_id": quote_id,
            "price": price_amount,
            "reason": "Screening unavailable; quote held pending review"
        }

    def _apply_screening_decision(
        self,
        risk_index: float,
        quote_id: str,
        shipper_id: str,
        weight_kg: float,
        distance_km: float
    ) -> Dict[str, Any]:
        if risk_index <= self.ACCEPT_MAX:
            return self._handle_accept(quote_id, shipper_id, weight_kg, distance_km)
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            return self._handle_review(quote_id)
        elif risk_index >= self.REFUSE_MIN:
            return self._handle_refuse(quote_id, shipper_id)
        else:
            return {
                "status": "error",
                "reason": "Invalid risk index"
            }

    def _handle_accept(
        self, quote_id: str, shipper_id: str, weight_kg: float, distance_km: float
    ) -> Dict[str, Any]:
        price_amount = self.tariff_engine.price(weight_kg, distance_km)
        self.quote_store.update_quote(quote_id, "statusQuoted", price_amount)
        
        try:
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
        except NotificationError:
            pass

        return {
            "status": "quotedResponse",
            "quote_id": quote_id,
            "price": price_amount
        }

    def _handle_review(self, quote_id: str) -> Dict[str, Any]:
        self.quote_store.update_quote(quote_id, "statusReviewHold")
        return {
            "status": "reviewHoldResponse",
            "quote_id": quote_id,
            "reason": "Quote held for manual compliance review"
        }

    def _handle_refuse(self, quote_id: str, shipper_id: str) -> Dict[str, Any]:
        self.quote_store.update_quote(quote_id, "statusRefusedScreening")
        
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except NotificationError:
            pass

        return {
            "status": "refusedScreeningResponse",
            "quote_id": quote_id,
            "reason": "Quote refused on compliance screening"
        }


def handle(request: dict) -> dict:
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    
    quote_api = QuoteAPI(
        quote_store,
        screening_service,
        tariff_engine,
        notification_service
    )

    shipper_id = request.get("shipper_id", "SHIPPER001")
    weight_kg = request.get("weight_kg", 1000.0)
    distance_km = request.get("distance_km", 500.0)
    declared_value = request.get("declared_value", 50000.0)

    if request.get("quote_store_exists") is False:
        return {"status": "error: quote_store_unavailable"}
    
    if request.get("screening_service_result") == "error":
        screening_service.set_available(False)
    
    if request.get("notification_service_result") == "error":
        notification_service.set_available(False)

    if request.get("screening_service_result") == "unavailable":
        screening_service.set_available(False)

    if "screening_result" in request:
        risk_result = request.get("screening_result")
        if risk_result == "approved":
            risk_index = 20.0
        elif risk_result == "review":
            risk_index = 50.0
        elif risk_result == "refused":
            risk_index = 85.0
        else:
            try:
                risk_index = float(risk_result)
            except (ValueError, TypeError):
                risk_index = 25.0

        original_screen = screening_service.screen

        def mock_screen(sid: str) -> float:
            return risk_index

        screening_service.screen = mock_screen

    try:
        result = quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
        return result
    except Exception as e:
        return {
            "status": "error: unexpected_exception",
            "reason": str(e)
        }