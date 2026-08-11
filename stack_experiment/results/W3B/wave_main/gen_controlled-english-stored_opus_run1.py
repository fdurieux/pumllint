import math


# ---------------------------------------------------------------------------
# Configuration constants (decision table DT-S thresholds, DT-V bounds)
# ---------------------------------------------------------------------------
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

WEIGHT_MIN = 1
WEIGHT_MAX = 26000
DISTANCE_MIN = 1
DISTANCE_MAX = 3000
VALUE_MIN = 0


# ---------------------------------------------------------------------------
# External systems (outside the CargoQuote boundary)
# ---------------------------------------------------------------------------
class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, result="assessed", risk_index=10):
        self._result = result
        self._risk_index = risk_index

    def screen(self, shipper_id):
        # Returns a single value: the shipper risk index, or an error marker.
        if self._result in ("error", "unavailable", "screeningUnavailableError"):
            return "screeningUnavailableError"
        return self._risk_index


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, result="sent"):
        self._result = result

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        # Fire-and-forget; delivery outcome never changes the caller's response.
        return "dispatched"

    def sendRefusalNotice(self, shipper_id, quote_id):
        return "dispatched"


# ---------------------------------------------------------------------------
# Internal containers
# ---------------------------------------------------------------------------
class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG_KM = 0.0005

    def price(self, weight_kg, distance_km):
        # Returns a single value: the price amount.
        amount = self.BASE_FEE + (weight_kg * distance_km * self.RATE_PER_KG_KM)
        return round(amount, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self._available = available
        self._seq = 0
        self._records = {}

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value):
        # Returns a single value: the quoteId, or a storage error marker.
        if not self._available:
            return "storeUnavailableError"
        self._seq += 1
        quote_id = "Q%05d" % self._seq
        self._records[quote_id] = {
            "shipperId": shipper_id,
            "weightKg": weight_kg,
            "distanceKm": distance_km,
            "declaredValue": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def updateQuote(self, quote_id, status, price_amount=None):
        # Returns a single value: a confirmation of the updated quote.
        rec = self._records.get(quote_id)
        if rec is None:
            return "updateFailed"
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        return "updated:" + quote_id


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, store, screening, tariff, notification):
        self._store = store
        self._screening = screening
        self._tariff = tariff
        self._notification = notification

    def _valid(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
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
        if v < VALUE_MIN:
            return False
        return True

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Step 2: validation (DT-V)
        if not self._valid(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # Step 2/3: store draft
        quote_id = self._store.storeDraft(
            shipper_id, weight_kg, distance_km, declared_value
        )
        if quote_id == "storeUnavailableError":
            # DT-S note 3: nothing else runs on storage failure.
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        risk_index = self._screening.screen(shipper_id)

        # Step 4d: screening outage -> price, hold, no notification (DT-S note 5)
        if risk_index == "screeningUnavailableError":
            price_amount = self._tariff.price(weight_kg, distance_km)
            self._store.updateQuote(quote_id, "statusHeldUnscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quoteId": quote_id,
                "price": price_amount,
            }

        # Step 4a: accept -> price, quote, notify (fire-and-forget)
        if risk_index <= ACCEPT_MAX:
            price_amount = self._tariff.price(weight_kg, distance_km)
            self._store.updateQuote(quote_id, "statusQuoted", price_amount)
            self._notification.sendQuoteDocument(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quoteId": quote_id,
                "price": price_amount,
            }

        # Step 4b: review hold -> no pricing, no notification (DT-S note 1)
        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self._store.updateQuote(quote_id, "statusReviewHold")
            return {"status": "review_hold", "quoteId": quote_id}

        # Step 4c: refuse -> notify, no pricing (DT-S note 2)
        if risk_index >= REFUSE_MIN:
            self._store.updateQuote(quote_id, "statusRefusedScreening")
            self._notification.sendRefusalNotice(shipper_id, quote_id)
            return {"status": "refused", "quoteId": quote_id}

        # Fallback (should be unreachable given contiguous bands)
        return {"status": "error: unclassified_risk"}


# ---------------------------------------------------------------------------
# Module-level end-to-end entry point
# ---------------------------------------------------------------------------
def _resolve_risk(request):
    for key in ("screening_result", "screening_status"):
        if key in request:
            val = request[key]
            if isinstance(val, (int, float)):
                return ("assessed", val)
            sval = str(val).lower()
            if sval in ("error", "unavailable", "screeningunavailableerror", "down"):
                return ("error", 0)
            mapping = {
                "approved": 5,
                "accept": 5,
                "clear": 5,
                "review": 50,
                "hold": 50,
                "declined": 90,
                "refuse": 90,
                "denied": 90,
            }
            if sval in mapping:
                return ("assessed", mapping[sval])
            try:
                return ("assessed", float(sval))
            except ValueError:
                return ("assessed", 10)
    return ("assessed", 10)


def _store_available(request):
    for key in ("store_result", "store_status"):
        if key in request:
            sval = str(request[key]).lower()
            if sval in ("error", "unavailable", "down", "storeunavailableerror"):
                return False
            return True
    if request.get("store_exists") is False or request.get("store_found") is False:
        return False
    return True


def handle(request: dict) -> dict:
    if not isinstance(request, dict):
        return {"status": "error: bad_request"}

    shipper_id = request.get("shipper_id") or request.get("shipperId")
    if request.get("shipper_exists") is False or request.get("shipper_found") is False:
        shipper_id = None

    weight_kg = request.get("weight_kg", request.get("weightKg"))
    distance_km = request.get("distance_km", request.get("distanceKm"))
    declared_value = request.get(
        "declared_value", request.get("declaredValue", 0)
    )

    store_available = _store_available(request)
    screening_result, risk_index = _resolve_risk(request)
    notif_result = request.get("notification_result", "sent")

    store = QuoteStore(available=store_available)
    screening = ScreeningService(result=screening_result, risk_index=risk_index)
    tariff = TariffEngine()
    notification = NotificationService(result=notif_result)

    api = QuoteApi(store, screening, tariff, notification)
    return api.requestQuote(shipper_id, weight_kg, distance_km, declared_value)