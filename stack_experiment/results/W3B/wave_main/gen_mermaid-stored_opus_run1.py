def _to_camel(alias):
    return "".join(p.capitalize() for p in alias.split("_"))


# ----- Decision table DT-V: validation bounds -----
WEIGHT_MIN, WEIGHT_MAX = 1.0, 26000.0
DISTANCE_MIN, DISTANCE_MAX = 1.0, 3000.0
VALUE_MIN, VALUE_MAX = 1.0, 1_000_000.0

# ----- Decision table DT-S: screening thresholds -----
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71


class ValidationError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, outcome=None):
        self._outcome = outcome

    def screen(self, shipper_id):
        outcome = self._outcome
        if outcome is None:
            return 0
        if isinstance(outcome, (int, float)):
            return int(outcome)
        word = str(outcome).strip().lower()
        if word in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailableError("screening service unavailable")
        if word in ("approved", "accept", "accepted", "clear", "active"):
            return 0
        if word in ("review", "hold", "manual", "assessed"):
            return REVIEW_MIN
        if word in ("declined", "refuse", "refused", "denied", "lapsed"):
            return REFUSE_MIN
        try:
            return int(float(word))
        except ValueError:
            return 0


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff rules."""

    BASE = 25.0
    PER_KG = 0.12
    PER_KM = 0.35

    def price(self, weight_kg, distance_km):
        return round(self.BASE + self.PER_KG * weight_kg + self.PER_KM * distance_km, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available=True):
        self._available = available
        self._seq = 0
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._available:
            raise StoreUnavailableError("quote store unavailable")
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

    def update_quote(self, quote_id, status, price_amount=None):
        if not self._available:
            raise StoreUnavailableError("quote store unavailable")
        rec = self._records.get(quote_id, {})
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        self._records[quote_id] = rec
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            raise ValidationError("missing shipper")
        if weight_kg is None or not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            raise ValidationError("weight out of bounds")
        if distance_km is None or not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            raise ValidationError("distance out of bounds")
        if declared_value is None or not (VALUE_MIN <= declared_value <= VALUE_MAX):
            raise ValidationError("declared value out of bounds")

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # DT-V validation
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as exc:
            return {"status": "rejected", "reason": str(exc)}

        # Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError as exc:
            return {"status": "error: store_unavailable", "reason": str(exc)}

        # Screening (DT-S)
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: outage does not fail the quote — price & hold.
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {"status": "confirmed", "quote_id": quote_id, "price": price_amount}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # risk_index >= REFUSE_MIN
        self.quote_store.update_quote(quote_id, "refused_screening")
        self.notification_service.send_refusal_notice(shipper_id, quote_id)
        return {"status": "rejected", "reason": "screening_refusal", "quote_id": quote_id}


def _store_available(request):
    for key in ("quote_store_result", "quote_store_status", "store_result", "store_status"):
        if key in request:
            val = str(request[key]).strip().lower()
            if val in ("error", "unavailable", "down"):
                return False
            if val in ("stored", "ok", "active", "available"):
                return True
    return True


def _screening_outcome(request):
    for key in (
        "screening_result",
        "screening_status",
        "screening_service_result",
        "screening_service_status",
    ):
        if key in request:
            return request[key]
    return None


def handle(request: dict) -> dict:
    request = request or {}

    shipper_id = request.get("shipper_id") or request.get("shipper")
    if request.get("shipper_exists") is False or request.get("shipper_found") is False:
        shipper_id = None

    weight_kg = request.get("weight_kg", request.get("weightKg"))
    distance_km = request.get("distance_km", request.get("distanceKm"))
    declared_value = request.get("declared_value", request.get("declaredValue"))

    store = QuoteStore(available=_store_available(request))
    screening = ScreeningService(outcome=_screening_outcome(request))
    tariff = TariffEngine()
    notifier = NotificationService()

    api = QuoteApi(store, screening, tariff, notifier)

    try:
        return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)
    except Exception as exc:  # pragma: no cover
        return {"status": "error: {}".format(exc)}