class ScreeningUnavailableError(Exception):
    """Raised when the screening provider is unavailable."""
    pass


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable."""
    pass


# Decision table DT-S thresholds (shipper risk index)
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

# Decision table DT-V validation bounds
WEIGHT_MIN = 1
WEIGHT_MAX = 30000
DISTANCE_MIN = 1
DISTANCE_MAX = 5000
VALUE_MIN = 0

# Lifecycle statuses
STATUS_QUOTED = "quoted"
STATUS_REVIEW_HOLD = "review_hold"
STATUS_REFUSED_SCREENING = "refused_screening"
STATUS_HELD_UNSCREENED = "held_unscreened"


class TariffEngine:
    """Computes the freight price from weight and distance."""

    BASE_RATE = 5.0
    PER_KG = 0.15
    PER_KM = 0.08

    def price(self, weight_kg, distance_km):
        return round(
            self.BASE_RATE
            + self.PER_KG * float(weight_kg)
            + self.PER_KM * float(distance_km),
            2,
        )


class ScreeningService:
    """External denied-party screening provider returning a risk index."""

    def __init__(self, risk_index=10, available=True):
        self._risk_index = risk_index
        self._available = available

    def screen(self, shipper_id):
        if not self._available:
            raise ScreeningUnavailableError("screening service unavailable")
        return self._risk_index


class NotificationService:
    """External messaging provider. Fire-and-forget delivery."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return True

    def send_refusal_notice(self, shipper_id, quote_id):
        return True


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

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
            "status": "draft",
            "price_amount": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        rec = self._records.get(quote_id, {"quote_id": quote_id})
        rec["status"] = status
        if price_amount is not None:
            rec["price_amount"] = price_amount
        self._records[quote_id] = rec
        return dict(rec)


class QuoteAPI:
    """Entry participant: orchestrates screening and pricing."""

    def __init__(self, tariff_engine, screening_service,
                 notification_service, quote_store):
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service
        self.quote_store = quote_store

    def _valid(self, weight_kg, distance_km, declared_value):
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
        if v < VALUE_MIN:
            return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km,
                      declared_value):
        # Step 1: validation (DT-V)
        if not self._valid(weight_kg, distance_km, declared_value):
            return {"status": "rejectedInvalidRequest"}

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError:
            return {"status": "storeUnavailableError"}

        # Step 2b: screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: outage does not fail the quote
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, STATUS_HELD_UNSCREENED, price_amount
            )
            return {
                "status": "heldUnscreenedResponse",
                "quote_id": quote_id,
                "price_amount": price_amount,
            }

        # Step 3: apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, STATUS_QUOTED, price_amount
            )
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount
            )
            return {
                "status": "quotedResponse",
                "quote_id": quote_id,
                "price_amount": price_amount,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, STATUS_REVIEW_HOLD)
            return {"status": "reviewHoldResponse", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, STATUS_REFUSED_SCREENING)
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refusedScreeningResponse", "quote_id": quote_id}


_RISK_WORDS = {
    "approved": 10,
    "accept": 10,
    "active": 10,
    "clear": 10,
    "review": 50,
    "hold": 50,
    "assessed": 50,
    "declined": 90,
    "refuse": 90,
    "refused": 90,
    "denied": 90,
}


def _resolve_risk_index(request):
    for key in ("screening_result", "screening_status"):
        if key in request and request[key] is not None:
            val = request[key]
            if isinstance(val, (int, float)):
                return int(val), True
            sval = str(val).strip().lower()
            if sval == "error":
                return None, False
            try:
                return int(float(sval)), True
            except ValueError:
                if sval in _RISK_WORDS:
                    return _RISK_WORDS[sval], True
    return 10, True


def _is_error(request, *keys):
    for key in keys:
        if key in request and request[key] is not None:
            if str(request[key]).strip().lower() in ("error", "unavailable"):
                return True
    return False


_OUTCOME_MAP = {
    "rejectedInvalidRequest": "rejected",
    "storeUnavailableError": "error: storage unavailable",
    "quotedResponse": "confirmed",
    "reviewHoldResponse": "review_hold",
    "refusedScreeningResponse": "refused",
    "heldUnscreenedResponse": "held_unscreened",
}


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value", 0)

    # Shipper existence check
    if request.get("shipper_exists") is False or \
            request.get("shipper_found") is False:
        return {"status": "rejectedInvalidRequest", "reason": "shipper not found"}

    store_available = not _is_error(request, "store_result", "store_status")
    risk_index, screening_available = _resolve_risk_index(request)

    tariff_engine = TariffEngine()
    screening_service = ScreeningService(
        risk_index=risk_index if risk_index is not None else 0,
        available=screening_available,
    )
    notification_service = NotificationService()
    quote_store = QuoteStore(available=store_available)

    api = QuoteAPI(tariff_engine, screening_service,
                   notification_service, quote_store)

    result = api.request_quote(shipper_id, weight_kg, distance_km,
                               declared_value)

    internal = result.get("status")
    outcome = dict(result)
    outcome["status"] = _OUTCOME_MAP.get(internal, internal)
    outcome["outcome"] = internal
    return outcome