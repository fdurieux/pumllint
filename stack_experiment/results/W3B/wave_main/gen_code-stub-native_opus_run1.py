import math


# --- Tariff / pricing configuration ---
BASE_FARE = 25.0
RATE_PER_KG_KM = 0.00035

# --- Screening decision thresholds (decision table DT-S) ---
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

# --- Validation bounds (decision table DT-V) ---
MIN_WEIGHT_KG = 0.0
MAX_WEIGHT_KG = 24000.0
MIN_DISTANCE_KM = 0.0
MAX_DISTANCE_KM = 3000.0
MIN_DECLARED_VALUE = 0.0

# --- Quote lifecycle statuses ---
STATUS_QUOTED = "quoted"
STATUS_REVIEW_HOLD = "review_hold"
STATUS_REFUSED_SCREENING = "refused_screening"
STATUS_HELD_UNSCREENED = "held_unscreened"


class ScreeningUnavailableError(Exception):
    """Raised when the external screening provider is unavailable."""


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable."""


class TariffEngine:  # engine
    def price(self, weight_kg, distance_km):
        """Compute priceAmount for a validated request."""
        amount = BASE_FARE + (float(weight_kg) * float(distance_km) *
                              RATE_PER_KG_KM)
        return round(amount, 2)


class ScreeningService:  # external
    def __init__(self, risk_index=0, unavailable=False):
        self._risk_index = risk_index
        self._unavailable = unavailable

    def screen(self, shipper_id):
        """Return riskIndex, or raise screeningUnavailableError."""
        if self._unavailable:
            raise ScreeningUnavailableError("screening service unavailable")
        return self._risk_index


class NotificationService:  # external
    def send_quote_document(self, shipper_id, quote_id, price_amount):
        """Deliver the quote document. Fire-and-forget."""
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        """Deliver the refusal notice. Fire-and-forget."""
        return "sent"


class QuoteStore:  # database
    def __init__(self, unavailable=False):
        self._unavailable = unavailable
        self._seq = 0
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km,
                    declared_value):
        """Store the draft; return quoteId, or raise storeUnavailableError."""
        if self._unavailable:
            raise StoreUnavailableError("quote store unavailable")
        self._seq += 1
        quote_id = "Q-%05d" % self._seq
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
        """Update the quote record; return the updated quote."""
        record = self._records.get(quote_id, {})
        record["status"] = status
        if price_amount is not None:
            record["price_amount"] = price_amount
        self._records[quote_id] = record
        return record


class QuoteAPI:  # service — the entry participant
    def __init__(self, tariff_engine, screening_service,
                 notification_service, quote_store):
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service
        self.quote_store = quote_store

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if shipper_id is None or str(shipper_id).strip() == "":
            return "missing shipper"
        try:
            w = float(weight_kg)
            d = float(distance_km)
            v = float(declared_value)
        except (TypeError, ValueError):
            return "non-numeric field"
        if math.isnan(w) or math.isnan(d) or math.isnan(v):
            return "non-numeric field"
        if not (MIN_WEIGHT_KG < w <= MAX_WEIGHT_KG):
            return "weight out of bounds"
        if not (MIN_DISTANCE_KM < d <= MAX_DISTANCE_KM):
            return "distance out of bounds"
        if v < MIN_DECLARED_VALUE:
            return "declared value out of bounds"
        return None

    def request_quote(self, shipper_id, weight_kg, distance_km,
                      declared_value):
        # 1. Validate (DT-V)
        error = self._validate(shipper_id, weight_kg, distance_km,
                               declared_value)
        if error is not None:
            return {"status": "rejected",
                    "response": "rejectedInvalidRequest",
                    "reason": error}

        # 1./2. Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError as exc:
            # DT-S note 3: nothing else runs
            return {"status": "error: storage unavailable",
                    "response": "storeUnavailableError",
                    "reason": str(exc)}

        # 2. Screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: price, hold, no notification
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, STATUS_HELD_UNSCREENED, price_amount)
            return {"status": "held_unscreened",
                    "response": "heldUnscreenedResponse",
                    "quote_id": quote_id,
                    "price_amount": price_amount}

        # 3. Apply screening decision (DT-S)
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
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, STATUS_REVIEW_HOLD)
            return {"status": "review_hold",
                    "response": "reviewHoldResponse",
                    "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, STATUS_REFUSED_SCREENING)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused",
                    "response": "refusedScreeningResponse",
                    "quote_id": quote_id}


def _interpret_screening(request):
    """Derive (risk_index, unavailable) from the request."""
    raw = request.get("screening_result", request.get("screening_status"))
    if raw is None:
        raw = request.get("screening_score")
    if raw is None:
        return 0, False
    if isinstance(raw, (int, float)):
        return raw, False
    word = str(raw).strip().lower()
    if word in ("error", "unavailable", "down", "timeout"):
        return 0, True
    if word in ("approved", "accept", "accepted", "clear", "active", "ok"):
        return ACCEPT_MAX, False
    if word in ("review", "hold", "manual", "assessed"):
        return (REVIEW_MIN + REVIEW_MAX) // 2, False
    if word in ("declined", "refused", "refuse", "denied", "blocked",
                "lapsed"):
        return REFUSE_MIN, False
    try:
        return float(word), False
    except ValueError:
        return 0, False


def _interpret_store(request):
    raw = request.get("store_result", request.get("store_status"))
    if raw is None:
        return False
    word = str(raw).strip().lower()
    return word in ("error", "unavailable", "down", "fail", "failed")


def handle(request: dict) -> dict:
    """Run one end-to-end quotation flow."""
    if not isinstance(request, dict):
        return {"status": "error: invalid request"}

    shipper_id = request.get("shipper_id", request.get("shipper"))

    # Existence flags
    if request.get("shipper_exists") is False or \
            request.get("shipper_found") is False:
        return {"status": "rejected",
                "response": "rejectedInvalidRequest",
                "reason": "unknown shipper"}

    weight_kg = request.get("weight_kg", request.get("weight"))
    distance_km = request.get("distance_km", request.get("distance"))
    declared_value = request.get("declared_value", request.get("value", 0))

    risk_index, screening_down = _interpret_screening(request)
    store_down = _interpret_store(request)

    api = QuoteAPI(
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(risk_index=risk_index,
                                           unavailable=screening_down),
        notification_service=NotificationService(),
        quote_store=QuoteStore(unavailable=store_down),
    )

    return api.request_quote(shipper_id, weight_kg, distance_km,
                             declared_value)