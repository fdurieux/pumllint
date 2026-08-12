"""CargoQuote — Instant Freight Quotation System."""


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id):
        """Return risk index. Raises screeningUnavailableError on failure."""
        pass


class TariffEngine:
    """Computes freight price from weight and distance."""

    def price(self, weight_kg, distance_km):
        """Compute price amount for a validated request."""
        pass


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        """Store draft quote; return quote_id."""
        pass

    def update_quote(self, quote_id, status, price_amount=None):
        """Update quote status and optionally price; return updated quote."""
        pass


class NotificationService:
    """External messaging provider."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        """Deliver quote document. Fire-and-forget."""
        pass

    def send_refusal_notice(self, shipper_id, quote_id):
        """Deliver refusal notice. Fire-and-forget."""
        pass


class QuoteAPI:
    """Quote request orchestrator."""

    WEIGHT_MIN_KG = 100
    WEIGHT_MAX_KG = 10000
    DISTANCE_MIN_KM = 10
    DISTANCE_MAX_KM = 1000
    DECLARED_VALUE_MIN = 0
    DECLARED_VALUE_MAX = 1000000

    ACCEPT_MAX = 30
    REVIEW_MIN = 31
    REVIEW_MAX = 70
    REFUSE_MIN = 71

    def __init__(self, quote_store, screening_service, tariff_engine,
                 notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def request_quote(self, shipper_id, weight_kg, distance_km,
                      declared_value):
        """Process a quote request through validation, screening, pricing,
        and notification."""

        # Step 1: Validate request bounds (DT-V).
        if not self._is_valid(weight_kg, distance_km, declared_value):
            return {
                "status": "rejected_invalid_request",
                "reason": "Request validation failed"
            }

        # Step 2: Store draft quote.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except Exception as e:
            return {
                "status": "store_unavailable_error",
                "reason": str(e)
            }

        # Step 3: Screen shipper.
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_available = True
        except Exception as e:
            risk_index = None
            screening_available = False

        # Step 4: Apply screening decision (DT-S).
        if screening_available:
            if risk_index <= self.ACCEPT_MAX:
                # Accept: price and notify.
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(
                    quote_id, "status_quoted", price_amount
                )
                try:
                    self.notification_service.send_quote_document(
                        shipper_id, quote_id, price_amount
                    )
                except Exception:
                    pass  # Fire-and-forget; ignore delivery failures.
                return {
                    "status": "quoted",
                    "quote_id": quote_id,
                    "price_amount": price_amount
                }
            elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
                # Review hold: no pricing, no notification.
                self.quote_store.update_quote(quote_id, "status_review_hold")
                return {
                    "status": "review_hold",
                    "quote_id": quote_id
                }
            elif risk_index >= self.REFUSE_MIN:
                # Refuse: notify but do not price.
                self.quote_store.update_quote(
                    quote_id, "status_refused_screening"
                )
                try:
                    self.notification_service.send_refusal_notice(
                        shipper_id, quote_id
                    )
                except Exception:
                    pass  # Fire-and-forget; ignore delivery failures.
                return {
                    "status": "refused_screening",
                    "quote_id": quote_id
                }
        else:
            # Screening unavailable: price and hold unscreened.
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, "status_held_unscreened", price_amount
            )
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price_amount": price_amount
            }

    def _is_valid(self, weight_kg, distance_km, declared_value):
        """Validate request bounds per DT-V."""
        if not (self.WEIGHT_MIN_KG <= weight_kg <= self.WEIGHT_MAX_KG):
            return False
        if not (self.DISTANCE_MIN_KM <= distance_km <= self.DISTANCE_MAX_KM):
            return False
        if not (self.DECLARED_VALUE_MIN <= declared_value <=
                self.DECLARED_VALUE_MAX):
            return False
        return True


class _MockScreeningService(ScreeningService):
    """Mock screening service for testing."""

    def __init__(self, result=None):
        self.result = result

    def screen(self, shipper_id):
        if self.result == "error":
            raise Exception("Screening service unavailable")
        return self.result if self.result is not None else 20


class _MockTariffEngine(TariffEngine):
    """Mock tariff engine for testing."""

    def __init__(self, result=None):
        self.result = result

    def price(self, weight_kg, distance_km):
        if self.result == "error":
            raise Exception("Pricing service unavailable")
        return self.result if self.result is not None else 1500


class _MockQuoteStore(QuoteStore):
    """Mock quote store for testing."""

    def __init__(self):
        self.quotes = {}
        self.draft_counter = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if shipper_id == "store_error":
            raise Exception("Storage unavailable")
        self.draft_counter += 1
        quote_id = f"quote_{self.draft_counter}"
        self.quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft"
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        if quote_id in self.quotes:
            self.quotes[quote_id]["status"] = status
            if price_amount is not None:
                self.quotes[quote_id]["price_amount"] = price_amount
        return self.quotes.get(quote_id)


class _MockNotificationService(NotificationService):
    """Mock notification service for testing."""

    def __init__(self):
        self.sent_documents = []
        self.sent_refusals = []

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        self.sent_documents.append({
            "shipper_id": shipper_id,
            "quote_id": quote_id,
            "price_amount": price_amount
        })

    def send_refusal_notice(self, shipper_id, quote_id):
        self.sent_refusals.append({
            "shipper_id": shipper_id,
            "quote_id": quote_id
        })


def handle(request: dict) -> dict:
    """End-to-end quote request handler."""
    shipper_id = request.get("shipper_id", "shipper_001")
    weight_kg = request.get("weight_kg", 500)
    distance_km = request.get("distance_km", 200)
    declared_value = request.get("declared_value", 50000)

    screening_result = request.get("screening_service_result")
    pricing_result = request.get("tariff_engine_result")

    quote_store = _MockQuoteStore()
    screening_service = _MockScreeningService(screening_result)
    tariff_engine = _MockTariffEngine(pricing_result)
    notification_service = _MockNotificationService()

    api = QuoteAPI(
        quote_store,
        screening_service,
        tariff_engine,
        notification_service
    )

    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)