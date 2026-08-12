import uuid

# ---- Decision table constants ----
# DT-V (validation bounds)
WEIGHT_MIN, WEIGHT_MAX = 1.0, 26000.0
DISTANCE_MIN, DISTANCE_MAX = 1.0, 4000.0
VALUE_MIN, VALUE_MAX = 0.0, 5_000_000.0

# DT-S (screening bands; higher risk is worse)
ACCEPT_MAX = 30
REVIEW_MIN, REVIEW_MAX = 31, 69
REFUSE_MIN = 70

# DT-P (pricing)
BASE_FEE = 25.0
RATE_PER_KG = 0.05
RATE_PER_KM = 0.10


class ScreeningUnavailableError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


# ---- External system: Screening Service ----
class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, outcome=None):
        self._outcome = outcome

    def screen(self, shipper_id):
        o = self._outcome
        if o is None:
            return 10
        if isinstance(o, (int, float)) and not isinstance(o, bool):
            return int(o)
        w = str(o).strip().lower()
        if w in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailableError("screening service unavailable")
        if w in ("approved", "active", "accept", "clear", "ok", "pass"):
            return 10
        if w in ("review", "hold", "assessed", "manual"):
            return 50
        if w in ("declined", "refused", "refuse", "denied", "blocked"):
            return 90
        try:
            return int(w)
        except ValueError:
            return 10


# ---- External system: Notification Service ----
class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, outcome=None):
        self._outcome = outcome

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        if str(self._outcome).strip().lower() in ("error", "failed", "unavailable"):
            raise RuntimeError("notification delivery failed")
        return "delivered"

    def sendRefusalNotice(self, shipper_id, quote_id):
        if str(self._outcome).strip().lower() in ("error", "failed", "unavailable"):
            raise RuntimeError("notification delivery failed")
        return "delivered"


# ---- Container: Quote Store ----
class QuoteStore:
    """Stores quote requests and their lifecycle status (PostgreSQL 16)."""

    def __init__(self, outcome=None):
        self._outcome = outcome
        self._records = {}

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value):
        if str(self._outcome).strip().lower() in ("error", "unavailable", "down"):
            raise StoreUnavailableError("quote store unavailable")
        quote_id = "q-" + uuid.uuid4().hex[:12]
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def updateQuote(self, quote_id, status, price_amount=None):
        rec = self._records.get(quote_id)
        if rec is None:
            rec = {}
            self._records[quote_id] = rec
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        return quote_id


# ---- Container: Tariff Engine ----
class TariffEngine:
    """Computes the freight price from weight and distance per the published tariff."""

    def price(self, weight_kg, distance_km):
        amount = BASE_FEE + weight_kg * RATE_PER_KG + distance_km * RATE_PER_KM
        return round(amount, 2)


# ---- Container: Quote API (orchestrator) ----
class QuoteApi:
    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or not shipper_id.strip():
            return False
        for v in (weight_kg, distance_km, declared_value):
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                return False
        if not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            return False
        if not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            return False
        if not (VALUE_MIN <= declared_value <= VALUE_MAX):
            return False
        return True

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value):
        # 1. Validate (DT-V)
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # 2. Store draft
        try:
            quote_id = self.quote_store.storeDraft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # 3. Screen
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage: price anyway, hold unscreened, no notification
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # 4-7. Apply DT-S decision
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price_amount)
            self._notify_quote(shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # risk_index >= REFUSE_MIN
        self.quote_store.updateQuote(quote_id, "refused_screening")
        self._notify_refusal(shipper_id, quote_id)
        return {"status": "refused_screening", "quote_id": quote_id}

    # Notifications are fire-and-forget: failures never change the response.
    def _notify_quote(self, shipper_id, quote_id, price_amount):
        try:
            self.notification_service.sendQuoteDocument(shipper_id, quote_id, price_amount)
        except Exception:
            pass

    def _notify_refusal(self, shipper_id, quote_id):
        try:
            self.notification_service.sendRefusalNotice(shipper_id, quote_id)
        except Exception:
            pass


# ---- Module-level end-to-end entry point ----
def handle(request: dict) -> dict:
    request = request or {}

    def _first(*keys):
        for k in keys:
            if k in request and request[k] is not None:
                return request[k]
        return None

    screening_outcome = _first("screening_result", "screening_status", "screening")
    store_outcome = _first("store_result", "store_status", "quote_store_result")
    notification_outcome = _first("notification_result", "notification_status", "notification")

    screening_service = ScreeningService(screening_outcome)
    notification_service = NotificationService(notification_outcome)
    quote_store = QuoteStore(store_outcome)
    tariff_engine = TariffEngine()

    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)

    shipper_id = _first("shipper_id", "shipperId")
    weight_kg = _first("weight_kg", "weightKg")
    distance_km = _first("distance_km", "distanceKm")
    declared_value = _first("declared_value", "declaredValue")

    return api.requestQuote(shipper_id, weight_kg, distance_km, declared_value)