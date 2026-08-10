def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# --- Constants (DT-S, DT-V, DT-P) ---
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


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, request=None):
        self._request = request or {}

    def screen(self, shipper_id):
        req = self._request
        status = req.get("screening_status", req.get("screening_result"))
        if isinstance(status, str) and status.lower() in (
            "error",
            "unavailable",
            "outage",
            "down",
        ):
            raise ScreeningUnavailableError("screening service unavailable")
        # explicit risk index keys
        for key in ("risk_index", "screening_result", "screening_status"):
            v = req.get(key)
            if _is_number(v):
                return int(v)
        # default: an accept-band index
        return 0


class TariffEngine:
    """Computes the freight price per DT-P."""

    def price(self, weight_kg, distance_km):
        base = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > HEAVY_THRESHOLD:
            base += HEAVY_SURCHARGE
        if distance_km >= LONGHAUL_THRESHOLD:
            base *= LONGHAUL_MULTIPLIER
        return round(base, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, request=None):
        self._request = request or {}
        self._counter = 0
        self._records = {}

    def _store_failed(self):
        req = self._request
        status = req.get("store_status", req.get("quote_store_result"))
        if isinstance(status, str) and status.lower() in (
            "error",
            "unavailable",
            "outage",
            "down",
        ):
            return True
        return False

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if self._store_failed():
            raise StoreUnavailableError("quote store unavailable")
        self._counter += 1
        quote_id = "Q-{:06d}".format(self._counter)
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price=None):
        rec = self._records.get(quote_id, {})
        rec["status"] = status
        if price is not None:
            rec["price"] = price
        self._records[quote_id] = rec
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, request=None):
        self._request = request or {}

    def _delivery_failed(self):
        req = self._request
        status = req.get("notification_status", req.get("notification_result"))
        if isinstance(status, str) and status.lower() in (
            "error",
            "unavailable",
            "failed",
            "fail",
        ):
            return True
        return False

    def send_quote_document(self, shipper_id, quote_id, price):
        if self._delivery_failed():
            raise RuntimeError("notification delivery failed")
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        if self._delivery_failed():
            raise RuntimeError("notification delivery failed")
        return "sent"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    def __init__(self, store, screening, tariff, notifier):
        self._store = store
        self._screening = screening
        self._tariff = tariff
        self._notifier = notifier

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False
        weight = request.get("weight_kg")
        if not _is_number(weight) or not (WEIGHT_MIN <= weight <= WEIGHT_MAX):
            return False
        distance = request.get("distance_km")
        if not _is_number(distance) or not (DISTANCE_MIN <= distance <= DISTANCE_MAX):
            return False
        value = request.get("declared_value")
        if not _is_number(value) or not (VALUE_MIN <= value <= VALUE_MAX):
            return False
        return True

    def request_quote(self, request):
        # 1. Validate (DT-V)
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]

        # 2. Store draft
        try:
            quote_id = self._store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # 3. Screening
        try:
            risk_index = self._screening.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage: price anyway, hold, no notify (DT-S note 5)
            price = self._tariff.price(weight_kg, distance_km)
            self._store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4/5/6. Apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            price = self._tariff.price(weight_kg, distance_km)
            self._store.update_quote(quote_id, "quoted", price)
            try:
                self._notifier.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                pass  # fire-and-forget (DT-S note 4)
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self._store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        else:  # risk_index >= REFUSE_MIN
            self._store.update_quote(quote_id, "refused_screening")
            try:
                self._notifier.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass  # fire-and-forget
            return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    try:
        api = QuoteApi(
            store=QuoteStore(request),
            screening=ScreeningService(request),
            tariff=TariffEngine(),
            notifier=NotificationService(request),
        )
        return api.request_quote(request)
    except Exception as exc:
        return {"status": "error: {}".format(exc)}