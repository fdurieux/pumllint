import threading


# Decision table DT-V — validation bounds
WEIGHT_MIN, WEIGHT_MAX = 1.0, 30000.0
DISTANCE_MIN, DISTANCE_MAX = 1.0, 5000.0
VALUE_MIN, VALUE_MAX = 0.01, 10_000_000.0

# Decision table DT-S — screening thresholds
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

# Status constants
STATUS_DRAFT = "draft"
STATUS_QUOTED = "quoted"
STATUS_REVIEW_HOLD = "review_hold"
STATUS_REFUSED_SCREENING = "refused_screening"
STATUS_HELD_UNSCREENED = "held_unscreened"

# Sentinel error values returned by collaborators
STORE_UNAVAILABLE_ERROR = "storeUnavailableError"
SCREENING_UNAVAILABLE_ERROR = "screeningUnavailableError"


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, outcome=None):
        # Returns a single value: the risk index (a number) or an error sentinel.
        if outcome is None:
            return 10
        if isinstance(outcome, (int, float)):
            return outcome
        word = str(outcome).lower()
        if word in ("error", "unavailable", "down", "timeout"):
            return SCREENING_UNAVAILABLE_ERROR
        if word in ("approved", "accept", "clear", "low", "active"):
            return 10
        if word in ("review", "assessed", "hold", "manual", "medium"):
            return 50
        if word in ("declined", "refuse", "refused", "denied", "high"):
            return 90
        # Try numeric string
        try:
            return float(word)
        except ValueError:
            return 10


class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG_KM = 0.0005

    def price(self, weight_kg, distance_km):
        # Returns a single value: the price amount.
        return round(self.BASE_FEE + self.RATE_PER_KG_KM * weight_kg * distance_km, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, outcome=None):
        # Returns a single value: the quoteId, or an error sentinel.
        if outcome is not None:
            word = str(outcome).lower()
            if word in ("error", "unavailable", "down", "fail", "failed"):
                return STORE_UNAVAILABLE_ERROR
        self._seq += 1
        quote_id = "Q%05d" % self._seq
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": STATUS_DRAFT,
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        # Returns a single value: a confirmation (the quoteId).
        rec = self._records.get(quote_id)
        if rec is not None:
            rec["status"] = status
            if price_amount is not None:
                rec["price"] = price_amount
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        # Fire-and-forget; returns a single value (a delivery ticket).
        return "sent:quote:%s" % quote_id

    def send_refusal_notice(self, shipper_id, quote_id):
        # Fire-and-forget; returns a single value (a delivery ticket).
        return "sent:refusal:%s" % quote_id


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, weight_kg, distance_km, declared_value):
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

    def _fire_and_forget(self, fn, *args):
        try:
            threading.Thread(target=fn, args=args, daemon=True).start()
        except Exception:
            pass

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value,
                      screening_outcome=None, store_outcome=None):
        # Step 2: validation
        if not self._validate(weight_kg, distance_km, declared_value):
            return {"status": "rejectedInvalidRequest"}

        # Step 2/3: store draft
        quote_id = self.quote_store.store_draft(
            shipper_id, weight_kg, distance_km, declared_value, outcome=store_outcome)
        if quote_id == STORE_UNAVAILABLE_ERROR:
            return {"status": "storeUnavailableError"}

        # Step 3: screening
        risk_index = self.screening_service.screen(shipper_id, outcome=screening_outcome)

        # Step 4d: screening failed
        if risk_index == SCREENING_UNAVAILABLE_ERROR:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, STATUS_HELD_UNSCREENED, price_amount)
            return {"status": "heldUnscreenedResponse",
                    "quote_id": quote_id, "price": price_amount}

        # Step 4a: accept
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, STATUS_QUOTED, price_amount)
            self._fire_and_forget(
                self.notification_service.send_quote_document,
                shipper_id, quote_id, price_amount)
            return {"status": "quotedResponse",
                    "quote_id": quote_id, "price": price_amount}

        # Step 4b: review
        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, STATUS_REVIEW_HOLD)
            return {"status": "reviewHoldResponse", "quote_id": quote_id}

        # Step 4c: refuse
        if risk_index >= REFUSE_MIN:
            self.quote_store.update_quote(quote_id, STATUS_REFUSED_SCREENING)
            self._fire_and_forget(
                self.notification_service.send_refusal_notice,
                shipper_id, quote_id)
            return {"status": "refusedScreeningResponse", "quote_id": quote_id}

        # Fallback (gap between bands) — treat as review hold
        self.quote_store.update_quote(quote_id, STATUS_REVIEW_HOLD)
        return {"status": "reviewHoldResponse", "quote_id": quote_id}


def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = request.get("shipper_id") or request.get("shipperId") or "unknown"
    weight_kg = request.get("weight_kg", request.get("weightKg"))
    distance_km = request.get("distance_km", request.get("distanceKm"))
    declared_value = request.get("declared_value", request.get("declaredValue"))

    # Existence flags — a missing shipper is an invalid request.
    if request.get("shipper_exists") is False or request.get("shipper_found") is False:
        return {"status": "rejectedInvalidRequest"}

    screening_outcome = request.get("screening_result", request.get("screening_status"))
    store_outcome = request.get("store_result", request.get("store_status"))

    api = QuoteApi(TariffEngine(), QuoteStore(), ScreeningService(), NotificationService())

    try:
        result = api.request_quote(
            shipper_id, weight_kg, distance_km, declared_value,
            screening_outcome=screening_outcome,
            store_outcome=store_outcome)
    except Exception as exc:
        return {"status": "error: %s" % exc}

    status = result.get("status")
    mapping = {
        "quotedResponse": "confirmed",
        "reviewHoldResponse": "review_hold",
        "refusedScreeningResponse": "rejected",
        "heldUnscreenedResponse": "held_unscreened",
        "rejectedInvalidRequest": "error: invalid_request",
        "storeUnavailableError": "error: store_unavailable",
    }
    out = dict(result)
    out["status"] = mapping.get(status, status)
    out["outcome"] = status
    return out