import threading

# --- Decision table constants ---------------------------------------------

# DT-V: request validation bounds
WEIGHT_MIN = 1
WEIGHT_MAX = 26000
DISTANCE_MIN = 1
DISTANCE_MAX = 3000
VALUE_MIN = 0

# DT-S: screening decision thresholds (risk index)
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70

# Lifecycle statuses
STATUS_QUOTED = "quoted"
STATUS_REVIEW_HOLD = "review_hold"
STATUS_REFUSED_SCREENING = "refused_screening"
STATUS_HELD_UNSCREENED = "held_unscreened"


# --- Errors ----------------------------------------------------------------

class ScreeningUnavailableError(Exception):
    """Raised when the screening provider is unavailable."""


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable."""


# --- External systems ------------------------------------------------------

class ScreeningService:  # external
    """External denied-party screening provider returning a risk index."""

    def __init__(self, outcome=None):
        # outcome may be a number (risk index) or a short word.
        self._outcome = outcome

    def screen(self, shipper_id):
        """Return riskIndex. Failure surfaces as ScreeningUnavailableError."""
        outcome = self._outcome
        if outcome is None:
            return 0
        if isinstance(outcome, (int, float)):
            return outcome
        word = str(outcome).strip().lower()
        if word in ("error", "unavailable", "timeout"):
            raise ScreeningUnavailableError("screening service unavailable")
        if word in ("approved", "accept", "accepted", "clear", "active"):
            return 0
        if word in ("review", "hold", "assessed"):
            return 50
        if word in ("declined", "refuse", "refused", "denied"):
            return 100
        # Try to parse a numeric string.
        try:
            return float(word)
        except ValueError:
            return 0


class NotificationService:  # external
    """External messaging provider. Fire-and-forget delivery."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        """Deliver the quote document; failures never change the response."""
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        """Deliver the refusal notice; failures never change the response."""
        return "sent"


# --- Internal containers ---------------------------------------------------

class TariffEngine:  # engine
    """Computes the freight price from weight and distance."""

    BASE_RATE = 5.0          # base handling charge
    PER_KG = 0.15            # per kilogram
    PER_KM = 0.30            # per kilometer

    def price(self, weight_kg, distance_km):
        """Compute the priceAmount for a validated request."""
        amount = self.BASE_RATE + (self.PER_KG * weight_kg) + \
            (self.PER_KM * distance_km)
        return round(amount, 2)


class QuoteStore:  # database
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self._available = available
        self._records = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        """Store the draft; return quoteId or raise StoreUnavailableError."""
        if not self._available:
            raise StoreUnavailableError("storage unavailable")
        self._seq += 1
        quote_id = "Q%05d" % self._seq
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
        """Update the record; return the updatedQuote."""
        record = self._records.get(quote_id)
        if record is None:
            record = {"shipper_id": None}
            self._records[quote_id] = record
        record["status"] = status
        if price_amount is not None:
            record["price_amount"] = price_amount
        return dict(record, quote_id=quote_id)


# --- Orchestrating service -------------------------------------------------

class QuoteAPI:  # service — the entry participant
    """Receives quote requests and orchestrates screening and pricing."""

    def __init__(self, tariff_engine, screening_service, notification_service,
                 quote_store):
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service
        self.quote_store = quote_store

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            return False
        if not isinstance(weight_kg, (int, float)):
            return False
        if not isinstance(distance_km, (int, float)):
            return False
        if not isinstance(declared_value, (int, float)):
            return False
        if weight_kg < WEIGHT_MIN or weight_kg > WEIGHT_MAX:
            return False
        if distance_km < DISTANCE_MIN or distance_km > DISTANCE_MAX:
            return False
        if declared_value < VALUE_MIN:
            return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km,
                      declared_value):
        # Step 1: validate (DT-V).
        if not self._validate(shipper_id, weight_kg, distance_km,
                              declared_value):
            return {"status": "rejected",
                    "reason": "rejectedInvalidRequest"}

        # Step 1/2: store draft.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError:
            # Nothing else runs (DT-S note 3).
            return {"status": "error: storage unavailable",
                    "reason": "storeUnavailableError"}

        # Step 2: screening.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: outage does not fail the quote.
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, STATUS_HELD_UNSCREENED, price_amount)
            return {"status": "held_unscreened",
                    "reason": "heldUnscreenedResponse",
                    "quote_id": quote_id,
                    "price_amount": price_amount}

        # Step 3: apply screening decision (DT-S).
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, STATUS_QUOTED, price_amount)
            self._fire_and_forget(
                self.notification_service.send_quote_document,
                shipper_id, quote_id, price_amount)
            return {"status": "confirmed",
                    "reason": "quotedResponse",
                    "quote_id": quote_id,
                    "price_amount": price_amount}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, STATUS_REVIEW_HOLD)
            return {"status": "review_hold",
                    "reason": "reviewHoldResponse",
                    "quote_id": quote_id}

        # risk_index >= REFUSE_MIN
        self.quote_store.update_quote(quote_id, STATUS_REFUSED_SCREENING)
        self._fire_and_forget(
            self.notification_service.send_refusal_notice,
            shipper_id, quote_id)
        return {"status": "refused",
                "reason": "refusedScreeningResponse",
                "quote_id": quote_id}

    @staticmethod
    def _fire_and_forget(func, *args):
        """Run a notification without letting failures affect the response."""
        def runner():
            try:
                func(*args)
            except Exception:
                pass
        thread = threading.Thread(target=runner)
        thread.daemon = True
        thread.start()


# --- Module-level entry point ----------------------------------------------

def _screening_outcome(request):
    for key in ("screening_result", "screening_status"):
        if key in request and request[key] is not None:
            return request[key]
    return 0


def _store_available(request):
    for key in ("store_result", "store_status", "quote_store_result",
                "quote_store_status"):
        if key in request and request[key] is not None:
            word = str(request[key]).strip().lower()
            if word in ("error", "unavailable", "down", "failed"):
                return False
    return True


def handle(request: dict) -> dict:
    """Run one end-to-end quotation flow."""
    request = request or {}

    shipper_id = request.get("shipper_id")
    # Honour existence flags.
    if request.get("shipper_exists") is False or \
            request.get("shipper_found") is False:
        shipper_id = None

    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    if declared_value is None:
        declared_value = 0

    tariff_engine = TariffEngine()
    screening_service = ScreeningService(_screening_outcome(request))
    notification_service = NotificationService()
    quote_store = QuoteStore(available=_store_available(request))

    api = QuoteAPI(tariff_engine, screening_service, notification_service,
                   quote_store)

    return api.request_quote(shipper_id, weight_kg, distance_km,
                             declared_value)