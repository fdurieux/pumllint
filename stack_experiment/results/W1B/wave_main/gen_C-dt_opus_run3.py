class ScreeningUnavailableError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


# --- Decision table constants (DT-V, DT-S, DT-P) ---

# DT-V validation bounds (mirrored from OpenAPI schema constraints)
WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000

# DT-S screening bands (risk index, higher is worse)
ACCEPT_MAX = 30
REVIEW_MIN, REVIEW_MAX = 31, 69
REFUSE_MIN = 70

# DT-P pricing coefficients
PRICE_BASE = 25.0
PRICE_PER_KG = 0.5
PRICE_PER_KM = 0.1


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, config=None):
        self._config = config or {}

    def screen(self, shipper_id):
        raw = self._config.get("screening_result",
                               self._config.get("screening_status"))
        if isinstance(raw, bool):
            raw = None
        if isinstance(raw, (int, float)):
            return int(raw)
        if isinstance(raw, str):
            low = raw.strip().lower()
            if low in ("error", "unavailable", "outage", "down", "timeout"):
                raise ScreeningUnavailableError("screening service unavailable")
            if low in ("accept", "accepted", "approved", "clear"):
                return ACCEPT_MAX
            if low in ("review", "hold"):
                return REVIEW_MIN
            if low in ("refuse", "refused", "declined", "denied"):
                return REFUSE_MIN
            try:
                return int(float(low))
            except ValueError:
                pass
        # default: clean shipper
        return 0


class TariffEngine:
    """Computes the freight price for a validated request (DT-P)."""

    def price(self, weight_kg, distance_km):
        return round(PRICE_BASE
                     + PRICE_PER_KG * float(weight_kg)
                     + PRICE_PER_KM * float(distance_km), 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, config=None):
        self._config = config or {}
        self._records = {}
        self._counter = 0

    def _store_ok(self):
        raw = self._config.get("store_result",
                               self._config.get("store_status"))
        if isinstance(raw, str):
            low = raw.strip().lower()
            if low in ("error", "unavailable", "down", "fail", "failed"):
                return False
        if self._config.get("store_exists") is False:
            return False
        return True

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._store_ok():
            raise StoreUnavailableError("quote store unavailable")
        self._counter += 1
        quote_id = "Q%05d" % self._counter
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

    def __init__(self, config=None):
        self._config = config or {}

    def _delivery_fails(self):
        raw = self._config.get("notification_result",
                               self._config.get("notification_status"))
        if isinstance(raw, str) and raw.strip().lower() in (
                "error", "unavailable", "fail", "failed", "undelivered"):
            return True
        return False

    def send_quote_document(self, shipper_id, quote_id, price):
        if self._delivery_fails():
            raise RuntimeError("notification delivery failure")
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        if self._delivery_fails():
            raise RuntimeError("notification delivery failure")
        return "sent"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening/pricing, returns outcome."""

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self._store = quote_store
        self._screening = screening_service
        self._tariff = tariff_engine
        self._notifier = notification_service

    def _valid(self, request):
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or len(shipper_id) < 1:
            return False
        if request.get("shipper_exists") is False:
            return False
        for key, lo, hi in (
            ("weight_kg", WEIGHT_MIN, WEIGHT_MAX),
            ("distance_km", DISTANCE_MIN, DISTANCE_MAX),
            ("declared_value", VALUE_MIN, VALUE_MAX),
        ):
            val = request.get(key)
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                return False
            if val < lo or val > hi:
                return False
        return True

    def request_quote(self, request):
        # Step 1: validate (DT-V)
        if not self._valid(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]

        # Step 2: store draft
        try:
            quote_id = self._store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self._screening.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage: price anyway, hold, no notification (DT-S note 5)
            price = self._tariff.price(weight_kg, distance_km)
            self._store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4-6: apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            price = self._tariff.price(weight_kg, distance_km)
            self._store.update_quote(quote_id, "quoted", price)
            try:
                self._notifier.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                pass  # fire-and-forget (DT-S note 4)
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self._store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # risk_index >= REFUSE_MIN
        self._store.update_quote(quote_id, "refused_screening")
        try:
            self._notifier.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            pass  # fire-and-forget (DT-S note 4)
        return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    request = request or {}
    store = QuoteStore(request)
    screening = ScreeningService(request)
    tariff = TariffEngine()
    notifier = NotificationService(request)
    api = QuoteApi(store, screening, tariff, notifier)
    try:
        return api.request_quote(request)
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error: %s" % type(exc).__name__}