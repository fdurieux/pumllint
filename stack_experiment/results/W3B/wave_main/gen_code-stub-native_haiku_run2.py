"""CargoQuote — Instant Freight Quotation System."""

# Configuration constants
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

# Validation bounds
MIN_WEIGHT_KG = 1
MAX_WEIGHT_KG = 30000
MIN_DISTANCE_KM = 1
MAX_DISTANCE_KM = 5000
MIN_DECLARED_VALUE = 0
MAX_DECLARED_VALUE = 1000000


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id):
        """Return riskIndex (0-100). Raises ScreeningUnavailableError on failure."""
        if not shipper_id:
            raise ScreeningUnavailableError("Invalid shipper_id")
        return 50  # Default plausible value


class TariffEngine:
    """Computes freight price from weight and distance."""

    def price(self, weight_kg, distance_km):
        """Return priceAmount in cents."""
        if weight_kg <= 0 or distance_km <= 0:
            raise ValueError("Invalid weight or distance")
        base_rate = 100  # cents per km
        weight_surcharge = weight_kg * 5  # cents per kg
        return int(base_rate * distance_km + weight_surcharge)


class QuoteStore:
    """Stores quote requests and lifecycle status."""

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        """Store draft quote; return quoteId."""
        if not shipper_id or weight_kg <= 0 or distance_km <= 0:
            raise StoreUnavailableError("Invalid quote parameters")
        return f"quote_{shipper_id}_{hash((weight_kg, distance_km)) % 10000}"

    def update_quote(self, quote_id, status, price_amount=None):
        """Update quote status and optional price; return updated quote record."""
        if not quote_id:
            raise StoreUnavailableError("Invalid quote_id")
        return {
            "quote_id": quote_id,
            "status": status,
            "price_amount": price_amount
        }


class NotificationService:
    """Delivers quote documents and refusal notices (fire-and-forget)."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        """Send quote document; fire-and-forget, never fails the flow."""
        pass

    def send_refusal_notice(self, shipper_id, quote_id):
        """Send refusal notice; fire-and-forget, never fails the flow."""
        pass


class ScreeningUnavailableError(Exception):
    """Screening service unavailable."""
    pass


class StoreUnavailableError(Exception):
    """Quote store unavailable."""
    pass


class QuoteAPI:
    """Orchestrates quote request validation, screening, pricing, and notification."""

    def __init__(self, screening_service, tariff_engine, quote_store, notification_service):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service

    def _validate_request(self, shipper_id, weight_kg, distance_km, declared_value):
        """Validate request against decision table DT-V bounds."""
        if not shipper_id:
            return False, "shipper_id is required"
        if weight_kg < MIN_WEIGHT_KG or weight_kg > MAX_WEIGHT_KG:
            return False, f"weight_kg must be between {MIN_WEIGHT_KG} and {MAX_WEIGHT_KG}"
        if distance_km < MIN_DISTANCE_KM or distance_km > MAX_DISTANCE_KM:
            return False, f"distance_km must be between {MIN_DISTANCE_KM} and {MAX_DISTANCE_KM}"
        if declared_value < MIN_DECLARED_VALUE or declared_value > MAX_DECLARED_VALUE:
            return False, f"declared_value must be between {MIN_DECLARED_VALUE} and {MAX_DECLARED_VALUE}"
        return True, None

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        """
        Main quotation flow: validate, store draft, screen shipper, apply
        screening decision, price (if approved), and notify.

        Returns dict with keys:
          - "status": outcome name (quotedResponse, reviewHoldResponse, etc.)
          - "quote_id": quote identifier (if applicable)
          - "price_amount": price in cents (if quoted)
          - "reason": error reason (if applicable)
        """

        # Step 1: Validate request
        is_valid, error_msg = self._validate_request(
            shipper_id, weight_kg, distance_km, declared_value
        )
        if not is_valid:
            return {
                "status": "rejectedInvalidRequest",
                "reason": error_msg
            }

        # Step 2: Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError as e:
            return {
                "status": "storeUnavailableError",
                "reason": str(e)
            }

        # Step 3: Screen shipper
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening unavailable: price the quote, hold it unscreened
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "statusHeldUnscreened", price_amount)
            return {
                "status": "heldUnscreenedResponse",
                "quote_id": quote_id,
                "price_amount": price_amount
            }

        # Step 4: Apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            # Row: accept — price and notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "statusQuoted", price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {
                "status": "quotedResponse",
                "quote_id": quote_id,
                "price_amount": price_amount
            }

        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # Row: review — hold for manual review, no pricing or notification
            self.quote_store.update_quote(quote_id, "statusReviewHold")
            return {
                "status": "reviewHoldResponse",
                "quote_id": quote_id
            }

        else:  # risk_index >= REFUSE_MIN
            # Row: refuse — mark refused, notify, no pricing
            self.quote_store.update_quote(quote_id, "statusRefusedScreening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refusedScreeningResponse",
                "quote_id": quote_id
            }


def handle(request: dict) -> dict:
    """
    End-to-end quote request handler.

    Input request dict keys:
      - shipper_id: str
      - weight_kg: float
      - distance_km: float
      - declared_value: float
      - (optional) screening_result: int (overrides service)
      - (optional) screening_status: str ("approved", "error", etc.; overrides result)
      - (optional) store_status: str ("error" triggers StoreUnavailableError)

    Returns dict with status and optional quote_id, price_amount, reason.
    """

    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg", 0)
    distance_km = request.get("distance_km", 0)
    declared_value = request.get("declared_value", 0)

    # Create service instances, optionally injecting test behaviors
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()

    # Wrap screening service to return test result if provided
    original_screen = screening_service.screen
    def screen_with_override(sid):
        if "screening_status" in request:
            if request["screening_status"] == "error":
                raise ScreeningUnavailableError("Screening service error")
            return request.get("screening_result", 50)
        if "screening_result" in request:
            return request["screening_result"]
        return original_screen(sid)
    screening_service.screen = screen_with_override

    # Wrap store to inject test behavior
    original_store_draft = quote_store.store_draft
    def store_draft_with_override(sid, wkg, dkm, dval):
        if request.get("store_status") == "error":
            raise StoreUnavailableError("Store unavailable")
        return original_store_draft(sid, wkg, dkm, dval)
    quote_store.store_draft = store_draft_with_override

    api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)
    result = api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    return result