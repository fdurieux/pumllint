"""CargoQuote — Instant Freight Quotation System."""


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str) -> float:
        """Return risk index (0.0–100.0). Raises ScreeningUnavailableError on failure."""
        return 0.0


class TariffEngine:
    """Computes freight price from weight and distance."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute price amount. Returns a single float price value."""
        base_rate = 0.5
        distance_factor = 0.01
        weight_factor = 0.001
        return base_rate * weight_kg * (1 + distance_km * distance_factor)


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        """Deliver quote document. Fire-and-forget; returns delivery confirmation."""
        return "delivered"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Deliver refusal notice. Fire-and-forget; returns delivery confirmation."""
        return "delivered"


class QuoteStore:
    """PostgreSQL-backed quote record storage."""

    def __init__(self):
        self._quotes = {}
        self._counter = 0

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store draft quote; return quote ID. Raises StoreUnavailableError on failure."""
        self._counter += 1
        quote_id = f"Q{self._counter:06d}"
        self._quotes[quote_id] = {
            "id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price_amount": None,
        }
        return quote_id

    def update_quote(self, quote_id: str, status: str, price_amount: float = None) -> dict:
        """Update quote status and optionally price. Returns updated quote dict."""
        if quote_id not in self._quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self._quotes[quote_id]["status"] = status
        if price_amount is not None:
            self._quotes[quote_id]["price_amount"] = price_amount
        return self._quotes[quote_id]


class QuoteAPI:
    """Main quotation service orchestrating validation, screening, pricing, and notification."""

    ACCEPT_MAX = 30.0
    REVIEW_MIN = 30.0
    REVIEW_MAX = 70.0
    REFUSE_MIN = 70.0

    def __init__(self, store: QuoteStore, screening: ScreeningService, tariff: TariffEngine, notification: NotificationService):
        self.store = store
        self.screening = screening
        self.tariff = tariff
        self.notification = notification

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        """
        Main quotation flow:
        1. Validate request (decision table DT-V).
        2. Store draft.
        3. Screen shipper.
        4. Apply screening decision and pricing (decision table DT-S).
        5. Notify and respond.
        """
        # Step 1: Validate request.
        validation_error = self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if validation_error:
            return {"status": "rejected_invalid_request", "reason": validation_error}

        # Step 2: Store draft.
        try:
            quote_id = self.store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception as e:
            return {"status": "store_unavailable_error", "reason": str(e)}

        # Step 3: Screen shipper.
        try:
            risk_index = self.screening.screen(shipper_id)
        except Exception:
            risk_index = None

        # Step 4: Apply screening decision and pricing.
        if risk_index is None:
            # Screening unavailable (note 5): price, hold, no notification.
            try:
                price_amount = self.tariff.price(weight_kg, distance_km)
                self.store.update_quote(quote_id, "held_unscreened", price_amount)
                return {"status": "held_unscreened_response", "quote_id": quote_id, "price_amount": price_amount}
            except Exception as e:
                return {"status": "error", "reason": str(e)}

        if risk_index <= self.ACCEPT_MAX:
            # Accept (note: row accept): price, update, notify.
            try:
                price_amount = self.tariff.price(weight_kg, distance_km)
                self.store.update_quote(quote_id, "quoted", price_amount)
                self.notification.send_quote_document(shipper_id, quote_id, price_amount)
                return {"status": "quoted_response", "quote_id": quote_id, "price_amount": price_amount}
            except Exception as e:
                return {"status": "error", "reason": str(e)}

        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review (note 1): hold for manual review, no pricing, no notification.
            try:
                self.store.update_quote(quote_id, "review_hold")
                return {"status": "review_hold_response", "quote_id": quote_id}
            except Exception as e:
                return {"status": "error", "reason": str(e)}

        elif risk_index >= self.REFUSE_MIN:
            # Refuse (note 2): refuse, notify, no pricing.
            try:
                self.store.update_quote(quote_id, "refused_screening")
                self.notification.send_refusal_notice(shipper_id, quote_id)
                return {"status": "refused_screening_response", "quote_id": quote_id}
            except Exception as e:
                return {"status": "error", "reason": str(e)}

        return {"status": "error", "reason": "Unknown screening decision"}

    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Validate request bounds per DT-V. Return error reason or None if valid."""
        if not shipper_id or len(shipper_id) == 0:
            return "shipper_id_missing"
        if weight_kg <= 0 or weight_kg > 25000:
            return "weight_out_of_bounds"
        if distance_km <= 0 or distance_km > 5000:
            return "distance_out_of_bounds"
        if declared_value < 0 or declared_value > 1000000:
            return "declared_value_out_of_bounds"
        return None


def handle(request: dict) -> dict:
    """
    End-to-end quotation flow entry point.
    
    request keys:
      - shipper_id: str
      - weight_kg: float
      - distance_km: float
      - declared_value: float
      - screening_result: str (optional, for testing: "approved", "declined", "error")
      - store_result: str (optional, for testing: "stored", "error")
    
    Returns a dict with "status" key naming the outcome.
    """
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0.0)
    distance_km = request.get("distance_km", 0.0)
    declared_value = request.get("declared_value", 0.0)

    store = QuoteStore()
    
    class MockScreeningService(ScreeningService):
        def screen(self, shipper_id: str) -> float:
            result = request.get("screening_result", "approved")
            if result == "approved":
                return 25.0
            elif result == "review":
                return 50.0
            elif result == "declined":
                return 85.0
            elif result == "error":
                raise Exception("Screening service unavailable")
            return 25.0

    class MockQuoteStore(QuoteStore):
        def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
            result = request.get("store_result", "stored")
            if result == "error":
                raise Exception("Store unavailable")
            return super().store_draft(shipper_id, weight_kg, distance_km, declared_value)

    screening = MockScreeningService()
    tariff = TariffEngine()
    notification = NotificationService()
    store = MockQuoteStore()

    api = QuoteAPI(store, screening, tariff, notification)
    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)