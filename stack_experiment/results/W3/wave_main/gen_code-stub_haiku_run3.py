"""CargoQuote — Instant Freight Quotation System"""

# Decision table DT-V: Request validation bounds
WEIGHT_MIN_KG = 100
WEIGHT_MAX_KG = 30000
DISTANCE_MIN_KM = 10
DISTANCE_MAX_KM = 3000
DECLARED_VALUE_MIN = 0
DECLARED_VALUE_MAX = 1000000

# Decision table DT-S: Screening decision thresholds
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

# Quote statuses
STATUS_DRAFT = "draft"
STATUS_QUOTED = "quoted"
STATUS_REVIEW_HOLD = "review_hold"
STATUS_REFUSED_SCREENING = "refused_screening"
STATUS_HELD_UNSCREENED = "held_unscreened"


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id):
        """Return riskIndex (0-100). Raises screeningUnavailableError on failure."""
        pass


class TariffEngine:
    """Computes freight price from weight and distance."""

    def price(self, weight_kg, distance_km):
        """Return priceAmount as a single value."""
        pass


class NotificationService:
    """External messaging provider."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        """Fire-and-forget delivery of quote document."""
        pass

    def send_refusal_notice(self, shipper_id, quote_id):
        """Fire-and-forget delivery of refusal notice."""
        pass


class QuoteStore:
    """PostgreSQL quote store."""

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        """Store draft quote; return quoteId. Raises storeUnavailableError on failure."""
        pass

    def update_quote(self, quote_id, status, price_amount=None):
        """Update quote status and optional price; return updatedQuote."""
        pass


class QuoteAPI:
    """Main quotation orchestrator."""

    def __init__(self, screening_service, tariff_engine, notification_service, quote_store):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service
        self.quote_store = quote_store

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        """Orchestrate the quotation flow."""
        
        # Step 1: Validate request
        if not self._is_valid_request(weight_kg, distance_km, declared_value):
            return {
                "status": "rejected_invalid_request",
                "reason": "Request validation failed"
            }
        
        # Step 2: Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except Exception:
            return {
                "status": "store_unavailable_error",
                "reason": "Failed to store quote draft"
            }
        
        # Step 3: Screen shipper
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception:
            # Screening unavailable: price the quote and hold unscreened
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, STATUS_HELD_UNSCREENED, price_amount
                )
                return {
                    "status": "held_unscreened_response",
                    "quote_id": quote_id,
                    "price_amount": price_amount,
                    "note": "Screening service unavailable"
                }
            except Exception:
                return {
                    "status": "error",
                    "reason": "Pricing or storage failed during unscreened hold"
                }
        
        # Step 4: Apply screening decision
        if risk_index <= ACCEPT_MAX:
            # Accept: price and issue quote
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, STATUS_QUOTED, price_amount
                )
                # Fire-and-forget notification
                try:
                    self.notification_service.send_quote_document(
                        shipper_id, quote_id, price_amount
                    )
                except Exception:
                    pass  # Notification failure does not change response
                return {
                    "status": "quoted_response",
                    "quote_id": quote_id,
                    "price_amount": price_amount,
                    "risk_index": risk_index
                }
            except Exception:
                return {
                    "status": "error",
                    "reason": "Pricing or storage failed"
                }
        
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # Review: hold for manual review
            try:
                self.quote_store.update_quote(quote_id, STATUS_REVIEW_HOLD)
                return {
                    "status": "review_hold_response",
                    "quote_id": quote_id,
                    "risk_index": risk_index
                }
            except Exception:
                return {
                    "status": "error",
                    "reason": "Storage failed during review hold"
                }
        
        elif risk_index >= REFUSE_MIN:
            # Refuse: reject and notify
            try:
                self.quote_store.update_quote(quote_id, STATUS_REFUSED_SCREENING)
                # Fire-and-forget notification
                try:
                    self.notification_service.send_refusal_notice(shipper_id, quote_id)
                except Exception:
                    pass  # Notification failure does not change response
                return {
                    "status": "refused_screening_response",
                    "quote_id": quote_id,
                    "risk_index": risk_index
                }
            except Exception:
                return {
                    "status": "error",
                    "reason": "Storage failed during refusal"
                }
        
        return {
            "status": "error",
            "reason": "Unexpected screening decision state"
        }
    
    def _is_valid_request(self, weight_kg, distance_km, declared_value):
        """Validate request bounds per DT-V."""
        if not (WEIGHT_MIN_KG <= weight_kg <= WEIGHT_MAX_KG):
            return False
        if not (DISTANCE_MIN_KM <= distance_km <= DISTANCE_MAX_KM):
            return False
        if not (DECLARED_VALUE_MIN <= declared_value <= DECLARED_VALUE_MAX):
            return False
        return True


def handle(request: dict) -> dict:
    """End-to-end quotation flow handler."""
    
    # Extract request parameters
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    # Create service implementations based on request flags/results
    screening_service = _create_screening_service(request)
    tariff_engine = _create_tariff_engine(request)
    notification_service = _create_notification_service(request)
    quote_store = _create_quote_store(request)
    
    # Create API and process request
    api = QuoteAPI(screening_service, tariff_engine, notification_service, quote_store)
    result = api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    
    return result


def _create_screening_service(request: dict) -> ScreeningService:
    """Factory for screening service with injected test behavior."""
    
    class TestScreeningService(ScreeningService):
        def screen(self, shipper_id):
            if request.get("screening_status") == "error":
                raise Exception("Screening service unavailable")
            risk_index = request.get("screening_result", 50)
            return risk_index
    
    return TestScreeningService()


def _create_tariff_engine(request: dict) -> TariffEngine:
    """Factory for tariff engine with injected test behavior."""
    
    class TestTariffEngine(TariffEngine):
        def price(self, weight_kg, distance_km):
            if request.get("pricing_status") == "error":
                raise Exception("Pricing service failed")
            # Simple pricing: 10 per 100kg + 5 per 100km
            base_price = (weight_kg / 100) * 10 + (distance_km / 100) * 5
            return request.get("pricing_result", base_price)
    
    return TestTariffEngine()


def _create_notification_service(request: dict) -> NotificationService:
    """Factory for notification service with injected test behavior."""
    
    class TestNotificationService(NotificationService):
        def send_quote_document(self, shipper_id, quote_id, price_amount):
            if request.get("notification_status") == "error":
                raise Exception("Notification service failed")
        
        def send_refusal_notice(self, shipper_id, quote_id):
            if request.get("notification_status") == "error":
                raise Exception("Notification service failed")
    
    return TestNotificationService()


def _create_quote_store(request: dict) -> QuoteStore:
    """Factory for quote store with injected test behavior."""
    
    class TestQuoteStore(QuoteStore):
        def __init__(self):
            self.quotes = {}
            self.next_id = 1000
        
        def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
            if request.get("storage_status") == "error":
                raise Exception("Quote store unavailable")
            quote_id = f"Q{self.next_id}"
            self.next_id += 1
            self.quotes[quote_id] = {
                "shipper_id": shipper_id,
                "weight_kg": weight_kg,
                "distance_km": distance_km,
                "declared_value": declared_value,
                "status": STATUS_DRAFT,
                "price_amount": None
            }
            return quote_id
        
        def update_quote(self, quote_id, status, price_amount=None):
            if quote_id not in self.quotes:
                raise Exception(f"Quote {quote_id} not found")
            self.quotes[quote_id]["status"] = status
            if price_amount is not None:
                self.quotes[quote_id]["price_amount"] = price_amount
            return self.quotes[quote_id]
    
    return TestQuoteStore()