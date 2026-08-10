import math


# ---------------------------------------------------------------------------
# Configuration constants (decision table DT-S screening thresholds and
# decision table DT-V validation bounds — best-guess concrete values).
# ---------------------------------------------------------------------------

ACCEPT_MAX = 30.0          # riskIndex <= ACCEPT_MAX  -> accept / quote
REVIEW_MIN = 30.0          # ACCEPT_MAX < riskIndex   -> review
REVIEW_MAX = 70.0          # riskIndex < REFUSE_MIN   -> review
REFUSE_MIN = 70.0          # riskIndex >= REFUSE_MIN  -> refuse

WEIGHT_MIN = 10.0          # kg — a palletized consignment has a floor weight
WEIGHT_MAX = 26000.0       # kg — a full road trailer
DISTANCE_MIN = 1.0         # km
DISTANCE_MAX = 3000.0      # km
VALUE_MIN = 0.0
VALUE_MAX = 1_000_000.0

TARIFF_BASE = 25.0
TARIFF_PER_KG = 0.35
TARIFF_PER_KM = 1.10


# ---------------------------------------------------------------------------
# System-internal exceptions (failure paths from the sequence diagram).
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


# ---------------------------------------------------------------------------
# External systems (outside the boundary). Each method returns a SINGLE value.
# ---------------------------------------------------------------------------

class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, risk_index=None, status=None):
        if status == "error":
            raise ScreeningUnavailableError("screening service unavailable")
        if risk_index is not None:
            return float(risk_index)
        return 10.0  # default: low risk


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        # Fire-and-forget: never affects the response.
        return "sent"

    def sendRefusalNotice(self, shipper_id, quote_id):
        # Fire-and-forget: never affects the response.
        return "sent"


# ---------------------------------------------------------------------------
# Internal containers.
# ---------------------------------------------------------------------------

class TariffEngine:
    """Computes the freight price from weight and distance per the tariff."""

    def price(self, weight_kg, distance_km):
        amount = TARIFF_BASE + weight_kg * TARIFF_PER_KG + distance_km * TARIFF_PER_KM
        return round(amount, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._seq = 0

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value, status=None):
        if status == "error":
            raise StoreUnavailableError("quote store unavailable")
        self._seq += 1
        quote_id = "Q-{}".format(self._seq)
        self._records[quote_id] = {
            "quoteId": quote_id,
            "shipperId": shipper_id,
            "weightKg": weight_kg,
            "distanceKm": distance_km,
            "declaredValue": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def updateQuote(self, quote_id, status, price_amount=None):
        record = self._records.get(quote_id)
        if record is None:
            record = {"quoteId": quote_id}
            self._records[quote_id] = record
        record["status"] = status
        if price_amount is not None:
            record["price"] = price_amount
        return dict(record)


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    # -- validation (decision table DT-V) -----------------------------------
    def _validate(self, shipper_id, weight_kg, distance_km, declared_value, shipper_exists):
        if not shipper_exists:
            raise ValidationError("unknown_shipper")
        if shipper_id in (None, ""):
            raise ValidationError("missing_shipper")
        if weight_kg is None or distance_km is None or declared_value is None:
            raise ValidationError("missing_field")
        if not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            raise ValidationError("weight_out_of_bounds")
        if not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            raise ValidationError("distance_out_of_bounds")
        if not (VALUE_MIN <= declared_value <= VALUE_MAX):
            raise ValidationError("value_out_of_bounds")

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value,
                     shipper_exists=True, store_status=None,
                     screening_risk=None, screening_status=None):

        # 1. Validate (DT-V). Failure -> rejected invalid request.
        self._validate(shipper_id, weight_kg, distance_km, declared_value, shipper_exists)

        # 2. Store draft. Storage failure -> nothing else runs (DT-S note 3).
        quote_id = self.quote_store.storeDraft(
            shipper_id, weight_kg, distance_km, declared_value, status=store_status
        )

        # 3. Screen the shipper.
        try:
            risk_index = self.screening_service.screen(
                shipper_id, risk_index=screening_risk, status=screening_status
            )
        except ScreeningUnavailableError:
            # DT-S note 5: outage does NOT fail the quote. Priced, held, not notified.
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quoteId": quote_id,
                "price": price_amount,
            }

        # 4. Branch on riskIndex (DT-S).
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price_amount)
            # Fire-and-forget notification (DT-S note 4).
            self.notification_service.sendQuoteDocument(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quoteId": quote_id,
                "price": price_amount,
                "riskIndex": risk_index,
            }
        elif risk_index >= REFUSE_MIN:
            # DT-S note 2: refusal IS notified; pricing never runs.
            self.quote_store.updateQuote(quote_id, "refused_screening")
            self.notification_service.sendRefusalNotice(shipper_id, quote_id)
            return {
                "status": "refused",
                "quoteId": quote_id,
                "riskIndex": risk_index,
            }
        else:
            # DT-S note 1: review hold — no pricing, no notification.
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quoteId": quote_id,
                "riskIndex": risk_index,
            }


# ---------------------------------------------------------------------------
# Request helpers.
# ---------------------------------------------------------------------------

def _get(request, *keys, default=None):
    for k in keys:
        if k in request and request[k] is not None:
            return request[k]
    return default


def _num(value, default=None):
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1", "exists", "found", "active")
    return bool(value)


def _screening_from_request(request):
    """Return (risk_index, status) tuple for driving the screening call."""
    raw = _get(request, "screening_result", "screening_status",
               "screening_service_result", "screening_service_status")
    if raw is None:
        return None, None
    if isinstance(raw, (int, float)):
        return float(raw), None
    word = str(raw).strip().lower()
    if word == "error":
        return None, "error"
    numeric = _num(word)
    if numeric is not None:
        return numeric, None
    mapping = {
        "approved": 10.0,
        "active": 10.0,
        "accept": 10.0,
        "clear": 10.0,
        "declined": 90.0,
        "refused": 90.0,
        "denied": 90.0,
        "review": 50.0,
        "assessed": 50.0,
        "hold": 50.0,
    }
    return mapping.get(word, 10.0), None


def _store_status_from_request(request):
    raw = _get(request, "store_result", "store_status",
               "quote_store_result", "quote_store_status")
    if raw is None:
        return None
    return str(raw).strip().lower()


# ---------------------------------------------------------------------------
# Module-level end-to-end entry point.
# ---------------------------------------------------------------------------

def handle(request: dict) -> dict:
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)

    shipper_id = _get(request, "shipper_id", "shipperId", "shipper")
    weight_kg = _num(_get(request, "weight_kg", "weightKg", "weight"))
    distance_km = _num(_get(request, "distance_km", "distanceKm", "distance"))
    declared_value = _num(_get(request, "declared_value", "declaredValue", "value"))

    shipper_exists = _bool(_get(request, "shipper_exists", "shipper_found",
                                default=True), default=True)

    screening_risk, screening_status = _screening_from_request(request)
    store_status = _store_status_from_request(request)

    try:
        return api.requestQuote(
            shipper_id, weight_kg, distance_km, declared_value,
            shipper_exists=shipper_exists,
            store_status=store_status,
            screening_risk=screening_risk,
            screening_status=screening_status,
        )
    except ValidationError as exc:
        return {"status": "rejected: invalid_request", "reason": str(exc)}
    except StoreUnavailableError as exc:
        return {"status": "error: store_unavailable", "reason": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error: {}".format(exc)}