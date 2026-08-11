"""CargoQuote — Instant Freight Quotation System."""

class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str) -> float:
        """Return risk index (0.0–100.0). Raises ScreeningUnavailableError on failure."""
        raise ScreeningUnavailableError("screening service unavailable")


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute price amount in currency units."""
        base_rate = 0.5
        weight_factor = weight_kg / 100.0
        distance_factor = distance_km / 10.0
        return round(base_rate * weight_factor * distance_factor, 2)


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> None:
        """Deliver quote document. Fire-and-forget."""
        pass

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Deliver refusal notice. Fire-and-forget."""
        pass


class QuoteStore:
    """PostgreSQL-backed quote record storage."""

    def __init__(self):
        self.quotes = {}
        self.next_id = 1000

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store draft quote; return quoteId. Raises StoreUnavailableError on failure."""
        quote_id = str(self.next_id)
        self.next_id += 1
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

    def update_quote(self, quote_id: str, status: str, price_amount: float = None) -> dict:
        """Update quote status and optionally price; return updated quote. Raises StoreUnavailableError on failure."""
        if quote_id not in self.quotes:
            raise StoreUnavailableError(f"quote {quote_id} not found")
        quote = self.quotes[quote_id]
        quote["status"] = status
        if price_amount is not None:
            quote["price_amount"] = price_amount
        return quote


class QuoteAPI:
    """Quote request orchestrator."""

    def __init__(self, quote_store: QuoteStore, screening_service: ScreeningService,
                 tariff_engine: TariffEngine, notification_service: NotificationService):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> dict:
        """Process quote request through screening and pricing; return response."""
        # Decision table DT-V: validate request bounds.
        if not self._validate_request(weight_kg, distance_km, declared_value):
            return {"status": "rejected_invalid_request"}

        # Step 1: Store draft.
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError:
            return {"status": "store_unavailable_error"}

        # Step 2: Screen shipper.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Step 3 (screening failure path): price, hold unscreened, do not notify.
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
                return {"status": "held_unscreened_response", "quote_id": quote_id, "price": price_amount}
            except Exception:
                return {"status": "error: price or store failed"}

        # Step 3: Apply screening decision (DT-S rows).
        ACCEPT_MAX = 30.0
        REVIEW_MIN = 31.0
        REVIEW_MAX = 70.0
        REFUSE_MIN = 71.0

        if risk_index <= ACCEPT_MAX:
            # Accept: price, update to quoted, notify.
            try:
                price_amount = self.tariff_engine.price(weight_kg, distance_km)
                self.quote_store.update_quote(quote_id, "quoted", price_amount)
                self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
                return {"status": "quoted_response", "quote_id": quote_id, "price": price_amount}
            except Exception as e:
                return {"status": f"error: {str(e)}"}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # Review: update to review hold, no pricing, no notification.
            try:
                self.quote_store.update_quote(quote_id, "review_hold")
                return {"status": "review_hold_response", "quote_id": quote_id}
            except Exception as e:
                return {"status": f"error: {str(e)}"}
        elif risk_index >= REFUSE_MIN:
            # Refuse: update to refused_screening, notify refusal, no pricing.
            try:
                self.quote_store.update_quote(quote_id, "refused_screening")
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
                return {"status": "refused_screening_response", "quote_id": quote_id}
            except Exception as e:
                return {"status": f"error: {str(e)}"}

        return {"status": "error: unknown screening outcome"}

    def _validate_request(self, weight_kg: float, distance_km: float, declared_value: float) -> bool:
        """Validate request bounds (DT-V)."""
        if weight_kg <= 0 or weight_kg > 25000:
            return False
        if distance_km <= 0 or distance_km > 3000:
            return False
        if declared_value < 0 or declared_value > 1000000:
            return False
        return True


class ScreeningUnavailableError(Exception):
    """Screening service unavailable."""
    pass


class StoreUnavailableError(Exception):
    """Quote store unavailable."""
    pass


def handle(request: dict) -> dict:
    """Run one end-to-end quote request flow."""
    shipper_id = request.get("shipper_id", "shipper_001")
    weight_kg = request.get("weight_kg", 500.0)
    distance_km = request.get("distance_km", 200.0)
    declared_value = request.get("declared_value", 10000.0)

    # Inject mock behaviors from request.
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()

    # Simulate external outcomes from request keys.
    if "screening_result" in request:
        result = request["screening_result"]
        if isinstance(result, (int, float)):
            screening_service.screen = lambda shipper_id: float(result)
        elif result == "error":
            screening_service.screen = lambda shipper_id: (_ for _ in ()).throw(ScreeningUnavailableError("screening failed"))

    if "store_result" in request:
        result = request["store_result"]
        if result == "error":
            quote_store.store_draft = lambda *args, **kwargs: (_ for _ in ()).throw(StoreUnavailableError("store failed"))

    if "quote_store_exists" in request and not request["quote_store_exists"]:
        quote_store.store_draft = lambda *args, **kwargs: (_ for _ in ()).throw(StoreUnavailableError("store unavailable"))

    # Simulate validation failure.
    if request.get("invalid_request"):
        weight_kg = -1

    api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)
    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)