import asyncio

# ---- Configuration constants (DT-V validation bounds, DT-S screening bands) ----
WEIGHT_MIN_KG = 1
WEIGHT_MAX_KG = 30000
DISTANCE_MIN_KM = 1
DISTANCE_MAX_KM = 5000
DECLARED_VALUE_MIN = 0
DECLARED_VALUE_MAX = 10_000_000

ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

# Status labels used on stored quote records
STATUS_QUOTED = "quoted"
STATUS_REVIEW_HOLD = "review_hold"
STATUS_REFUSED_SCREENING = "refused_screening"
STATUS_HELD_UNSCREENED = "held_unscreened"


# ---- Errors ----
class ScreeningUnavailableError(Exception):
    """Raised when the screening provider is unavailable."""


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable."""


class ValidationError(Exception):
    """Raised when a quote request fails validation (DT-V)."""


# ---- Tariff Engine (internal container) ----
class TariffEngine:
    BASE_RATE = 0.75          # per kg
    DISTANCE_RATE = 0.12      # per km
    MINIMUM_PRICE = 25.0

    def price(self, weight_kg, distance_km):
        """Compute priceAmount for a validated request."""
        amount = weight_kg * self.BASE_RATE + distance_km * self.DISTANCE_RATE
        return round(max(amount, self.MINIMUM_PRICE), 2)


# ---- Screening Service (external) ----
class ScreeningService:
    def __init__(self, outcome=None):
        # outcome may be a number (risk index), a word, or "error"
        self._outcome = outcome

    def screen(self, shipper_id):
        """Return riskIndex; raise ScreeningUnavailableError on failure."""
        outcome = self._outcome

        if outcome is None:
            return 10  # default: low risk / accept

        if isinstance(outcome, (int, float)):
            return outcome

        word = str(outcome).strip().lower()
        if word in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailableError("screening service unavailable")
        if word in ("approved", "accept", "accepted", "clear", "pass"):
            return 10
        if word in ("review", "hold", "manual", "assessed"):
            return 50
        if word in ("declined", "refused", "refuse", "denied", "reject",
                    "rejected", "blocked"):
            return 90

        # Try to interpret as a numeric string
        try:
            return float(word)
        except ValueError:
            return 10


# ---- Notification Service (external) ----
class NotificationService:
    def send_quote_document(self, shipper_id, quote_id, price_amount):
        """Deliver the quote document. Fire-and-forget."""
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        """Deliver the refusal notice. Fire-and-forget."""
        return "sent"


# ---- Quote Store (internal database container) ----
class QuoteStore:
    def __init__(self, outcome=None):
        self._outcome = outcome
        self._counter = 0
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        """Store the draft; return quoteId; raise on storage failure."""
        if self._outcome is not None:
            word = str(self._outcome).strip().lower()
            if word in ("error", "unavailable", "down", "timeout"):
                raise StoreUnavailableError("storage unavailable")

        self._counter += 1
        quote_id = "Q-%05d" % self._counter
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price_amount": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        """Update the record; return updatedQuote."""
        record = self._records.get(quote_id, {"quote_id": quote_id})
        record["status"] = status
        if price_amount is not None:
            record["price_amount"] = price_amount
        self._records[quote_id] = record
        return record


# ---- Quote API (internal service, entry participant) ----
class QuoteAPI:
    def __init__(self, tariff_engine, screening_service,
                 quote_store, notification_service):
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.quote_store = quote_store
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            raise ValidationError("missing shipper id")
        if not isinstance(weight_kg, (int, float)) or \
                not (WEIGHT_MIN_KG <= weight_kg <= WEIGHT_MAX_KG):
            raise ValidationError("weight out of bounds")
        if not isinstance(distance_km, (int, float)) or \
                not (DISTANCE_MIN_KM <= distance_km <= DISTANCE_MAX_KM):
            raise ValidationError("distance out of bounds")
        if not isinstance(declared_value, (int, float)) or \
                not (DECLARED_VALUE_MIN <= declared_value <= DECLARED_VALUE_MAX):
            raise ValidationError("declared value out of bounds")

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # 1. Validate
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as exc:
            return {"status": "rejected", "reason": "invalid_request",
                    "detail": str(exc)}

        # 2. Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError as exc:
            return {"status": "error: storage unavailable", "detail": str(exc)}

        # 2b. Screen
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: outage does not fail the quote — price, hold, no notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, STATUS_HELD_UNSCREENED, price_amount)
            return {"status": "held_unscreened", "quote_id": quote_id,
                    "price_amount": price_amount}

        # 3. Apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, STATUS_QUOTED, price_amount)
            self._fire_and_forget(
                self.notification_service.send_quote_document,
                shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quote_id": quote_id,
                    "price_amount": price_amount, "risk_index": risk_index}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, STATUS_REVIEW_HOLD)
            return {"status": "review_hold", "quote_id": quote_id,
                    "risk_index": risk_index}

        if risk_index >= REFUSE_MIN:
            self.quote_store.update_quote(quote_id, STATUS_REFUSED_SCREENING)
            self._fire_and_forget(
                self.notification_service.send_refusal_notice,
                shipper_id, quote_id)
            return {"status": "refused", "quote_id": quote_id,
                    "risk_index": risk_index}

        # Fallback (band gap) — treat as review hold
        self.quote_store.update_quote(quote_id, STATUS_REVIEW_HOLD)
        return {"status": "review_hold", "quote_id": quote_id,
                "risk_index": risk_index}

    @staticmethod
    def _fire_and_forget(func, *args):
        """Invoke a notification without letting failures affect the response."""
        try:
            func(*args)
        except Exception:
            pass


# ---- Module-level end-to-end entry point ----
def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id") or request.get("shipper")
    weight_kg = request.get("weight_kg", request.get("weight"))
    distance_km = request.get("distance_km", request.get("distance"))
    declared_value = request.get("declared_value",
                                 request.get("value", 0))

    # Existence flags may indicate a non-existent shipper.
    for key in ("shipper_exists", "shipper_found"):
        if key in request and not request[key]:
            return {"status": "rejected", "reason": "invalid_request",
                    "detail": "shipper not found"}

    screening_outcome = (request.get("screening_result",
                                     request.get("screening_status")))
    store_outcome = (request.get("store_result",
                                 request.get("quote_store_result",
                                             request.get("quote_store_status"))))

    tariff_engine = TariffEngine()
    screening_service = ScreeningService(screening_outcome)
    quote_store = QuoteStore(store_outcome)
    notification_service = NotificationService()

    api = QuoteAPI(tariff_engine, screening_service,
                   quote_store, notification_service)

    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)