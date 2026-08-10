import logging

logger = logging.getLogger("cargoquote")

# --- Tariff / screening thresholds (0-100 risk index scale) ---
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70

# --- Validation bounds (decision table DT-V) ---
WEIGHT_MIN = 1
WEIGHT_MAX = 26000
DISTANCE_MIN = 1
DISTANCE_MAX = 3000
VALUE_MIN = 0
VALUE_MAX = 10_000_000

# --- Tariff constants ---
BASE_CHARGE = 25.0
RATE_PER_KG_KM = 0.0005

# --- Status names ---
STATUS_QUOTED = "quoted"
STATUS_REVIEW_HOLD = "review_hold"
STATUS_REFUSED_SCREENING = "refused_screening"
STATUS_HELD_UNSCREENED = "held_unscreened"


class ScreeningUnavailableError(Exception):
    """Raised when the external screening provider is unavailable."""


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable."""


class TariffEngine:  # engine
    def price(self, weight_kg, distance_km):
        """Compute priceAmount for a validated request."""
        amount = BASE_CHARGE + (float(weight_kg) * float(distance_km) *
                                RATE_PER_KG_KM)
        return round(amount, 2)


class ScreeningService:  # external
    def __init__(self, result=None, status=None):
        self._result = result
        self._status = status

    def screen(self, shipper_id):
        """Return riskIndex. A screening failure surfaces as
        screeningUnavailableError (service unavailable)."""
        if self._status in ("error", "unavailable"):
            raise ScreeningUnavailableError(
                "screening service unavailable")
        if self._result is not None:
            try:
                return float(self._result)
            except (TypeError, ValueError):
                pass
        mapping = {
            "approved": 10.0,
            "active": 10.0,
            "accept": 10.0,
            "clear": 10.0,
            "assessed": 50.0,
            "review": 50.0,
            "hold": 50.0,
            "declined": 90.0,
            "refuse": 90.0,
            "denied": 90.0,
        }
        return mapping.get(self._status, 10.0)


class NotificationService:  # external
    def send_quote_document(self, shipper_id, quote_id, price_amount):
        """Deliver the quote document. Fire-and-forget."""
        try:
            logger.info("quote document sent to %s for %s (%s)",
                        shipper_id, quote_id, price_amount)
        except Exception:
            pass
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        """Deliver the refusal notice. Fire-and-forget."""
        try:
            logger.info("refusal notice sent to %s for %s",
                        shipper_id, quote_id)
        except Exception:
            pass
        return "sent"


class QuoteStore:  # database
    def __init__(self, status=None, quote_id="Q-1"):
        self._status = status
        self._quote_id = quote_id
        self._counter = 0

    def store_draft(self, shipper_id, weight_kg, distance_km,
                    declared_value):
        """Store the draft; return quoteId. A storage failure surfaces
        as storeUnavailableError (storage unavailable)."""
        if self._status in ("error", "unavailable"):
            raise StoreUnavailableError("storage unavailable")
        self._counter += 1
        return self._quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        """Called as updateQuote(quoteId, status) or
        updateQuote(quoteId, status, priceAmount); returns updatedQuote."""
        if self._status in ("error", "unavailable"):
            raise StoreUnavailableError("storage unavailable")
        return {
            "quote_id": quote_id,
            "status": status,
            "price_amount": price_amount,
        }


class QuoteAPI:  # service — the entry participant
    def __init__(self, store, screening, tariff, notification):
        self._store = store
        self._screening = screening
        self._tariff = tariff
        self._notification = notification

    def _validate(self, weight_kg, distance_km, declared_value):
        try:
            w = float(weight_kg)
            d = float(distance_km)
            v = float(declared_value)
        except (TypeError, ValueError):
            return False
        if not (WEIGHT_MIN <= w <= WEIGHT_MAX):
            return False
        if not (DISTANCE_MIN <= d <= DISTANCE_MAX):
            return False
        if not (VALUE_MIN <= v <= VALUE_MAX):
            return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km,
                      declared_value):
        # 1. Validate (DT-V)
        if not self._validate(weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # store draft
        try:
            quote_id = self._store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # 2. Screen
        try:
            risk_index = self._screening.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: outage does not fail the quote; price + hold
            price_amount = self._tariff.price(weight_kg, distance_km)
            try:
                self._store.update_quote(
                    quote_id, STATUS_HELD_UNSCREENED, price_amount)
            except StoreUnavailableError:
                return {"status": "error: store_unavailable"}
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price_amount": price_amount,
            }

        # 3. Apply screening decision (DT-S)
        try:
            if risk_index <= ACCEPT_MAX:
                price_amount = self._tariff.price(weight_kg, distance_km)
                self._store.update_quote(
                    quote_id, STATUS_QUOTED, price_amount)
                self._notification.send_quote_document(
                    shipper_id, quote_id, price_amount)
                return {
                    "status": "confirmed",
                    "quote_id": quote_id,
                    "price_amount": price_amount,
                }
            elif risk_index >= REFUSE_MIN:
                self._store.update_quote(
                    quote_id, STATUS_REFUSED_SCREENING)
                self._notification.send_refusal_notice(
                    shipper_id, quote_id)
                return {"status": "refused", "quote_id": quote_id}
            else:  # REVIEW_MIN <= risk_index <= REVIEW_MAX
                self._store.update_quote(quote_id, STATUS_REVIEW_HOLD)
                return {"status": "review_hold", "quote_id": quote_id}
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}


def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = request.get("shipper_id", "S-1")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value", 0)

    # Existence checks
    if request.get("shipper_exists") is False or \
            request.get("shipper_found") is False:
        return {"status": "rejected: invalid_request"}

    screening = ScreeningService(
        result=request.get("screening_result"),
        status=request.get("screening_status"),
    )
    store_status = request.get("store_status") or request.get("store_result")
    if store_status == "stored":
        store_status = None
    store = QuoteStore(
        status=store_status,
        quote_id=request.get("quote_id", "Q-1"),
    )
    tariff = TariffEngine()
    notification = NotificationService()

    api = QuoteAPI(store, screening, tariff, notification)
    return api.request_quote(
        shipper_id, weight_kg, distance_km, declared_value)