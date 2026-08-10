ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000

HEAVY_THRESHOLD = 1244
HEAVY_SURCHARGE = 316.00
LONGHAUL_THRESHOLD = 4912
LONGHAUL_MULTIPLIER = 1.19


class ScreeningError(Exception):
    pass


class StoreError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider (outside system boundary)."""

    def screen(self, shipper_id, forced=None):
        if forced == "unavailable" or forced == "error":
            raise ScreeningError("screening_unavailable")
        if forced is not None:
            return int(forced)
        return 12

    def risk_index(self, shipper_id):
        return 12


class TariffEngine:
    """Computes freight price per DT-P."""

    def price(self, weight_kg, distance_km):
        base = 0.87 * weight_kg + 1.13 * distance_km
        total = base
        if weight_kg > HEAVY_THRESHOLD:
            total += HEAVY_SURCHARGE
        if distance_km >= LONGHAUL_THRESHOLD:
            total *= LONGHAUL_MULTIPLIER
        return round(total, 2)


class QuoteStore:
    """Stores quote requests and lifecycle status (ContainerDb)."""

    def __init__(self):
        self._quotes = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, available=True):
        if not available:
            raise StoreError("store_unavailable")
        self._seq += 1
        quote_id = "Q-{:06d}".format(self._seq)
        self._quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price=None):
        rec = self._quotes.get(quote_id)
        if rec is None:
            raise StoreError("quote_not_found")
        rec["status"] = status
        if price is not None:
            rec["price"] = price
        return rec


class NotificationService:
    """External messaging provider (outside system boundary)."""

    def __init__(self):
        self.sent = []

    def send_quote_document(self, shipper_id, quote_id, price, fail=False):
        # fire-and-forget; delivery failure never propagates
        if fail:
            return False
        self.sent.append(("quote_document", shipper_id, quote_id, price))
        return True

    def send_refusal_notice(self, shipper_id, quote_id, fail=False):
        if fail:
            return False
        self.sent.append(("refusal_notice", shipper_id, quote_id))
        return True


class QuoteApi:
    """Receives quote requests, orchestrates screening and pricing."""

    def __init__(self, tariff_engine=None, quote_store=None,
                 screening_service=None, notification_service=None):
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    def _validate(self, req):
        shipper_id = req.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False
        for key, lo, hi in (
            ("weight_kg", WEIGHT_MIN, WEIGHT_MAX),
            ("distance_km", DISTANCE_MIN, DISTANCE_MAX),
            ("declared_value", VALUE_MIN, VALUE_MAX),
        ):
            v = req.get(key)
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                return False
            if v < lo or v > hi:
                return False
        return True

    def request_quote(self, req, store_available=True,
                      screening_forced=None, notify_fail=False):
        # Step 1: validate
        if not self._validate(req):
            return {"status": "rejected: invalid_request"}

        shipper_id = req["shipper_id"]
        weight_kg = req["weight_kg"]
        distance_km = req["distance_km"]
        declared_value = req["declared_value"]

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value,
                available=store_available)
        except StoreError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id, forced=screening_forced)
        except ScreeningError:
            # screening outage: price anyway, hold, no notification
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4-7: apply DT-S
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price, fail=notify_fail)
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # risk_index >= REFUSE_MIN
        self.quote_store.update_quote(quote_id, "refused_screening")
        self.notification_service.send_refusal_notice(
            shipper_id, quote_id, fail=notify_fail)
        return {"status": "refused_screening", "quote_id": quote_id}


class Shipper:
    """A logistics customer requesting a price quote."""

    def __init__(self, quote_api):
        self.quote_api = quote_api

    def request_quote(self, req, **kwargs):
        return self.quote_api.request_quote(req, **kwargs)


def _coerce_screening_forced(request):
    # Determine screening outcome from request keys.
    for key in ("screening_status", "screening_result", "screening_service_status",
                "screening_service_result"):
        if key in request and request[key] is not None:
            val = request[key]
            if isinstance(val, str):
                low = val.lower()
                if low in ("unavailable", "error", "down", "outage"):
                    return "unavailable"
                try:
                    return int(float(val))
                except ValueError:
                    return None
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                return int(val)
    if "risk_index" in request and request["risk_index"] is not None:
        return int(request["risk_index"])
    return None


def _store_available(request):
    for key in ("quote_store_status", "quote_store_result", "store_status",
                "store_result"):
        if key in request and request[key] is not None:
            val = request[key]
            if isinstance(val, str) and val.lower() in (
                    "unavailable", "error", "down", "outage"):
                return False
    if request.get("quote_store_exists") is False:
        return False
    if request.get("store_available") is False:
        return False
    return True


def _notify_fail(request):
    for key in ("notification_status", "notification_result",
                "notification_service_status", "notification_service_result"):
        if key in request and request[key] is not None:
            val = request[key]
            if isinstance(val, str) and val.lower() in (
                    "error", "failed", "failure", "undelivered", "unavailable"):
                return True
    return False


def handle(request: dict) -> dict:
    api = QuoteApi()
    req = {
        "shipper_id": request.get("shipper_id"),
        "weight_kg": request.get("weight_kg"),
        "distance_km": request.get("distance_km"),
        "declared_value": request.get("declared_value"),
    }
    store_available = _store_available(request)
    screening_forced = _coerce_screening_forced(request)
    notify_fail = _notify_fail(request)

    return api.request_quote(
        req,
        store_available=store_available,
        screening_forced=screening_forced,
        notify_fail=notify_fail,
    )