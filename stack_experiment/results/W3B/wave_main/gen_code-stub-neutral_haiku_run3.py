"""CargoQuote — Instant Freight Quotation System."""


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id):
        """Return riskIndex (0-100 scale). Raises ScreeningUnavailableError on service failure."""
        return 0


class TariffEngine:
    """Computes freight price from weight and distance."""

    def price(self, weight_kg, distance_km):
        """Compute priceAmount for a validated request."""
        return 0.0


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        """Deliver the quote document. Fire-and-forget."""
        pass

    def send_refusal_notice(self, shipper_id, quote_id):
        """Deliver the refusal notice. Fire-and-forget."""
        pass


class QuoteStore:
    """PostgreSQL-backed quote storage."""

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        """Store the draft; return quoteId. Raises StoreUnavailableError on failure."""
        return "quote-001"

    def update_quote(self, quote_id, status, price_amount=None):
        """Update quote status and optionally price; return updatedQuote."""
        return {"quote_id": quote_id, "status": status, "price_amount": price_amount}


class QuoteAPI:
    """Main quotation orchestrator."""

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
        """Validate request bounds per decision table DT-V."""
        if not shipper_id or shipper_id.strip() == "":
            return False, "shipper_id is required"
        if weight_kg is None or weight_kg <= 0 or weight_kg > 50000:
            return False, "weight_kg must be > 0 and <= 50000"
        if distance_km is None or distance_km <= 0 or distance_km > 5000:
            return False, "distance_km must be > 0 and <= 5000"
        if declared_value is None or declared_value < 0 or declared_value > 1000000:
            return False, "declared_value must be >= 0 and <= 1000000"
        return True, None

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        """Orchestrate the quotation flow."""
        
        # Step 1: Validate request
        is_valid, error_msg = self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if not is_valid:
            return {
                "status": "rejected",
                "reason": "invalidRequest",
                "details": error_msg
            }

        # Step 2: Store draft
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception as e:
            return {
                "status": "error",
                "reason": "storeUnavailableError",
                "details": str(e)
            }

        # Step 3: Screen shipper
        screening_failed = False
        risk_index = None
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception:
            screening_failed = True

        # Step 4: Apply screening decision
        if screening_failed:
            # Screening unavailable: price, hold, no notification
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
            except Exception as e:
                return {
                    "status": "error",
                    "reason": "pricingError",
                    "details": str(e)
                }

            try:
                self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            except Exception as e:
                return {
                    "status": "error",
                    "reason": "storeUnavailableError",
                    "details": str(e)
                }

            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price_amount": price_amount,
                "reason": "screeningUnavailable"
            }

        # Screening succeeded; apply decision based on risk_index
        if risk_index <= self.ACCEPT_MAX:
            # Accept: price, quote, notify
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
            except Exception as e:
                return {
                    "status": "error",
                    "reason": "pricingError",
                    "details": str(e)
                }

            try:
                self.quote_store.update_quote(quote_id, "quoted", price_amount)
            except Exception as e:
                return {
                    "status": "error",
                    "reason": "storeUnavailableError",
                    "details": str(e)
                }

            # Fire-and-forget notification
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            except Exception:
                pass

            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price_amount": price_amount
            }

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review: hold, no pricing, no notification
            try:
                self.quote_store.update_quote(quote_id, "review_hold")
            except Exception as e:
                return {
                    "status": "error",
                    "reason": "storeUnavailableError",
                    "details": str(e)
                }

            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "reason": "screeningRiskLevel"
            }

        elif risk_index >= self.REFUSE_MIN:
            # Refuse: refuse, notify
            try:
                self.quote_store.update_quote(quote_id, "refused_screening")
            except Exception as e:
                return {
                    "status": "error",
                    "reason": "storeUnavailableError",
                    "details": str(e)
                }

            # Fire-and-forget notification
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass

            return {
                "status": "refused",
                "quote_id": quote_id,
                "reason": "screeningRiskLevel"
            }

        # Fallback (should not reach here if decision table is exhaustive)
        return {
            "status": "error",
            "reason": "unexpectedScreeningOutcome",
            "details": f"risk_index={risk_index}"
        }


def handle(request: dict) -> dict:
    """Run one end-to-end quotation flow."""
    
    # Extract request parameters with test overrides
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value", 0)

    # Instantiate collaborators with test overrides
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()

    # Apply test-controlled outcomes
    if "screening_result" in request:
        screening_result = request["screening_result"]
        if screening_result == "error":
            class MockScreening(ScreeningService):
                def screen(self, shipper_id):
                    raise Exception("Screening service unavailable")
            screening_service = MockScreening()
        else:
            # screening_result is a risk index number
            class MockScreening(ScreeningService):
                def screen(self, shipper_id):
                    return screening_result
            screening_service = MockScreening()

    if "tariff_result" in request:
        tariff_result = request["tariff_result"]
        class MockTariff(TariffEngine):
            def price(self, weight_kg, distance_km):
                return tariff_result
        tariff_engine = MockTariff()

    if "store_result" in request:
        store_result = request["store_result"]
        if store_result == "error":
            class MockStore(QuoteStore):
                def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
                    raise Exception("Quote store unavailable")
            quote_store = MockStore()
        else:
            class MockStore(QuoteStore):
                def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
                    return store_result
            quote_store = MockStore()

    # Run the quotation flow
    api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)
    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)