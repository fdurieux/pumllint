"""CargoQuote — Instant Freight Quotation System"""


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id):
        """Return riskIndex (0-100). Raises exception on unavailability."""
        return 25


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules."""

    def price(self, weight_kg, distance_km):
        """Return priceAmount (float in currency units)."""
        base_rate = 0.50
        return round(weight_kg * distance_km * base_rate, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self.quotes = {}
        self.next_quote_id = 1

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        """Store draft quote; return quoteId. Raises exception on unavailability."""
        quote_id = f"QUOTE-{self.next_quote_id}"
        self.next_quote_id += 1
        self.quotes[quote_id] = {
            "quote_id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price_amount": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        """Update quote status and optionally price; return updatedQuote dict."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote["status"] = status
        if price_amount is not None:
            quote["price_amount"] = price_amount
        return quote


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        """Fire-and-forget delivery of quote document."""
        pass

    def send_refusal_notice(self, shipper_id, quote_id):
        """Fire-and-forget delivery of refusal notice."""
        pass


class QuoteAPI:
    """Main service: receives quote requests, orchestrates screening and pricing."""

    ACCEPT_MAX = 30
    REVIEW_MIN = 31
    REVIEW_MAX = 70
    REFUSE_MIN = 71

    WEIGHT_MIN = 100
    WEIGHT_MAX = 20000
    DISTANCE_MIN = 10
    DISTANCE_MAX = 2000
    VALUE_MIN = 100
    VALUE_MAX = 500000

    def __init__(
        self,
        quote_store,
        screening_service,
        tariff_engine,
        notification_service,
    ):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def request_quote(
        self, shipper_id, weight_kg, distance_km, declared_value
    ):
        """
        Main quotation flow.
        Returns a dict with 'status' key and additional context.
        """

        if not self._validate_request(
            shipper_id, weight_kg, distance_km, declared_value
        ):
            return {"status": "rejectedInvalidRequest"}

        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except Exception:
            return {"status": "storeUnavailableError"}

        try:
            risk_index = self.screening_service.screen(shipper_id)
        except Exception:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, "held_unscreened", price_amount
            )
            return {"status": "heldUnscreenedResponse", "quote_id": quote_id}

        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, "quoted", price_amount
            )
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount
            )
            return {
                "status": "quotedResponse",
                "quote_id": quote_id,
                "price_amount": price_amount,
            }

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "reviewHoldResponse", "quote_id": quote_id}

        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(
                quote_id, "refused_screening"
            )
            self.notification_service.send_refusal_notice(
                shipper_id, quote_id
            )
            return {"status": "refusedScreeningResponse", "quote_id": quote_id}

    def _validate_request(
        self, shipper_id, weight_kg, distance_km, declared_value
    ):
        """Decision table DT-V: validate request bounds."""
        if not shipper_id:
            return False
        if not (self.WEIGHT_MIN <= weight_kg <= self.WEIGHT_MAX):
            return False
        if not (self.DISTANCE_MIN <= distance_km <= self.DISTANCE_MAX):
            return False
        if not (self.VALUE_MIN <= declared_value <= self.VALUE_MAX):
            return False
        return True


def handle(request: dict) -> dict:
    """
    End-to-end handler: accepts a request dict with scenario input and returns outcome.

    Request keys:
    - shipper_id: string
    - weight_kg: number
    - distance_km: number
    - declared_value: number
    - screening_result: string (optional, for mock: "approved", "review", "declined", "error")
    - screening_risk_index: number (optional, for mock)
    - store_result: string (optional, for mock: "stored" or "error")
    - pricing_result: number (optional, for mock price override)

    Returns dict with 'status' key and optional additional fields.
    """

    class MockScreeningService(ScreeningService):
        def __init__(self, mock_result=None, mock_risk_index=None):
            self.mock_result = mock_result
            self.mock_risk_index = mock_risk_index

        def screen(self, shipper_id):
            if self.mock_result == "error":
                raise Exception("screening_unavailable")
            if self.mock_risk_index is not None:
                return self.mock_risk_index
            if self.mock_result == "approved":
                return 25
            elif self.mock_result == "review":
                return 50
            elif self.mock_result == "declined":
                return 80
            return 25

    class MockTariffEngine(TariffEngine):
        def __init__(self, mock_price=None):
            self.mock_price = mock_price

        def price(self, weight_kg, distance_km):
            if self.mock_price is not None:
                return self.mock_price
            return super().price(weight_kg, distance_km)

    class MockQuoteStore(QuoteStore):
        def __init__(self, mock_result=None):
            super().__init__()
            self.mock_result = mock_result

        def store_draft(
            self, shipper_id, weight_kg, distance_km, declared_value
        ):
            if self.mock_result == "error":
                raise Exception("store_unavailable")
            return super().store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )

    screening_result = request.get("screening_result")
    screening_risk_index = request.get("screening_risk_index")
    store_result = request.get("store_result")
    pricing_result = request.get("pricing_result")

    mock_screening = MockScreeningService(
        mock_result=screening_result,
        mock_risk_index=screening_risk_index,
    )
    mock_tariff = MockTariffEngine(mock_price=pricing_result)
    mock_store = MockQuoteStore(mock_result=store_result)
    mock_notification = NotificationService()

    api = QuoteAPI(
        quote_store=mock_store,
        screening_service=mock_screening,
        tariff_engine=mock_tariff,
        notification_service=mock_notification,
    )

    try:
        result = api.request_quote(
            shipper_id=request.get("shipper_id", "SHIPPER-001"),
            weight_kg=request.get("weight_kg", 500),
            distance_km=request.get("distance_km", 100),
            declared_value=request.get("declared_value", 5000),
        )
        return result
    except Exception as e:
        return {"status": f"error: {str(e)}"}