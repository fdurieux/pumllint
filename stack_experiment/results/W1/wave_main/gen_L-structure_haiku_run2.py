import json
from typing import Optional
from abc import ABC, abstractmethod


class ScreeningService:
    """External screening provider."""
    def __init__(self, risk_index: Optional[int] = None, available: bool = True):
        self.risk_index = risk_index
        self.available = available
    
    def screen(self, shipper_id: str) -> int:
        if not self.available:
            raise ScreeningUnavailableError()
        return self.risk_index


class ScreeningUnavailableError(Exception):
    pass


class TariffEngine:
    """Pricing computation engine."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        # DT-P: pricing rules
        # P1: base calculation
        base = 0.87 * weight_kg + 1.13 * distance_km
        
        # P2: heavy surcharge
        if weight_kg > 1244:
            base += 316.00
        
        # P3: long-haul multiplier (applied after P2)
        if distance_km >= 4912:
            base *= 1.19
        
        # P4: round to 2 decimal places
        return round(base, 2)


class QuoteStore:
    """Quote storage backend."""
    def __init__(self, available: bool = True):
        self.available = available
        self.quotes = {}
        self.counter = 0
    
    def store_draft(self, shipper_id: str, weight_kg: float, 
                   distance_km: float, declared_value: float) -> str:
        if not self.available:
            raise StoreUnavailableError()
        self.counter += 1
        quote_id = f"QT-{self.counter:06d}"
        self.quotes[quote_id] = {
            "quote_id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        return self.quotes[quote_id]


class StoreUnavailableError(Exception):
    pass


class NotificationService:
    """External notification provider."""
    def __init__(self, available: bool = True):
        self.available = available
        self.notifications = []
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        if not self.available:
            raise NotificationUnavailableError()
        self.notifications.append({
            "type": "quote_document",
            "shipper_id": shipper_id,
            "quote_id": quote_id,
            "price": price
        })
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if not self.available:
            raise NotificationUnavailableError()
        self.notifications.append({
            "type": "refusal_notice",
            "shipper_id": shipper_id,
            "quote_id": quote_id
        })
        return "sent"


class NotificationUnavailableError(Exception):
    pass


class QuoteAPI:
    """Main quotation API orchestrator."""
    
    # Decision table constants (DT-S)
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
    
    def validate_request(self, shipper_id: str, weight_kg: float,
                        distance_km: float, declared_value: float) -> bool:
        """DT-V: request validation"""
        # V1: shipper_id present and non-empty
        if not shipper_id or not isinstance(shipper_id, str):
            return False
        
        # V2: weight_kg in range [3, 19400]
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False
        
        # V3: distance_km in range [25, 7150]
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False
        
        # V4: declared_value in range [50, 83000]
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False
        
        return True
    
    def request_quote(self, shipper_id: str, weight_kg: float,
                     distance_km: float, declared_value: float) -> dict:
        """Main quotation flow"""
        
        # Step 1: Validate request
        if not self.validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}
        
        # Step 2: Store draft
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}
        
        # Step 3: Screen the shipper
        risk_index = None
        screening_failed = False
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            screening_failed = True
        
        # Step 4 & 5: Apply screening decision
        if screening_failed:
            # Screening outage: price anyway, store as held_unscreened, do not notify
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True
            }
        
        # Screening succeeded: apply risk banding (DT-S)
        if risk_index <= self.ACCEPT_MAX:
            # Accept: price and notify
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except NotificationUnavailableError:
                # Fire-and-forget: notification failure does not change response
                pass
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price
            }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review: hold without pricing or notification
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id
            }
        
        elif risk_index >= self.REFUSE_MIN:
            # Refuse: do not price, but notify
            self.quote_store.update_quote(quote_id, "refused_screening")
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except NotificationUnavailableError:
                # Fire-and-forget: notification failure does not change response
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id
            }


def handle(request: dict) -> dict:
    """
    End-to-end quotation flow handler.
    
    request keys:
    - shipper_id, weight_kg, distance_km, declared_value: quote parameters
    - screening_result: risk index (int) or "error" for unavailability
    - store_result: "stored" or "error"
    - notification_result: "sent" or "error"
    """
    
    # Extract parameters
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    # Determine screening service behavior
    screening_result = request.get("screening_result", "ok")
    if screening_result == "error":
        screening_service = ScreeningService(available=False)
    else:
        screening_service = ScreeningService(risk_index=screening_result, available=True)
    
    # Determine store availability
    store_available = request.get("store_result", "stored") != "error"
    quote_store = QuoteStore(available=store_available)
    
    # Determine notification service availability
    notification_available = request.get("notification_result", "sent") != "error"
    notification_service = NotificationService(available=notification_available)
    
    # Create engines
    tariff_engine = TariffEngine()
    
    # Create API
    api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)
    
    # Execute request
    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)