class ScreeningUnavailableError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ValidationError(Exception):
    pass


# --- External systems (outside the boundary) ---

class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, risk_index=10.0, fail=False):
        self._risk_index = risk_index
        self._fail = fail

    def screen(self, shipper_id):
        if self._fail:
            raise ScreeningUnavailableError("screening service unavailable")
        return self._risk_index


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, fail=False):
        self._fail = fail

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        # fire-and-forget: failures are the provider's retry problem
        return "queued"

    def sendRefusalNotice(self, shipper_id, quote_id):
        return "queued"


# --- Internal containers ---

class QuoteStore:
    """Stores quote requests and their lifecycle status (PostgreSQL)."""

    def __init__(self, fail=False):
        self._fail = fail
        self._seq = 0
        self._records = {}

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value):
        if self._fail:
            raise StoreUnavailableError("quote store unavailable")
        self._seq += 1
        quote_id = "Q%05d" % self._seq
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
        rec = self._records.get(quote_id, {})
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        self._records[quote_id] = rec
        return quote_id


class TariffEngine:
    """Computes freight price from weight and distance per published tariff rules."""

    BASE = 25.0
    RATE_PER_KG = 0.35
    RATE_PER_KM = 0.90

    def price(self, weight_kg, distance_km):
        amount = self.BASE + weight_kg * self.RATE_PER_KG + distance_km * self.RATE_PER_KM
        return round(amount, 2)


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    # DT-V validation bounds
    WEIGHT_MIN = 1
    WEIGHT_MAX = 26000
    DISTANCE_MIN = 1
    DISTANCE_MAX = 5000
    VALUE_MIN = 1
    VALUE_MAX = 10_000_000

    # DT-S screening thresholds
    ACCEPT_MAX = 39
    REVIEW_MIN = 40
    REVIEW_MAX = 69
    REFUSE_MIN = 70

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value, shipper_exists):
        if not shipper_id or not shipper_exists:
            raise ValidationError("unknown_shipper")
        if weight_kg is None or not (self.WEIGHT_MIN <= weight_kg <= self.WEIGHT_MAX):
            raise ValidationError("weight_out_of_bounds")
        if distance_km is None or not (self.DISTANCE_MIN <= distance_km <= self.DISTANCE_MAX):
            raise ValidationError("distance_out_of_bounds")
        if declared_value is None or not (self.VALUE_MIN <= declared_value <= self.VALUE_MAX):
            raise ValidationError("declared_value_out_of_bounds")

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value,
                     shipper_exists=True):
        # Validation (DT-V)
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value, shipper_exists)
        except ValidationError as exc:
            return {"status": "rejected", "reason": str(exc)}

        # Store draft; on storage failure nothing else runs (DT-S note 3)
        try:
            quote_id = self.quote_store.storeDraft(
                shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage does NOT fail the quote (DT-S note 5)
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # Accept row: price, store quoted, notify (fire-and-forget)
        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price_amount)
            self.notification_service.sendQuoteDocument(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # Review row: no pricing, no notification (DT-S note 1)
        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # Refuse row: notify refusal, no pricing (DT-S note 2)
        self.quote_store.updateQuote(quote_id, "refused_screening")
        self.notification_service.sendRefusalNotice(shipper_id, quote_id)
        return {"status": "refused", "quote_id": quote_id}


# --- helpers for the end-to-end entry point ---

def _to_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


_RISK_WORDS = {
    "approved": 10.0,
    "accept": 10.0,
    "accepted": 10.0,
    "clear": 10.0,
    "active": 10.0,
    "assessed": 10.0,
    "review": 55.0,
    "hold": 55.0,
    "manual": 55.0,
    "declined": 90.0,
    "refused": 90.0,
    "denied": 90.0,
    "lapsed": 90.0,
}


def _resolve_screening(request):
    """Return (fail, risk_index) from request-driven screening outcome."""
    raw = request.get("screening_result", request.get("screening_status"))
    if isinstance(raw, str) and raw.strip().lower() in ("error", "unavailable", "down", "timeout"):
        return True, None
    num = _to_number(raw)
    if num is not None:
        return False, num
    if isinstance(raw, str):
        word = raw.strip().lower()
        if word in _RISK_WORDS:
            return False, _RISK_WORDS[word]
    # default: clearly accept
    return False, 10.0


def _store_fails(request):
    raw = request.get("store_result", request.get("store_status"))
    if isinstance(raw, str) and raw.strip().lower() in ("error", "unavailable", "down"):
        return True
    return False


def _notify_fails(request):
    raw = request.get("notification_result", request.get("notification_status"))
    if isinstance(raw, str) and raw.strip().lower() in ("error", "unavailable", "down"):
        return True
    return False


def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = request.get("shipper_id", request.get("shipperId"))
    shipper_exists = request.get("shipper_exists", request.get("shipper_found", True))

    weight_kg = _to_number(request.get("weight_kg", request.get("weightKg")))
    distance_km = _to_number(request.get("distance_km", request.get("distanceKm")))
    declared_value = _to_number(request.get("declared_value", request.get("declaredValue")))

    screening_fail, risk_index = _resolve_screening(request)

    quote_store = QuoteStore(fail=_store_fails(request))
    screening_service = ScreeningService(risk_index=risk_index, fail=screening_fail)
    tariff_engine = TariffEngine()
    notification_service = NotificationService(fail=_notify_fails(request))

    api = QuoteApi(quote_store, screening_service, tariff_engine, notification_service)

    return api.requestQuote(
        shipper_id, weight_kg, distance_km, declared_value, shipper_exists=shipper_exists)