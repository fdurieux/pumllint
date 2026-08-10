import math


# ---------------------------------------------------------------------------
# Decision-table constants (DT-S, DT-V, DT-P)
# ---------------------------------------------------------------------------
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

_ERROR_WORDS = {"error", "unavailable", "down", "outage", "fail", "failed", "timeout"}


# ---------------------------------------------------------------------------
# Internal exceptions modelling failure paths
# ---------------------------------------------------------------------------
class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


# ---------------------------------------------------------------------------
# External system: denied-party screening provider
# ---------------------------------------------------------------------------
class ScreeningService:
    def __init__(self, ctx=None):
        self._ctx = ctx or {}

    def screen(self, shipper_id):
        ctx = self._ctx
        status = ctx.get("screening_status")
        result = ctx.get("screening_result")

        for candidate in (status, result):
            if isinstance(candidate, str) and candidate.strip().lower() in _ERROR_WORDS:
                raise ScreeningUnavailableError("screening unavailable")

        # Determine risk index from available keys.
        for key in ("risk_index", "screening_result", "screening_status"):
            val = ctx.get(key)
            if isinstance(val, bool):
                continue
            if isinstance(val, (int, float)):
                return int(val)
            if isinstance(val, str):
                s = val.strip()
                try:
                    return int(float(s))
                except ValueError:
                    continue
        # Sensible default: a clean, accept-band shipper.
        return 0


# ---------------------------------------------------------------------------
# Pricing / tariff computation (DT-P)
# ---------------------------------------------------------------------------
class TariffEngine:
    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km  # P1
        if weight_kg > HEAVY_THRESHOLD:                 # P2
            result += HEAVY_SURCHARGE
        if distance_km >= LONGHAUL_THRESHOLD:           # P3 (after P2)
            result *= LONGHAUL_MULTIPLIER
        return round(result, 2)                         # P4


# ---------------------------------------------------------------------------
# Quote store
# ---------------------------------------------------------------------------
class QuoteStore:
    def __init__(self, ctx=None):
        self._ctx = ctx or {}
        self._seq = 0
        self._quotes = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        status = self._ctx.get("store_status")
        result = self._ctx.get("store_result")
        for candidate in (status, result):
            if isinstance(candidate, str) and candidate.strip().lower() in _ERROR_WORDS:
                raise StoreUnavailableError("store unavailable")

        self._seq += 1
        quote_id = "Q-{:06d}".format(self._seq)
        self._quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
        }
        return quote_id

    def update_quote(self, quote_id, status, price=None):
        record = self._quotes.get(quote_id, {})
        record["status"] = status
        if price is not None:
            record["price"] = price
        self._quotes[quote_id] = record
        return record


# ---------------------------------------------------------------------------
# External system: notification provider (fire-and-forget)
# ---------------------------------------------------------------------------
class NotificationService:
    def __init__(self, ctx=None):
        self._ctx = ctx or {}

    def _fails(self):
        status = self._ctx.get("notification_status")
        result = self._ctx.get("notification_result")
        for candidate in (status, result):
            if isinstance(candidate, str) and candidate.strip().lower() in _ERROR_WORDS:
                return True
        return False

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        if self._fails():
            raise RuntimeError("notification delivery failed")
        return "delivered"

    def send_refusal_notice(self, shipper_id, quote_id):
        if self._fails():
            raise RuntimeError("notification delivery failed")
        return "delivered"


# ---------------------------------------------------------------------------
# QuoteAPI — orchestrates the quotation flow
# ---------------------------------------------------------------------------
class QuoteAPI:
    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    # -- DT-V validation ---------------------------------------------------
    @staticmethod
    def _is_number(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def _valid(self, req):
        sid = req.get("shipper_id")
        if not isinstance(sid, str) or sid.strip() == "":
            return False
        w = req.get("weight_kg")
        if not self._is_number(w) or not (WEIGHT_MIN <= w <= WEIGHT_MAX):
            return False
        d = req.get("distance_km")
        if not self._is_number(d) or not (DISTANCE_MIN <= d <= DISTANCE_MAX):
            return False
        v = req.get("declared_value")
        if not self._is_number(v) or not (VALUE_MIN <= v <= VALUE_MAX):
            return False
        return True

    # -- main flow ---------------------------------------------------------
    def request_quote(self, req):
        # 1. Validate (DT-V)
        if not self._valid(req):
            return {"status": "rejected: invalid_request"}

        shipper_id = req["shipper_id"]
        weight_kg = req["weight_kg"]
        distance_km = req["distance_km"]
        declared_value = req["declared_value"]

        # 2. Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # 3. Screen
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage: price, hold, do NOT notify (DT-S note 5)
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4/5/6. Apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                pass  # fire-and-forget (DT-S note 4)
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # risk_index >= REFUSE_MIN
        self.quote_store.update_quote(quote_id, "refused_screening")
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            pass  # fire-and-forget
        return {"status": "refused_screening", "quote_id": quote_id}


# ---------------------------------------------------------------------------
# Module-level entry point
# ---------------------------------------------------------------------------
def handle(request: dict) -> dict:
    request = request or {}
    quote_store = QuoteStore(request)
    screening_service = ScreeningService(request)
    tariff_engine = TariffEngine()
    notification_service = NotificationService(request)

    api = QuoteAPI(quote_store, screening_service, tariff_engine, notification_service)
    return api.request_quote(request)