from dataclasses import dataclass
from typing import Optional
from enum import Enum


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
    price_amount: Optional[float] = None


class ValidationError(Exception):
    pass


class StorageUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class ScreeningService:
    def screen(self, shipper_id: str) -> float:
        return 0.5


class TariffEngine:
    BASE_RATE_PER_KG_KM = 0.05
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        return weight_kg * distance_km * self.BASE_RATE_PER_KG_KM


class QuoteStore:
    def __init__(self):
        self.quotes = {}
        self.next_id = 1
    
    def store_draft(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> str:
        quote_id = f"quote_{self.next_id}"
        self.next_id += 1
        quote = Quote(
            quote_id=quote_id,
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status=QuoteStatus.DRAFT,
        )
        self.quotes[quote_id] = quote
        return quote_id
    
    def update_quote(self, quote_id: str, status: QuoteStatus, price_amount: Optional[float] = None) -> Quote:
        quote = self.quotes[quote_id]
        quote.status = status
        if price_amount is not None:
            quote.price_amount = price_amount
        return quote


class NotificationService:
    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


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
        notification_service: NotificationService,
    ):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service
    
    def validate_request(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> bool:
        if not shipper_id or shipper_id.strip() == "":
            return False
        if weight_kg <= 0:
            return False
        if distance_km <= 0:
            return False
        if declared_value < 0:
            return False
        return True
    
    def request_quote(
        self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float
    ) -> dict:
        if not self.validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected_invalid_request"}
        
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StorageUnavailableError:
            return {"status": "store_unavailable_error"}
        
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            risk_index = None
        
        if risk_index is None:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.HELD_UNSCREENED, price_amount)
            return {"status": "held_unscreened", "quote_id": quote_id, "price": price_amount}
        
        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, QuoteStatus.QUOTED, price_amount)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            except Exception:
                pass
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
        
        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, QuoteStatus.REVIEW_HOLD)
            return {"status": "review_hold", "quote_id": quote_id}
        
        if risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, QuoteStatus.REFUSED_SCREENING)
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass
            return {"status": "refused_screening", "quote_id": quote_id}
        
        return {"status": "error: unknown_screening_outcome"}


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)
    
    screening_result = request.get("screening_service_result")
    store_available = request.get("quote_store_exists", True)
    screening_available = request.get("screening_service_found", True)
    
    quote_store = QuoteStore()
    if not store_available:
        quote_store.store_draft = lambda *args, **kwargs: (_ for _ in ()).throw(StorageUnavailableError())
    
    screening_service = ScreeningService()
    if screening_result is not None:
        screening_service.screen = lambda *args, **kwargs: float(screening_result)
    if not screening_available:
        screening_service.screen = lambda *args, **kwargs: (_ for _ in ()).throw(ScreeningUnavailableError())
    
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    
    quote_api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)
    
    result = quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    
    return result