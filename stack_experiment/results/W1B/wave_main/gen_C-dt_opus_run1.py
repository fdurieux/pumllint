import math


# --- Decision table constants ---------------------------------------------

# DT-V validation bounds (mirrored from OpenAPI schema constraints)
WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000

# DT-S screening bands (higher risk index is worse)
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70

# DT-P pricing coefficients
BASE_FEE = 25.0
PER_KG = 0.05
PER_KM = 0.10


# --- Exceptions -----------------------------------------------------------

class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


# --- External systems (outside the boundary) ------------------------------

class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, result=None, status=None):
        self._result = result
        self._status = status

    def screen(self, shipper_id):
        if self._status == "error" or self._result == "error":
            raise ScreeningUnavailableError("screening service unavailable")
        r = self._result
        if isinstance(r, bool):
            r = None
        if isinstance(r, (int, float)):
            return int(r)
        word = str(r).lower() if r is not None else ""
        if word in ("approved", "accept", "accepted", "active", "clear"):
            return 10
        if word in ("review", "hold", "manual"):
            return 50
        if word in ("declined", "refuse", "refused", "denied"):
            return 90
        # default: low risk / accept band
        return 10


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, status=None):
        self._status = status

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        if self._status == "error":
            return "failed"
        return "sent"

    def sendRefusalNotice(self, shipper_id, quote_id):
        if self._status == "error":
            return "failed"
        return "sent"


# --- Internal containers --------------------------------------------------

class TariffEngine:
    """Computes the freight price from weight and distance per the tariff rules."""

    def price(self, weight_kg, distance_km):
        return round(BASE_FEE + PER_KG * weight_kg + PER_KM * distance_km, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, status=None):
        self._status = status
        self._records = {}
        self._counter = 0

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value):
        if self._status == "error":
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

    def updateQuote(self, quote_id, status, price_amount=None):
        rec = self._records.get(quote_id, {})
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        self._records[quote_id] = rec
        return quote_id


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening/pricing, returns outcome."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _valid(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or len(shipper_id) < 1:
            return False
        for v in (weight_kg, distance_km, declared_value):
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                return False
        if not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            return False
        if not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            return False
        if not (VALUE_MIN <= declared_value <= VALUE_MAX):
            return False
        return True

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Step 1: validate (DT-V)
        if not self._valid(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # Step 2: store draft
        try:
            quote_id = self.quote_store.storeDraft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screen
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage: price anyway, hold, do not notify (DT-S note 5)
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4-7: apply DT-S decision
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price_amount)
            self.notification_service.sendQuoteDocument(shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # risk_index >= REFUSE_MIN
        self.quote_store.updateQuote(quote_id, "refused_screening")
        self.notification_service.sendRefusalNotice(shipper_id, quote_id)
        return {"status": "refused_screening", "quote_id": quote_id}


# --- Module-level entry point ---------------------------------------------

def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    screening_service = ScreeningService(
        result=request.get("screening_result"),
        status=request.get("screening_status"),
    )
    notification_service = NotificationService(
        status=request.get("notification_status"),
    )
    quote_store = QuoteStore(
        status=request.get("store_status"),
    )
    tariff_engine = TariffEngine()

    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)

    try:
        return api.requestQuote(shipper_id, weight_kg, distance_km, declared_value)
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "error: %s" % type(exc).__name__}