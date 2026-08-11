def _to_camel(alias):
    return "".join(p.capitalize() for p in alias.split("_"))


# ---- Decision table DT-V: validation bounds ----
WEIGHT_MIN = 0
WEIGHT_MAX = 30000
DISTANCE_MIN = 0
DISTANCE_MAX = 5000
VALUE_MIN = 0
VALUE_MAX = 10_000_000

# ---- Decision table DT-S: screening thresholds ----
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

# Sentinels
STORE_UNAVAILABLE = "storeUnavailableError"
SCREENING_UNAVAILABLE = "screeningUnavailableError"

# Quote statuses
STATUS_DRAFT = "draft"
STATUS_QUOTED = "quoted"
STATUS_REVIEW_HOLD = "review_hold"
STATUS_REFUSED_SCREENING = "refused_screening"
STATUS_HELD_UNSCREENED = "held_unscreened"


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, outcome="assessed"):
        self._outcome = outcome

    def screen(self, shipper_id):
        o = self._outcome
        if isinstance(o, (int, float)):
            return int(o)
        w = str(o).strip().lower()
        if w in ("error", "unavailable", "down", "timeout", "screening_unavailable"):
            return SCREENING_UNAVAILABLE
        if w in ("approved", "accept", "accepted", "low", "clear"):
            return 10
        if w in ("review", "hold", "manual", "medium"):
            return 50
        if w in ("declined", "refuse", "refused", "high", "denied"):
            return 90
        if w.lstrip("-").isdigit():
            return int(w)
        return 10


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff rules."""

    BASE = 25.0
    PER_KG = 0.15
    PER_KM = 0.40

    def price(self, weight_kg, distance_km):
        return round(self.BASE + self.PER_KG * weight_kg + self.PER_KM * distance_km, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self._available = available
        self._records = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._available:
            return STORE_UNAVAILABLE
        self._seq += 1
        quote_id = "Q%04d" % self._seq
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
        rec = self._records.get(quote_id)
        if rec is None:
            return "updateFailed"
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _valid(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            return False
        try:
            w = float(weight_kg)
            d = float(distance_km)
            v = float(declared_value)
        except (TypeError, ValueError):
            return False
        if not (WEIGHT_MIN < w <= WEIGHT_MAX):
            return False
        if not (DISTANCE_MIN < d <= DISTANCE_MAX):
            return False
        if not (VALUE_MIN < v <= VALUE_MAX):
            return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Step 2 - validation (DT-V)
        if not self._valid(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected_invalid_request",
                    "reason": "validation error"}

        # Step 2 - store draft
        quote_id = self.quote_store.store_draft(
            shipper_id, weight_kg, distance_km, declared_value)
        if quote_id == STORE_UNAVAILABLE:
            # Step 3 - storage failure: nothing else runs
            return {"status": "store_unavailable_error"}

        # Step 3 - screening
        risk_index = self.screening_service.screen(shipper_id)

        # Step 4d - screening failure
        if risk_index == SCREENING_UNAVAILABLE:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, STATUS_HELD_UNSCREENED, price_amount)
            return {"status": "held_unscreened",
                    "quote_id": quote_id,
                    "price": price_amount}

        # Step 4a - accept
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, STATUS_QUOTED, price_amount)
            # fire-and-forget notification
            try:
                self.notification_service.send_quote_document(
                    shipper_id, quote_id, price_amount)
            except Exception:
                pass
            return {"status": "quoted",
                    "quote_id": quote_id,
                    "price": price_amount,
                    "risk_index": risk_index}

        # Step 4b - review hold
        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, STATUS_REVIEW_HOLD)
            return {"status": "review_hold",
                    "quote_id": quote_id,
                    "risk_index": risk_index}

        # Step 4c - refuse
        # risk_index >= REFUSE_MIN
        self.quote_store.update_quote(quote_id, STATUS_REFUSED_SCREENING)
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            pass
        return {"status": "refused_screening",
                "quote_id": quote_id,
                "risk_index": risk_index}


def _store_available(request):
    val = request.get("store_result", request.get("store_status", "stored"))
    if request.get("store_exists") is False or request.get("store_found") is False:
        return False
    w = str(val).strip().lower()
    if w in ("error", "unavailable", "down", "store_unavailable", "failed"):
        return False
    return True


def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = request.get("shipper_id", request.get("shipperId"))
    if request.get("shipper_exists") is False or request.get("shipper_found") is False:
        shipper_id = None

    weight_kg = request.get("weight_kg", request.get("weightKg"))
    distance_km = request.get("distance_km", request.get("distanceKm"))
    declared_value = request.get("declared_value", request.get("declaredValue"))

    screening_outcome = request.get(
        "screening_result", request.get("screening_status", "assessed"))

    store = QuoteStore(available=_store_available(request))
    screening = ScreeningService(outcome=screening_outcome)
    tariff = TariffEngine()
    notification = NotificationService()

    api = QuoteApi(store, screening, tariff, notification)

    try:
        return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    except Exception as exc:  # pragma: no cover
        return {"status": "error: %s" % exc}