def _to_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class ScreeningUnavailableError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, outcome=None, risk_index=None):
        if outcome in ("error", "unavailable", "down", "outage"):
            raise ScreeningUnavailableError("screening_unavailable")
        if risk_index is not None:
            return int(risk_index)
        # plausible default
        return 10


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        return "sent"

    def sendRefusalNotice(self, shipper_id, quote_id):
        return "sent"


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

    HEAVY_THRESHOLD = 1244
    HEAVY_SURCHARGE = 316.00
    LONGHAUL_THRESHOLD = 4912
    LONGHAUL_MULTIPLIER = 1.19

    def price(self, weight_kg, distance_km):
        total = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > self.HEAVY_THRESHOLD:
            total += self.HEAVY_SURCHARGE
        if distance_km >= self.LONGHAUL_THRESHOLD:
            total *= self.LONGHAUL_MULTIPLIER
        return round(total, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._quotes = {}
        self._counter = 0

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value, ok=True):
        if not ok:
            raise StoreUnavailableError("store_unavailable")
        self._counter += 1
        quote_id = "Q%05d" % self._counter
        self._quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def updateQuote(self, quote_id, status, price=None):
        record = self._quotes.get(quote_id)
        if record is None:
            record = {}
            self._quotes[quote_id] = record
        record["status"] = status
        if price is not None:
            record["price"] = price
        return quote_id


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def __init__(self, store=None, screening=None, tariff=None, notifier=None):
        self.store = store or QuoteStore()
        self.screening = screening or ScreeningService()
        self.tariff = tariff or TariffEngine()
        self.notifier = notifier or NotificationService()

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id or not isinstance(shipper_id, str):
            return False
        w = _to_number(weight_kg)
        if w is None or not (3 <= w <= 19400):
            return False
        d = _to_number(distance_km)
        if d is None or not (25 <= d <= 7150):
            return False
        v = _to_number(declared_value)
        if v is None or not (50 <= v <= 83000):
            return False
        return True

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value,
                     store_ok=True, screening_outcome=None, risk_index=None):
        # Step 1: validate (DT-V)
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # Step 2: store draft
        try:
            quote_id = self.store.storeDraft(
                shipper_id, weight_kg, distance_km, declared_value, ok=store_ok)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk = self.screening.screen(
                shipper_id, outcome=screening_outcome, risk_index=risk_index)
        except ScreeningUnavailableError:
            # screening outage: price anyway, hold unscreened, no notification
            price = self.tariff.price(weight_kg, distance_km)
            self.store.updateQuote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4-6: apply DT-S
        if risk <= self.ACCEPT_MAX:
            price = self.tariff.price(weight_kg, distance_km)
            self.store.updateQuote(quote_id, "quoted", price)
            self.notifier.sendQuoteDocument(shipper_id, quote_id, price)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif risk <= self.REVIEW_MAX:
            self.store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:
            self.store.updateQuote(quote_id, "refused_screening")
            self.notifier.sendRefusalNotice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def _extract_store_ok(request):
    for key in ("quote_store_result", "quote_store_status", "store_result",
                "store_status", "quote_store_exists"):
        if key in request:
            val = request[key]
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() in ("stored", "ok", "active", "available", "success")
    return True


def _extract_screening(request):
    """Return (outcome_word, risk_index)."""
    for key in ("screening_service_status", "screening_status",
                "screening_service_result", "screening_result", "screening"):
        if key in request:
            val = request[key]
            num = _to_number(val)
            if num is not None and not isinstance(val, bool):
                return None, int(num)
            if isinstance(val, str):
                low = val.lower()
                if low in ("error", "unavailable", "down", "outage"):
                    return low, None
    for key in ("risk_index", "risk", "score"):
        if key in request:
            num = _to_number(request[key])
            if num is not None:
                return None, int(num)
    return None, None


def handle(request: dict) -> dict:
    api = QuoteApi()

    shipper_id = request.get("shipper_id")
    if shipper_id is None and request.get("shipper_exists") is False:
        shipper_id = ""

    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    store_ok = _extract_store_ok(request)
    screening_outcome, risk_index = _extract_screening(request)

    try:
        return api.requestQuote(
            shipper_id, weight_kg, distance_km, declared_value,
            store_ok=store_ok,
            screening_outcome=screening_outcome,
            risk_index=risk_index,
        )
    except Exception as exc:  # pragma: no cover
        return {"status": "error: %s" % exc}