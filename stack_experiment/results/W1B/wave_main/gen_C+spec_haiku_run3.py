import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationError(Exception):
    reason: str


@dataclass
class StorageError(Exception):
    reason: str


@dataclass
class ScreeningError(Exception):
    reason: str


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str) -> int:
        """
        Returns the shipper risk index (integer; higher is worse).
        In test mode, respects screening_service_result from request context.
        """
        return 50


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Returns price in EUR.
        Basic linear model: EUR 2 per kg + EUR 0.5 per km.
        In test mode, respects tariff_engine_result from request context.
        """
        return (weight_kg * 2.0) + (distance_km * 0.5)


class QuoteStore:
    """Persistent store for quote requests and their lifecycle."""
    
    def __init__(self):
        self.quotes = {}
        self.quote_counter = 0
    
    def store_draft(self, shipper_id: str, weight_kg: float, 
                    distance_km: float, declared_value: float) -> str:
        """
        Stores a draft quote; returns quote_id.
        In test mode, respects quote_store_result to simulate storage outcome.
        """
        self.quote_counter += 1
        quote_id = f"QT-{self.quote_counter:06d}"
        self.quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, 
                     price: Optional[float] = None) -> dict:
        """
        Updates a quote with status and optional price; returns updated record.
        In test mode, respects quote_store_result to simulate update outcome.
        """
        if quote_id not in self.quotes:
            raise StorageError("quote_not_found")
        quote = self.quotes[quote_id]
        quote["status"] = status
        if price is not None:
            quote["price"] = price
        return quote


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, 
                           price: float) -> str:
        """
        Sends a quote document to the shipper (fire-and-forget).
        Returns "sent" or silently fails (caller ignores result per spec note 4).
        In test mode, respects notification_service_result.
        """
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """
        Sends a refusal notice to the shipper (fire-and-forget).
        Returns "sent" or silently fails.
        In test mode, respects notification_service_result.
        """
        return "sent"


class QuoteAPI:
    """
    Main orchestrator: validates requests, manages the quote lifecycle,
    coordinates screening, pricing, storage, and notification.
    """
    
    def __init__(self, screening_service: ScreeningService,
                 tariff_engine: TariffEngine,
                 quote_store: QuoteStore,
                 notification_service: NotificationService):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service
    
    def request_quote(self, shipper_id: str, weight_kg: float,
                     distance_km: float, declared_value: float) -> dict:
        """
        Main entry point: validates request, stores draft, screens shipper,
        applies screening decision, prices, notifies, and returns outcome.
        
        DT-V validation bounds:
          shipper_id: non-empty string
          weight_kg: 0.1 to 30000
          distance_km: 1 to 5000
          declared_value: 1 to 1000000
        """
        
        # Step 1: Validate (DT-V)
        if not shipper_id or not isinstance(shipper_id, str):
            return {"status": "rejected: invalid_request"}
        if not (0.1 <= weight_kg <= 30000):
            return {"status": "rejected: invalid_request"}
        if not (1 <= distance_km <= 5000):
            return {"status": "rejected: invalid_request"}
        if not (1 <= declared_value <= 1000000):
            return {"status": "rejected: invalid_request"}
        
        # Step 2: Store draft (DT-S note 3: failure stops flow)
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StorageError:
            return {"status": "error: store_unavailable"}
        
        # Step 3: Screen shipper (DT-S note 5: outage does not fail)
        risk_index = None
        screening_failed = False
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningError:
            screening_failed = True
        
        # Step 4: Apply screening decision (DT-S decision table)
        # DT-S bounds: ACCEPT_MAX=40, REVIEW_MIN=41, REVIEW_MAX=70, REFUSE_MIN=71
        status_decision = None
        should_price = False
        should_notify = False
        
        if screening_failed:
            # Screening outage: price anyway, status held_unscreened (DT-S note 5)
            status_decision = "held_unscreened"
            should_price = True
            should_notify = False
        elif risk_index <= 40:
            # Accept band: price and notify (DT-S row accept)
            status_decision = "quoted"
            should_price = True
            should_notify = True
        elif 41 <= risk_index <= 70:
            # Review band: hold, no pricing, no notification (DT-S row review)
            status_decision = "review_hold"
            should_price = False
            should_notify = False
        elif risk_index >= 71:
            # Refuse band: refuse, no pricing, notify (DT-S row refuse)
            status_decision = "refused_screening"
            should_price = False
            should_notify = True
        
        # Step 5: Price (only if marked in DT-S)
        price_amount = None
        if should_price:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
        
        # Step 6: Update stored quote
        try:
            self.quote_store.update_quote(quote_id, status_decision, price_amount)
        except StorageError:
            return {"status": "error: store_unavailable"}
        
        # Step 7: Notify (only if marked in DT-S; fire-and-forget, spec note 4)
        if should_notify:
            if status_decision == "quoted":
                self.notification_service.send_quote_document(
                    shipper_id, quote_id, price_amount
                )
            elif status_decision == "refused_screening":
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
        
        # Step 8: Build response
        response = {
            "status": status_decision,
            "quote_id": quote_id,
        }
        
        if price_amount is not None:
            response["price"] = price_amount
        
        if status_decision == "held_unscreened":
            response["hold"] = True
        
        return response


def handle(request: dict) -> dict:
    """
    End-to-end entry point: processes a quote request.
    
    Input request keys:
      - shipper_id (string)
      - weight_kg (number)
      - distance_km (number)
      - declared_value (number)
      - Optional test overrides: screening_service_result, tariff_engine_result,
        quote_store_result, notification_service_result
    
    Returns a dict with "status" and optional "quote_id", "price", "hold".
    """
    
    # Instantiate services
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    
    # Wrap services with test-mode result injection
    if "screening_service_result" in request:
        original_screen = screening_service.screen
        def mock_screen(shipper_id):
            result = request["screening_service_result"]
            if result == "error":
                raise ScreeningError("service_unavailable")
            return int(result)
        screening_service.screen = mock_screen
    
    if "tariff_engine_result" in request:
        original_price = tariff_engine.price
        def mock_price(weight_kg, distance_km):
            result = request["tariff_engine_result"]
            if result == "error":
                raise Exception("tariff_unavailable")
            return float(result)
        tariff_engine.price = mock_price
    
    if "quote_store_result" in request:
        original_store = quote_store.store_draft
        original_update = quote_store.update_quote
        def mock_store(shipper_id, weight_kg, distance_km, declared_value):
            result = request["quote_store_result"]
            if result == "error":
                raise StorageError("storage_unavailable")
            return original_store(shipper_id, weight_kg, distance_km, declared_value)
        def mock_update(quote_id, status, price=None):
            result = request["quote_store_result"]
            if result == "error":
                raise StorageError("storage_unavailable")
            return original_update(quote_id, status, price)
        quote_store.store_draft = mock_store
        quote_store.update_quote = mock_update
    
    if "notification_service_result" in request:
        original_send_doc = notification_service.send_quote_document
        original_send_ref = notification_service.send_refusal_notice
        def mock_send_doc(shipper_id, quote_id, price):
            result = request["notification_service_result"]
            if result == "error":
                return "failed"
            return "sent"
        def mock_send_ref(shipper_id, quote_id):
            result = request["notification_service_result"]
            if result == "error":
                return "failed"
            return "sent"
        notification_service.send_quote_document = mock_send_doc
        notification_service.send_refusal_notice = mock_send_ref
    
    # Build API and run flow
    api = QuoteAPI(screening_service, tariff_engine, quote_store, 
                   notification_service)
    
    result = api.request_quote(
        shipper_id=request.get("shipper_id", ""),
        weight_kg=request.get("weight_kg", 0),
        distance_km=request.get("distance_km", 0),
        declared_value=request.get("declared_value", 0),
    )
    
    return result