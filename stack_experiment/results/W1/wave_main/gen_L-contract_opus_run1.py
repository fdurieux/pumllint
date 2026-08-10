import math


class InvalidRequestError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


# ---- Tuning constants (from decision tables DT-V and DT-S) ----
WEIGHT_MIN = 10.0
WEIGHT_MAX = 26000.0
DISTANCE_MIN = 1.0
DISTANCE_MAX = 3000.0

RATE_PER_KG = 0.87
RATE_PER_KM = 1.13

ACCEPT_MAX = 30.0
REVIEW_MIN = 30.0
REVIEW_MAX = 70.0
REFUSE_MIN = 70.0


# ---- External systems (outside the boundary) ----
class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, risk_index=12.0, available=True):
        self._risk_index = risk_index
        self._available = available

    def screen(self, shipper_id):
        if not self._available:
            raise ScreeningUnavailableError("screening service unavailable")
        return self._risk_index


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, deliver=True):
        self._deliver = deliver

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        # Fire-and-forget: a delivery failure never changes the response.
        return bool(self._deliver)

    def send_refusal_notice(self, shipper_id, quote_id):
        return bool(self._deliver)


# ---- Internal containers ----
class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self._available = available
        self._records = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._available:
            raise StoreUnavailableError("quote store unavailable")
        self._seq += 1
        quote_id = "Q-%04d" % self._seq
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        rec = self._records.get(quote_id)
        if rec is None:
            rec = {"shipper_id": None}
            self._records[quote_id] = rec
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        return quote_id


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff rules."""

    def price(self, weight_kg, distance_km):
        amount = RATE_PER_KG * float(weight_kg) + RATE_PER_KM * float(distance_km)
        return round(amount, 2)


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            raise InvalidRequestError("missing shipper id")
        try:
            w = float(weight_kg)
            d = float(distance_km)
            v = float(declared_value)
        except (TypeError, ValueError):
            raise InvalidRequestError("non-numeric field")
        if not (WEIGHT_MIN <= w <= WEIGHT_MAX):
            raise InvalidRequestError("weight out of bounds")
        if not (DISTANCE_MIN <= d <= DISTANCE_MAX):
            raise InvalidRequestError("distance out of bounds")
        if v <= 0:
            raise InvalidRequestError("declared value out of bounds")

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # 1. Validate (DT-V)
        self._validate(shipper_id, weight_kg, distance_km, declared_value)

        # 2. Store draft — on storage failure nothing else runs (DT-S note 3)
        quote_id = self.quote_store.store_draft(
            shipper_id, weight_kg, distance_km, declared_value
        )

        # 3. Screen
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Outage does not fail the quote: price, hold, no notification (note 5)
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        risk = float(risk_index)

        # 4. Decide (DT-S)
        if risk <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            # Fire-and-forget notification (note 4)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount
            )
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": False,
            }
        elif risk >= REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            # Refusal IS notified; pricing never runs (note 2)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
                "price": None,
            }
        else:
            # Review band: no pricing, no notification (note 1)
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
                "price": None,
            }


# ---- Helpers for handle() ----
_ERROR_WORDS = {"error", "unavailable", "down", "failed", "failure", "timeout"}
_ACCEPT_WORDS = {"approved", "accepted", "clear", "clean", "pass"}
_REFUSE_WORDS = {"declined", "refused", "denied", "reject", "rejected"}
_REVIEW_WORDS = {"review", "hold", "manual"}


def _first(request, *keys, default=None):
    for k in keys:
        if k in request and request[k] is not None:
            return request[k]
    return default


def _screening_config(request):
    val = _first(
        request,
        "screening_result",
        "screening_status",
        "screening",
        "risk_index",
        "riskIndex",
    )
    if val is None:
        return (True, 12.0)
    if isinstance(val, (int, float)):
        return (True, float(val))
    s = str(val).strip().lower()
    if s in _ERROR_WORDS:
        return (False, None)
    if s in _ACCEPT_WORDS:
        return (True, 0.0)
    if s in _REFUSE_WORDS:
        return (True, 100.0)
    if s in _REVIEW_WORDS:
        return (True, 50.0)
    try:
        return (True, float(s))
    except ValueError:
        return (True, 12.0)


def _store_available(request):
    val = _first(request, "store_status", "store_result", "quote_store_status")
    if val is None:
        exists = _first(request, "store_exists", "store_found")
        if exists is False:
            return False
        return True
    s = str(val).strip().lower()
    if s in _ERROR_WORDS:
        return False
    return True


def _notification_ok(request):
    val = _first(request, "notification_status", "notification_result", "notify_status")
    if val is None:
        return True
    s = str(val).strip().lower()
    if s in _ERROR_WORDS:
        return False
    return True


def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = _first(
        request, "shipper_id", "shipperId", "shipper", default="unknown"
    )
    weight = _first(request, "weight_kg", "weightKg", "weight")
    distance = _first(request, "distance_km", "distanceKm", "distance")
    declared = _first(
        request, "declared_value", "declaredValue", "value", default=1.0
    )

    screening_available, risk = _screening_config(request)
    store_available = _store_available(request)
    notification_ok = _notification_ok(request)

    tariff_engine = TariffEngine()
    quote_store = QuoteStore(available=store_available)
    screening_service = ScreeningService(
        risk_index=risk, available=screening_available
    )
    notification_service = NotificationService(deliver=notification_ok)

    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)

    try:
        return api.request_quote(shipper_id, weight, distance, declared)
    except InvalidRequestError as e:
        return {"status": "rejected: invalid_request", "reason": str(e)}
    except StoreUnavailableError as e:
        return {"status": "error: store_unavailable", "reason": str(e)}
    except Exception as e:  # pragma: no cover
        return {"status": "error: %s" % type(e).__name__, "reason": str(e)}