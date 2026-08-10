import copy

# ---------------------------------------------------------------------------
# Decision-table constants (DT-S, DT-P, DT-V)
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


# ---------------------------------------------------------------------------
# Internal signalling exceptions
# ---------------------------------------------------------------------------
class InvalidRequestError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


# ---------------------------------------------------------------------------
# External systems (outside the CargoQuote boundary)
# ---------------------------------------------------------------------------
class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, outcome=None):
        # outcome: an int risk index, or a status word like "error"/"unavailable"
        self._outcome = outcome

    def screen(self, shipper_id):
        outcome = self._outcome
        if isinstance(outcome, str):
            word = outcome.strip().lower()
            if word in ("error", "unavailable", "down", "timeout", "outage"):
                raise ScreeningUnavailableError("screening_unavailable")
            try:
                return int(word)
            except ValueError:
                # unknown word -> treat as clean (accept band)
                return 0
        if outcome is None:
            return 0
        return int(outcome)


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, deliver_ok=True):
        self._deliver_ok = deliver_ok

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        # fire-and-forget: return a plausible single value; failures are ignored
        if not self._deliver_ok:
            return "delivery_failed"
        return "delivered"

    def sendRefusalNotice(self, shipper_id, quote_id):
        if not self._deliver_ok:
            return "delivery_failed"
        return "delivered"


# ---------------------------------------------------------------------------
# CargoQuote containers
# ---------------------------------------------------------------------------
class TariffEngine:
    """Computes the freight price per DT-P."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km  # P1
        if weight_kg > HEAVY_THRESHOLD:  # P2
            result += HEAVY_SURCHARGE
        if distance_km >= LONGHAUL_THRESHOLD:  # P3 (after P2)
            result *= LONGHAUL_MULTIPLIER
        return round(result, 2)  # P4


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self._available = available
        self._records = {}
        self._seq = 0

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._available:
            raise StoreUnavailableError("store_unavailable")
        self._seq += 1
        quote_id = "Q-{:06d}".format(self._seq)
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
        record = self._records.get(quote_id)
        if record is None:
            record = {}
            self._records[quote_id] = record
        record["status"] = status
        if price_amount is not None:
            record["price"] = price_amount
        return quote_id


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    # -- DT-V validation ---------------------------------------------------
    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            raise InvalidRequestError("shipper_id")
        if not self._is_number(weight_kg) or not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            raise InvalidRequestError("weight_kg")
        if not self._is_number(distance_km) or not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            raise InvalidRequestError("distance_km")
        if not self._is_number(declared_value) or not (VALUE_MIN <= declared_value <= VALUE_MAX):
            raise InvalidRequestError("declared_value")

    @staticmethod
    def _is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    # -- orchestration -----------------------------------------------------
    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Step 1 — validate (DT-V)
        self._validate(shipper_id, weight_kg, distance_km, declared_value)

        # Step 2 — store draft
        quote_id = self.quote_store.storeDraft(shipper_id, weight_kg, distance_km, declared_value)

        # Step 3 — screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # screening outage: price anyway, hold, no notification (DT-S note 5)
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4/5/6 — apply DT-S decision
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price_amount)
            self.notification_service.sendQuoteDocument(shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.updateQuote(quote_id, "refused_screening")
            self.notification_service.sendRefusalNotice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


# ---------------------------------------------------------------------------
# Module-level end-to-end entry point
# ---------------------------------------------------------------------------
def _extract_store_available(request):
    for key in ("store_result", "store_status", "quote_store_result", "quote_store_status"):
        if key in request:
            word = str(request[key]).strip().lower()
            if word in ("error", "unavailable", "down", "fail", "failed"):
                return False
            return True
    # existence flags
    if request.get("store_exists") is False or request.get("quote_store_exists") is False:
        return False
    return True


def _extract_screening_outcome(request):
    for key in ("screening_result", "screening_status", "screening_service_result",
                "risk_index", "risk"):
        if key in request:
            return request[key]
    return None


def _extract_notification_ok(request):
    for key in ("notification_result", "notification_status",
                "notification_service_result", "notification_service_status"):
        if key in request:
            word = str(request[key]).strip().lower()
            if word in ("error", "unavailable", "fail", "failed", "down"):
                return False
            return True
    return True


def handle(request: dict) -> dict:
    request = copy.deepcopy(request) if isinstance(request, dict) else {}

    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    store_available = _extract_store_available(request)
    screening_outcome = _extract_screening_outcome(request)
    notification_ok = _extract_notification_ok(request)

    tariff_engine = TariffEngine()
    quote_store = QuoteStore(available=store_available)
    screening_service = ScreeningService(outcome=screening_outcome)
    notification_service = NotificationService(deliver_ok=notification_ok)

    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)

    try:
        return api.requestQuote(shipper_id, weight_kg, distance_km, declared_value)
    except InvalidRequestError:
        return {"status": "rejected: invalid_request"}
    except StoreUnavailableError:
        return {"status": "error: store_unavailable"}
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error: {}".format(exc)}