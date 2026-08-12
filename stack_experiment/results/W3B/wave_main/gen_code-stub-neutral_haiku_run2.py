"""CargoQuote — Instant Freight Quotation System."""


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id):
        """Return riskIndex. Raises ScreeningUnavailableError if service unavailable."""
        return 0


class TariffEngine:
    """Computes freight price from weight and distance."""
    
    def price(self, weight_kg, distance_km):
        """Compute priceAmount for a validated request."""
        return weight_kg * distance_km * 0.5


class QuoteStore:
    """Stores quote requests and their lifecycle status."""
    
    def __init__(self):
        self._quotes = {}
        self._next_id = 1
    
    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        """Store the draft; return quoteId. Raises StoreUnavailableError on failure."""
        quote_id = f"Q{self._next_id}"
        self._next_id += 1
        self._quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price_amount": None
        }
        return quote_id
    
    def update_quote(self, quote_id, status, price_amount=None):
        """Update quote status and optionally price. Returns updatedQuote."""
        if quote_id not in self._quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self._quotes[quote_id]["status"] = status
        if price_amount is not None:
            self._quotes[quote_id]["price_amount"] = price_amount
        return self._quotes[quote_id]


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def send_quote_document(self, shipper_id, quote_id, price_amount):
        """Deliver the quote document. Fire-and-forget."""
        return "sent"
    
    def send_refusal_notice(self, shipper_id, quote_id):
        """Deliver the refusal notice. Fire-and-forget."""
        return "sent"


class QuoteAPI:
    """Orchestrates quote requests through validation, screening, pricing, and notification."""
    
    ACCEPT_MAX = 30
    REVIEW_MIN = 31
    REVIEW_MAX = 70
    REFUSE_MIN = 71
    
    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service
    
    def _validate_request(self, shipper_id, weight_kg, distance_km, declared_value):
        """Validate request bounds per DT-V."""
        if not shipper_id or len(str(shipper_id)) == 0:
            return False
        if weight_kg <= 0 or weight_kg > 100000:
            return False
        if distance_km <= 0 or distance_km > 10000:
            return False
        if declared_value < 0 or declared_value > 1000000:
            return False
        return True
    
    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        """
        Main quotation flow:
        1. Validate request
        2. Store draft
        3. Screen shipper
        4. Apply screening decision (accept/review/refuse/unavailable)
        5. Price and notify as appropriate
        """
        
        # Step 1: Validate
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {
                "status": "rejected",
                "reason": "invalidRequest"
            }
        
        # Step 2: Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except Exception as e:
            return {
                "status": "error",
                "reason": "storeUnavailable",
                "details": str(e)
            }
        
        # Step 3: Screen shipper
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception:
            # Screening unavailable: price and hold unscreened
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, "held_unscreened", price_amount
                )
                return {
                    "status": "heldUnscreened",
                    "quote_id": quote_id,
                    "price_amount": price_amount
                }
            except Exception as e:
                return {
                    "status": "error",
                    "reason": "pricingError",
                    "details": str(e)
                }
        
        # Step 4 & 5: Apply screening decision per DT-S
        if risk_index <= self.ACCEPT_MAX:
            # Accept: price, update, notify, respond
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, "quoted", price_amount
                )
                # Fire-and-forget notification
                try:
                    self.notification_service.send_quote_document(
                        shipper_id, quote_id, price_amount
                    )
                except Exception:
                    pass
                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price_amount": price_amount
                }
            except Exception as e:
                return {
                    "status": "error",
                    "reason": "pricingError",
                    "details": str(e)
                }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review: hold for manual review, no pricing, no notification
            try:
                self.quote_store.update_quote(quote_id, "review_hold")
                return {
                    "status": "reviewHold",
                    "quote_id": quote_id
                }
            except Exception as e:
                return {
                    "status": "error",
                    "reason": "storeError",
                    "details": str(e)
                }
        
        elif risk_index >= self.REFUSE_MIN:
            # Refuse: update, notify, respond
            try:
                self.quote_store.update_quote(quote_id, "refused_screening")
                # Fire-and-forget notification
                try:
                    self.notification_service.send_refusal_notice(
                        shipper_id, quote_id
                    )
                except Exception:
                    pass
                return {
                    "status": "refusedScreening",
                    "quote_id": quote_id
                }
            except Exception as e:
                return {
                    "status": "error",
                    "reason": "storeError",
                    "details": str(e)
                }
        
        return {
            "status": "error",
            "reason": "unknownError"
        }


def handle(request: dict) -> dict:
    """
    Run one end-to-end quotation flow.
    
    request dict keys:
      - shipper_id: identifier of the shipper
      - weight_kg: cargo weight
      - distance_km: shipping distance
      - declared_value: declared cargo value
      - screening_result: (optional) override screening result ("approved", "review", "refused", "error")
      - store_result: (optional) override store result ("stored", "error")
      - pricing_result: (optional) override pricing result (numeric price or "error")
      - notification_result: (optional) override notification result ("sent", "error")
    
    Returns a dict with "status" key and optional details.
    """
    
    # Build collaborators with injectable behavior for testing
    class TestableScreeningService(ScreeningService):
        def __init__(self, override=None):
            self.override = override
        
        def screen(self, shipper_id):
            if self.override == "error":
                raise Exception("Screening unavailable")
            elif self.override == "approved":
                return 20
            elif self.override == "review":
                return 50
            elif self.override == "refused":
                return 80
            return 0
    
    class TestableTariffEngine(TariffEngine):
        def __init__(self, override=None):
            self.override = override
        
        def price(self, weight_kg, distance_km):
            if self.override == "error":
                raise Exception("Pricing error")
            elif isinstance(self.override, (int, float)):
                return self.override
            return weight_kg * distance_km * 0.5
    
    class TestableQuoteStore(QuoteStore):
        def __init__(self, override=None):
            super().__init__()
            self.override = override
        
        def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
            if self.override == "error":
                raise Exception("Store unavailable")
            return super().store_draft(shipper_id, weight_kg, distance_km, declared_value)
    
    class TestableNotificationService(NotificationService):
        def __init__(self, override=None):
            self.override = override
        
        def send_quote_document(self, shipper_id, quote_id, price_amount):
            if self.override == "error":
                raise Exception("Notification error")
            return "sent"
        
        def send_refusal_notice(self, shipper_id, quote_id):
            if self.override == "error":
                raise Exception("Notification error")
            return "sent"
    
    # Extract test parameters
    screening_override = request.get("screening_result")
    store_override = request.get("store_result")
    pricing_override = request.get("pricing_result")
    notification_override = request.get("notification_result")
    
    # Instantiate collaborators
    quote_store = TestableQuoteStore(
        override="error" if store_override == "error" else None
    )
    screening_service = TestableScreeningService(override=screening_override)
    tariff_engine = TestableTariffEngine(override=pricing_override)
    notification_service = TestableNotificationService(override=notification_override)
    
    # Instantiate API and execute flow
    api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)
    
    result = api.request_quote(
        shipper_id=request.get("shipper_id"),
        weight_kg=request.get("weight_kg"),
        distance_km=request.get("distance_km"),
        declared_value=request.get("declared_value", 0)
    )
    
    return result