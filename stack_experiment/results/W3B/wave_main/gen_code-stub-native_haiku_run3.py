"""CargoQuote — Instant Freight Quotation System for palletized road cargo."""


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id):
        """Return riskIndex (0-100 scale). Raises screeningUnavailableError on failure."""
        # External system: returns a single value (risk index)
        return 0


class TariffEngine:
    """Tariff computation engine."""
    
    def price(self, weight_kg, distance_km):
        """Compute priceAmount for a validated request.
        Returns a single price value."""
        if weight_kg <= 0 or distance_km <= 0:
            raise ValueError("Invalid weight or distance")
        # Simple tariff: base + weight rate + distance rate
        base = 50.0
        weight_rate = 0.5  # per kg
        distance_rate = 0.1  # per km
        return base + (weight_kg * weight_rate) + (distance_km * distance_rate)


class QuoteStore:
    """PostgreSQL quote store."""
    
    def __init__(self):
        self._quotes = {}
        self._next_id = 1000
    
    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        """Store the draft; return quoteId. Raises storeUnavailableError on failure."""
        quote_id = self._next_id
        self._next_id += 1
        self._quotes[quote_id] = {
            "quoteId": quote_id,
            "shipperId": shipper_id,
            "weightKg": weight_kg,
            "distanceKm": distance_km,
            "declaredValue": declared_value,
            "status": "draft",
            "priceAmount": None
        }
        return quote_id
    
    def update_quote(self, quote_id, status, price_amount=None):
        """Update quote status and optionally price; return updatedQuote.
        Returns a single dict representing the updated quote."""
        if quote_id not in self._quotes:
            raise ValueError(f"Quote {quote_id} not found")
        
        self._quotes[quote_id]["status"] = status
        if price_amount is not None:
            self._quotes[quote_id]["priceAmount"] = price_amount
        
        return self._quotes[quote_id]


class NotificationService:
    """External messaging provider."""
    
    def send_quote_document(self, shipper_id, quote_id, price_amount):
        """Deliver the quote document. Fire-and-forget.
        Returns a single confirmation value."""
        return "sent"
    
    def send_refusal_notice(self, shipper_id, quote_id):
        """Deliver the refusal notice. Fire-and-forget.
        Returns a single confirmation value."""
        return "sent"


class QuoteAPI:
    """Quote API — orchestrates screening, pricing, and storage."""
    
    # Screening decision thresholds
    ACCEPT_MAX = 30
    REVIEW_MIN = 31
    REVIEW_MAX = 70
    REFUSE_MIN = 71
    
    # Status constants
    STATUS_QUOTED = "quoted"
    STATUS_REVIEW_HOLD = "review_hold"
    STATUS_REFUSED_SCREENING = "refused_screening"
    STATUS_HELD_UNSCREENED = "held_unscreened"
    
    def __init__(self, tariff_engine, screening_service, quote_store, notification_service):
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.quote_store = quote_store
        self.notification_service = notification_service
    
    def _validate_request(self, shipper_id, weight_kg, distance_km, declared_value):
        """Validate request per decision table DT-V.
        Returns (is_valid, error_message)."""
        if not shipper_id or shipper_id.strip() == "":
            return False, "shipper_id required"
        if weight_kg is None or weight_kg <= 0 or weight_kg > 10000:
            return False, "weight_kg must be > 0 and <= 10000"
        if distance_km is None or distance_km <= 0 or distance_km > 5000:
            return False, "distance_km must be > 0 and <= 5000"
        if declared_value is None or declared_value < 0 or declared_value > 1000000:
            return False, "declared_value must be >= 0 and <= 1000000"
        return True, None
    
    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        """Main quotation flow.
        Returns a single dict with status and details."""
        
        # Step 1: Validate request (DT-V)
        is_valid, error_msg = self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if not is_valid:
            return {
                "status": "rejected_invalid_request",
                "error": error_msg
            }
        
        # Step 2: Store draft
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception as e:
            return {
                "status": "store_unavailable_error",
                "error": str(e)
            }
        
        # Step 3: Screen the shipper
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception as e:
            # Screening unavailable: price the quote anyway, hold unscreened
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                updated = self.quote_store.update_quote(quote_id, self.STATUS_HELD_UNSCREENED, price_amount)
                return {
                    "status": "held_unscreened_response",
                    "quoteId": quote_id,
                    "priceAmount": price_amount,
                    "message": "Quote held due to screening service unavailability"
                }
            except Exception as pricing_error:
                return {
                    "status": "error",
                    "error": f"Pricing failed: {str(pricing_error)}"
                }
        
        # Step 4: Apply screening decision (DT-S)
        if risk_index <= self.ACCEPT_MAX:
            # Accept: price and issue
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                updated = self.quote_store.update_quote(quote_id, self.STATUS_QUOTED, price_amount)
                # Send notification (fire-and-forget)
                try:
                    self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
                except Exception:
                    pass  # Notification failure does not change response
                return {
                    "status": "quoted_response",
                    "quoteId": quote_id,
                    "priceAmount": price_amount
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Pricing failed: {str(e)}"
                }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review: hold for manual review
            try:
                updated = self.quote_store.update_quote(quote_id, self.STATUS_REVIEW_HOLD)
                return {
                    "status": "review_hold_response",
                    "quoteId": quote_id,
                    "message": "Quote held for compliance review"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Failed to hold for review: {str(e)}"
                }
        
        elif risk_index >= self.REFUSE_MIN:
            # Refuse: update and notify
            try:
                updated = self.quote_store.update_quote(quote_id, self.STATUS_REFUSED_SCREENING)
                # Send refusal notice (fire-and-forget)
                try:
                    self.notification_service.send_refusal_notice(shipper_id, quote_id)
                except Exception:
                    pass  # Notification failure does not change response
                return {
                    "status": "refused_screening_response",
                    "quoteId": quote_id,
                    "message": "Quote refused due to screening result"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Failed to refuse quote: {str(e)}"
                }
        
        else:
            return {
                "status": "error",
                "error": "Unexpected screening result"
            }


def handle(request: dict) -> dict:
    """End-to-end flow handler.
    
    Receives a request dict with:
    - shipper_id: str
    - weight_kg: float or int
    - distance_km: float or int
    - declared_value: float or int
    - Optional test overrides: screening_result, tariff_result, store_result, etc.
    
    Returns a dict with "status" key naming the outcome.
    """
    
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    # Create instances (in a real system, these would be injected/configured)
    tariff_engine = TariffEngine()
    screening_service = ScreeningService()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    quote_api = QuoteAPI(tariff_engine, screening_service, quote_store, notification_service)
    
    # Support test overrides via request parameters
    if "screening_result" in request:
        # Mock the screening result
        original_screen = screening_service.screen
        def mocked_screen(sid):
            result = request["screening_result"]
            if result == "error":
                raise Exception("Screening service unavailable")
            return int(result) if isinstance(result, (int, str)) else result
        screening_service.screen = mocked_screen
    
    if "tariff_result" in request:
        # Mock the tariff result
        original_price = tariff_engine.price
        def mocked_price(w, d):
            result = request["tariff_result"]
            if result == "error":
                raise Exception("Pricing failed")
            return float(result) if isinstance(result, (int, str, float)) else result
        tariff_engine.price = mocked_price
    
    if "store_result" in request:
        # Mock the store result
        original_store = quote_store.store_draft
        def mocked_store(sid, w, d, dv):
            result = request["store_result"]
            if result == "error":
                raise Exception("Storage unavailable")
            return 1000
        quote_store.store_draft = mocked_store
    
    # Execute the main flow
    result = quote_api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    return result