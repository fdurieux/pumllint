def _to_number(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, outcome=None):
        # outcome may carry an explicit risk index or an 'error'/outage signal.
        if outcome is not None:
            if isinstance(outcome, str):
                if outcome.strip().lower() in ("error", "unavailable", "outage", "down"):
                    raise RuntimeError("screening_unavailable")
                n = _to_number(outcome)
                if n is not None:
                    return int(n)
            else:
                n = _to_number(outcome)
                if n is not None:
                    return int(n)
        return 0


class TariffEngine:
    """Computes the freight price per DT-P."""

    def price(self, weight_kg, distance_km):
        base = 0.87 * weight_kg + 1.13 * distance_km
        total = base
        if weight_kg > 1244:
            total += 316.00
        if distance_km >= 4912:
            total *= 1.19
        return round(total, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._counter = 0
        self._records = {}

    def store_draft(self, request, ok=True):
        if not ok:
            raise RuntimeError("store_unavailable")
        self._counter += 1
        quote_id = "Q-{:06d}".format(self._counter)
        self._records[quote_id] = {"request": dict(request), "status": "draft"}
        return quote_id

    def update_status(self, quote_id, status):
        if quote_id in self._records:
            self._records[quote_id]["status"] = status
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send(self, shipper_id, kind, ok=True):
        if not ok:
            raise RuntimeError("notification_failed")
        return "delivered"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def __init__(self, store=None, screening=None, tariff=None, notification=None):
        self.store = store or QuoteStore()
        self.screening = screening or ScreeningService()
        self.tariff = tariff or TariffEngine()
        self.notification = notification or NotificationService()

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False
        weight = _to_number(request.get("weight_kg"))
        if weight is None or not (3 <= weight <= 19400):
            return False
        distance = _to_number(request.get("distance_km"))
        if distance is None or not (25 <= distance <= 7150):
            return False
        value = _to_number(request.get("declared_value"))
        if value is None or not (50 <= value <= 83000):
            return False
        return True

    def request_quote(self, request):
        # 1. Validate
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        weight = _to_number(request.get("weight_kg"))
        distance = _to_number(request.get("distance_km"))
        shipper_id = request.get("shipper_id")

        # 2. Store draft
        store_ok = _store_ok(request)
        try:
            quote_id = self.store.store_draft(request, ok=store_ok)
        except RuntimeError:
            return {"status": "error: store_unavailable"}

        # 3. Screening
        screening_outcome = _screening_outcome(request)
        try:
            risk_index = self.screening.screen(shipper_id, screening_outcome)
        except RuntimeError:
            # Screening outage: price anyway, hold unscreened, no notification.
            price = self.tariff.price(weight, distance)
            self.store.update_status(quote_id, "held_unscreened")
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4. Apply screening decision (DT-S)
        if risk_index <= self.ACCEPT_MAX:
            self.store.update_status(quote_id, "quoted")
            price = self.tariff.price(weight, distance)
            self._notify(shipper_id, "quote_document", request)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif risk_index <= self.REVIEW_MAX:
            self.store.update_status(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:
            self.store.update_status(quote_id, "refused_screening")
            self._notify(shipper_id, "refusal_notice", request)
            return {"status": "refused_screening", "quote_id": quote_id}

    def _notify(self, shipper_id, kind, request):
        notify_ok = _notify_ok(request)
        try:
            self.notification.send(shipper_id, kind, ok=notify_ok)
        except RuntimeError:
            # Fire-and-forget: delivery failure never changes the outcome.
            pass


def _store_ok(request):
    for key in ("store_result", "store_status", "quote_store_result",
                "quote_store_status"):
        val = request.get(key)
        if isinstance(val, str) and val.strip().lower() in ("error", "unavailable", "down"):
            return False
    if request.get("store_exists") is False or request.get("store_found") is False:
        return False
    return True


def _screening_outcome(request):
    if "risk_index" in request:
        return request.get("risk_index")
    for key in ("screening_result", "screening_status",
                "screening_service_result", "screening_service_status"):
        if key in request:
            return request.get(key)
    return None


def _notify_ok(request):
    for key in ("notification_result", "notification_status",
                "notification_service_result", "notification_service_status"):
        val = request.get(key)
        if isinstance(val, str) and val.strip().lower() in ("error", "failed", "unavailable"):
            return False
    return True


def handle(request: dict) -> dict:
    api = QuoteApi()
    return api.request_quote(request)