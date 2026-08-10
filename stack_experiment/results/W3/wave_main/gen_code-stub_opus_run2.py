MIN_WEIGHT_KG = 1
MAX_WEIGHT_KG = 26000
MIN_DISTANCE_KM = 1
MAX_DISTANCE_KM = 3000
MIN_DECLARED_VALUE = 1
MAX_DECLARED_VALUE = 1_000_000

ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

STATUS_QUOTED = "QUOTED"
STATUS_REVIEW_HOLD = "REVIEW_HOLD"
STATUS_REFUSED_SCREENING = "REFUSED_SCREENING"
STATUS_HELD_UNSCREENED = "HELD_UNSCREENED"

BASE_RATE_PER_KG = 0.15
BASE_RATE_PER_KM = 0.85


class ScreeningUnavailableError(Exception):
    """Raised when the screening provider is unavailable."""


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable."""


class TariffEngine:  # tariff_engine
    def price(self, weight_kg, distance_km):
        amount = (weight_kg * BASE_RATE_PER_KG) + (distance_km * BASE_RATE_PER_KM)
        return round(amount, 2)


class ScreeningService:  # screening_service (external)
    def __init__(self, risk_index=0, available=True):
        self._risk_index = risk_index
        self._available = available

    def screen(self, shipper_id):
        if not self._available:
            raise ScreeningUnavailableError("screening service unavailable")
        return self._risk_index


class NotificationService:  # notification_service (external)
    def __init__(self, available=True):
        self._available = available

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        # Fire-and-forget: a delivery failure never changes the response.
        try:
            if not self._available:
                return False
            return True
        except Exception:
            return False

    def send_refusal_notice(self, shipper_id, quote_id):
        # Fire-and-forget: a delivery failure never changes the response.
        try:
            if not self._available:
                return False
            return True
        except Exception:
            return False


class QuoteStore:  # quote_store (database)
    def __init__(self, available=True):
        self._available = available
        self._seq = 0
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._available:
            raise StoreUnavailableError("storage unavailable")
        self._seq += 1
        quote_id = "Q-%04d" % self._seq
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "DRAFT",
            "price_amount": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        if not self._available:
            raise StoreUnavailableError("storage unavailable")
        record = self._records.get(quote_id, {"quote_id": quote_id})
        record["status"] = status
        if price_amount is not None:
            record["price_amount"] = price_amount
        self._records[quote_id] = record
        return dict(record)


class QuoteAPI:  # quote_api (entry participant)
    def __init__(self, tariff_engine, screening_service,
                 notification_service, quote_store):
        self._tariff_engine = tariff_engine
        self._screening_service = screening_service
        self._notification_service = notification_service
        self._quote_store = quote_store

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            return False
        try:
            w = float(weight_kg)
            d = float(distance_km)
            v = float(declared_value)
        except (TypeError, ValueError):
            return False
        if not (MIN_WEIGHT_KG <= w <= MAX_WEIGHT_KG):
            return False
        if not (MIN_DISTANCE_KM <= d <= MAX_DISTANCE_KM):
            return False
        if not (MIN_DECLARED_VALUE <= v <= MAX_DECLARED_VALUE):
            return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Step 1: validate (DT-V)
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected", "reason": "invalid request"}

        # Step 1/2: store draft
        try:
            quote_id = self._quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError as exc:
            return {"status": "error: storage unavailable", "reason": str(exc)}

        # Step 2: screening
        try:
            risk_index = self._screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: screening outage does not fail the quote.
            price_amount = self._tariff_engine.price(weight_kg, distance_km)
            self._quote_store.update_quote(
                quote_id, STATUS_HELD_UNSCREENED, price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        # Step 3: apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            # accept
            price_amount = self._tariff_engine.price(weight_kg, distance_km)
            self._quote_store.update_quote(
                quote_id, STATUS_QUOTED, price_amount)
            self._notification_service.send_quote_document(
                shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # review hold (DT-S note 1): no pricing, no notification
            self._quote_store.update_quote(quote_id, STATUS_REVIEW_HOLD)
            return {"status": "review_hold", "quote_id": quote_id}
        else:
            # refuse (risk_index >= REFUSE_MIN); DT-S note 2: notified, no pricing
            self._quote_store.update_quote(quote_id, STATUS_REFUSED_SCREENING)
            self._notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused", "quote_id": quote_id}


def _parse_screening(request):
    """Determine (risk_index, available) from the request."""
    raw = request.get("screening_service_result",
                       request.get("screening_service_status"))
    if raw is None:
        return 0, True

    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return raw, True

    word = str(raw).strip().lower()
    if word in ("error", "unavailable", "down", "timeout"):
        return 0, False
    if word in ("approved", "accept", "accepted", "clear", "low"):
        return ACCEPT_MAX, True
    if word in ("review", "hold", "manual", "medium"):
        return REVIEW_MIN, True
    if word in ("declined", "refuse", "refused", "denied", "high"):
        return REFUSE_MIN, True
    # Numeric string?
    try:
        return float(word), True
    except ValueError:
        return 0, True


def _service_available(request, prefix):
    status = request.get(prefix + "_status", request.get(prefix + "_result"))
    if status is None:
        return True
    word = str(status).strip().lower()
    if word in ("error", "unavailable", "down", "timeout", "fail", "failed"):
        return False
    return True


def handle(request: dict) -> dict:
    if not isinstance(request, dict):
        return {"status": "error: invalid request"}

    risk_index, screening_available = _parse_screening(request)
    store_available = _service_available(request, "quote_store")
    notification_available = _service_available(request, "notification_service")

    tariff_engine = TariffEngine()
    screening_service = ScreeningService(
        risk_index=risk_index, available=screening_available)
    notification_service = NotificationService(available=notification_available)
    quote_store = QuoteStore(available=store_available)

    api = QuoteAPI(tariff_engine, screening_service,
                   notification_service, quote_store)

    shipper_id = request.get("shipper_id")
    if "shipper_exists" in request and not request.get("shipper_exists"):
        shipper_id = None
    if "shipper_found" in request and not request.get("shipper_found"):
        shipper_id = None

    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)