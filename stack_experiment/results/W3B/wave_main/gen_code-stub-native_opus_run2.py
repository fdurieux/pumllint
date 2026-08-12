class ScreeningUnavailableError(Exception):
    """Raised when the screening provider is unavailable."""


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable."""


# Screening decision thresholds (risk index scale 0..100).
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

# Validation bounds (decision table DT-V).
WEIGHT_MIN = 1
WEIGHT_MAX = 30000
DISTANCE_MIN = 1
DISTANCE_MAX = 3000
VALUE_MIN = 0
VALUE_MAX = 10_000_000

# Status constants.
STATUS_QUOTED = "quoted"
STATUS_REVIEW_HOLD = "review_hold"
STATUS_REFUSED_SCREENING = "refused_screening"
STATUS_HELD_UNSCREENED = "held_unscreened"


class TariffEngine:
    """Computes the freight price from weight and distance."""

    BASE_RATE = 5.0          # currency per km baseline handling
    PER_KG_KM = 0.0009       # currency per kg per km

    def price(self, weight_kg, distance_km):
        """Compute priceAmount for a validated request."""
        amount = self.BASE_RATE + (weight_kg * distance_km * self.PER_KG_KM)
        return round(amount, 2)


class ScreeningService:
    """External denied-party screening provider."""

    def __init__(self, outcome=None):
        self._outcome = outcome

    def screen(self, shipper_id):
        """Return riskIndex, or raise screeningUnavailableError."""
        outcome = self._outcome
        if outcome is None:
            return 10
        if isinstance(outcome, (int, float)):
            return outcome
        word = str(outcome).strip().lower()
        if word in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailableError("screening service unavailable")
        if word in ("approved", "accept", "accepted", "clear", "active"):
            return 10
        if word in ("review", "assessed", "hold", "manual"):
            return 50
        if word in ("declined", "refused", "refuse", "denied", "hit"):
            return 90
        # Try to interpret numeric strings.
        try:
            return float(word)
        except ValueError:
            return 10


class NotificationService:
    """External messaging provider (fire-and-forget)."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        """Deliver the quote document; failures never change the response."""
        try:
            return "sent"
        except Exception:
            return "failed"

    def send_refusal_notice(self, shipper_id, quote_id):
        """Deliver the refusal notice; failures never change the response."""
        try:
            return "sent"
        except Exception:
            return "failed"


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, store_outcome=None):
        self._store_outcome = store_outcome
        self._seq = 0
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        """Store the draft; return quoteId, or raise storeUnavailableError."""
        if self._store_outcome is not None:
            word = str(self._store_outcome).strip().lower()
            if word in ("error", "unavailable", "down", "timeout"):
                raise StoreUnavailableError("storage unavailable")
        self._seq += 1
        quote_id = "Q{:06d}".format(self._seq)
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
        """Update status (and optionally price); return updatedQuote."""
        record = self._records.get(quote_id, {})
        record["status"] = status
        if price_amount is not None:
            record["price_amount"] = price_amount
        self._records[quote_id] = record
        return dict(record, quote_id=quote_id)


class QuoteAPI:
    """Entry participant: orchestrates validation, screening and pricing."""

    def __init__(self, tariff_engine, screening_service,
                 notification_service, quote_store):
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service
        self.quote_store = quote_store

    def _is_valid(self, weight_kg, distance_km, declared_value):
        if weight_kg is None or distance_km is None or declared_value is None:
            return False
        try:
            w = float(weight_kg)
            d = float(distance_km)
            v = float(declared_value)
        except (TypeError, ValueError):
            return False
        if not (WEIGHT_MIN <= w <= WEIGHT_MAX):
            return False
        if not (DISTANCE_MIN <= d <= DISTANCE_MAX):
            return False
        if not (VALUE_MIN <= v <= VALUE_MAX):
            return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km,
                      declared_value):
        # 1. Validation (DT-V).
        if not self._is_valid(weight_kg, distance_km, declared_value):
            return {"status": "rejected",
                    "response": "rejectedInvalidRequest"}

        # 2. Store draft.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError:
            return {"status": "error: storage unavailable",
                    "response": "storeUnavailableError"}

        # Screening.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: outage does not fail the quote.
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, STATUS_HELD_UNSCREENED, price_amount)
            return {"status": "held_unscreened",
                    "response": "heldUnscreenedResponse",
                    "quote_id": quote_id,
                    "price_amount": price_amount}

        # 3. Screening decision (DT-S).
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, STATUS_QUOTED, price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount)
            return {"status": "quoted",
                    "response": "quotedResponse",
                    "quote_id": quote_id,
                    "price_amount": price_amount}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, STATUS_REVIEW_HOLD)
            return {"status": "review_hold",
                    "response": "reviewHoldResponse",
                    "quote_id": quote_id}

        # riskIndex >= REFUSE_MIN
        self.quote_store.update_quote(quote_id, STATUS_REFUSED_SCREENING)
        self.notification_service.send_refusal_notice(shipper_id, quote_id)
        return {"status": "refused",
                "response": "refusedScreeningResponse",
                "quote_id": quote_id}


def handle(request: dict) -> dict:
    """Run one end-to-end quotation flow."""
    request = request or {}

    shipper_id = request.get("shipper_id", request.get("shipper", "unknown"))
    weight_kg = request.get("weight_kg", request.get("weight"))
    distance_km = request.get("distance_km", request.get("distance"))
    declared_value = request.get("declared_value", request.get("value"))

    # Handle explicit existence flags for the shipper.
    if request.get("shipper_exists") is False or \
            request.get("shipper_found") is False:
        return {"status": "rejected", "response": "rejectedInvalidRequest"}

    screening_outcome = request.get("screening_result",
                                    request.get("screening_status"))
    store_outcome = request.get("store_result", request.get("store_status"))

    tariff_engine = TariffEngine()
    screening_service = ScreeningService(screening_outcome)
    notification_service = NotificationService()
    quote_store = QuoteStore(store_outcome)

    api = QuoteAPI(tariff_engine, screening_service,
                   notification_service, quote_store)

    return api.request_quote(shipper_id, weight_kg, distance_km,
                             declared_value)