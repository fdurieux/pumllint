# CargoQuote — instant freight quotation system (single module implementation).

# --- Configuration / decision-table thresholds ---

ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70

# Validation bounds (decision table DT-V)
WEIGHT_MIN = 1
WEIGHT_MAX = 44000
DISTANCE_MIN = 1
DISTANCE_MAX = 5000
VALUE_MIN = 0
VALUE_MAX = 10_000_000

# Quote lifecycle status constants
STATUS_QUOTED = "QUOTED"
STATUS_REVIEW_HOLD = "REVIEW_HOLD"
STATUS_REFUSED_SCREENING = "REFUSED_SCREENING"
STATUS_HELD_UNSCREENED = "HELD_UNSCREENED"


# --- Internal exceptions for failure paths ---

class ScreeningUnavailableError(Exception):
    """Raised when the external screening provider is unavailable."""


class StoreUnavailableError(Exception):
    """Raised when the quote store cannot persist a draft."""


class ValidationError(Exception):
    """Raised when a quote request fails validation (DT-V)."""


# --- Tariff Engine (internal container) ---

class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    BASE_FEE = 25.0
    PER_KG = 0.12
    PER_KM = 0.35

    def price(self, weight_kg, distance_km):
        amount = self.BASE_FEE + (weight_kg * self.PER_KG) + (distance_km * self.PER_KM)
        return round(amount, 2)


# --- Screening Service (external system) ---

class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, outcome=None):
        # outcome may be a number (risk index), a word, or "error"/"unavailable".
        self._outcome = outcome

    def screen(self, shipper_id):
        outcome = self._outcome

        if outcome is None:
            return 10  # default: low risk / accept

        if isinstance(outcome, (int, float)):
            return outcome

        word = str(outcome).strip().lower()
        if word in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailableError("screening service unavailable")
        if word in ("approved", "accept", "accepted", "clear", "assessed"):
            return 10
        if word in ("review", "hold", "manual"):
            return 50
        if word in ("declined", "refused", "refuse", "denied", "blocked"):
            return 90

        # Numeric string?
        try:
            return float(word)
        except ValueError:
            return 10


# --- Notification Service (external system) ---

class NotificationService:
    """External messaging provider. Fire-and-forget delivery."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        # Fire-and-forget: delivery failures never affect the response.
        return "queued"

    def send_refusal_notice(self, shipper_id, quote_id):
        # Fire-and-forget: delivery failures never affect the response.
        return "queued"


# --- Quote Store (internal database container) ---

class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, store_status=None):
        self._store_status = store_status
        self._seq = 0
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        status = self._store_status
        if status is not None and str(status).strip().lower() in (
            "error", "unavailable", "down", "fail", "failed"
        ):
            raise StoreUnavailableError("quote storage unavailable")

        self._seq += 1
        quote_id = "Q-%04d" % self._seq
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "DRAFT",
            "price_amount": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        record = self._records.get(quote_id, {})
        record["status"] = status
        if price_amount is not None:
            record["price_amount"] = price_amount
        self._records[quote_id] = record
        return record


# --- Quote API (entry participant / orchestrator) ---

class QuoteAPI:
    """Receives quote requests, validates them, orchestrates screening
    and pricing, and returns the quotation outcome."""

    def __init__(self, tariff_engine, screening_service,
                 notification_service, quote_store):
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service
        self.quote_store = quote_store

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            raise ValidationError("missing shipper id")
        if not isinstance(weight_kg, (int, float)) or \
                not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            raise ValidationError("weight out of bounds")
        if not isinstance(distance_km, (int, float)) or \
                not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            raise ValidationError("distance out of bounds")
        if not isinstance(declared_value, (int, float)) or \
                not (VALUE_MIN <= declared_value <= VALUE_MAX):
            raise ValidationError("declared value out of bounds")

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Step 1: validation (DT-V)
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as exc:
            return {"status": "rejectedInvalidRequest", "reason": str(exc)}

        # Step 1 (cont): store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError as exc:
            # DT-S note 3: on storage failure nothing else runs.
            return {"status": "storeUnavailableError", "reason": str(exc)}

        # Step 2: screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: screening outage does NOT fail the quote.
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, STATUS_HELD_UNSCREENED, price_amount)
            return {
                "status": "heldUnscreenedResponse",
                "quote_id": quote_id,
                "price_amount": price_amount,
            }

        # Step 3: apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            # accept
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, STATUS_QUOTED, price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount)
            return {
                "status": "quotedResponse",
                "quote_id": quote_id,
                "price_amount": price_amount,
            }

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # review hold — DT-S note 1: no pricing, no notification.
            self.quote_store.update_quote(quote_id, STATUS_REVIEW_HOLD)
            return {"status": "reviewHoldResponse", "quote_id": quote_id}

        # risk_index >= REFUSE_MIN -> refuse
        # DT-S note 2: refusal IS notified; pricing never runs.
        self.quote_store.update_quote(quote_id, STATUS_REFUSED_SCREENING)
        self.notification_service.send_refusal_notice(shipper_id, quote_id)
        return {"status": "refusedScreeningResponse", "quote_id": quote_id}


# --- Module-level end-to-end entry point ---

# Maps internal response names to outward outcome words.
_OUTCOME_MAP = {
    "quotedResponse": "confirmed",
    "reviewHoldResponse": "review_hold",
    "refusedScreeningResponse": "refused",
    "heldUnscreenedResponse": "held_unscreened",
    "rejectedInvalidRequest": "rejected",
    "storeUnavailableError": "error: storage_unavailable",
}


def _pick(request, *keys, default=None):
    for key in keys:
        if key in request and request[key] is not None:
            return request[key]
    return default


def handle(request: dict) -> dict:
    """Run one end-to-end quotation flow from a scenario input dict."""
    request = request or {}

    shipper_id = _pick(request, "shipper_id", "shipperId", default="SHIP-1")

    # Existence flags may reject before any real work.
    if request.get("shipper_exists") is False or \
            request.get("shipper_found") is False:
        return {"status": "rejected", "reason": "shipper not found"}

    weight_kg = _pick(request, "weight_kg", "weight", default=100)
    distance_km = _pick(request, "distance_km", "distance", default=100)
    declared_value = _pick(request, "declared_value", "value", "amount",
                           default=1000)

    screening_outcome = _pick(request, "screening_result", "screening_status")
    store_status = _pick(request, "store_result", "store_status",
                         "quote_store_result", "quote_store_status")

    tariff_engine = TariffEngine()
    screening_service = ScreeningService(outcome=screening_outcome)
    notification_service = NotificationService()
    quote_store = QuoteStore(store_status=store_status)

    api = QuoteAPI(tariff_engine, screening_service,
                   notification_service, quote_store)

    result = api.request_quote(shipper_id, weight_kg, distance_km,
                               declared_value)

    internal_status = result.get("status")
    outcome = _OUTCOME_MAP.get(internal_status, internal_status)

    response = dict(result)
    response["status"] = outcome
    response["detail"] = internal_status
    return response