ACCEPT_MAX = 30.0
REVIEW_MIN = 30.0
REVIEW_MAX = 70.0
REFUSE_MIN = 70.0

MAX_WEIGHT_KG = 26000.0
MAX_DISTANCE_KM = 5000.0
MAX_DECLARED_VALUE = 10_000_000.0


class ScreeningError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, outcome=None):
        if outcome is None:
            return 10.0
        if isinstance(outcome, (int, float)):
            return float(outcome)
        word = str(outcome).lower()
        if word in ("error", "unavailable", "down", "timeout"):
            raise ScreeningError("screeningUnavailableError")
        mapping = {
            "approved": 5.0,
            "accept": 5.0,
            "clear": 5.0,
            "review": 50.0,
            "hold": 50.0,
            "declined": 90.0,
            "refuse": 90.0,
            "denied": 90.0,
        }
        try:
            return float(word)
        except ValueError:
            return mapping.get(word, 5.0)


class TariffEngine:
    """Computes freight price from weight and distance per tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG_KM = 0.00035

    def price(self, weight_kg, distance_km):
        return round(self.BASE_FEE + self.RATE_PER_KG_KM * weight_kg * distance_km, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, available=True):
        if not available:
            raise StoreUnavailableError("storeUnavailableError")
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

    def update_quote(self, quote_id, status, price_amount=None):
        rec = self._records.get(quote_id)
        if rec is None:
            rec = {"shipper_id": None, "status": None, "price": None}
            self._records[quote_id] = rec
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        return {"quote_id": quote_id, "status": status, "price": price_amount}


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening/pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _valid(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            return False
        try:
            w = float(weight_kg)
            d = float(distance_km)
            v = float(declared_value)
        except (TypeError, ValueError):
            return False
        if not (0 < w <= MAX_WEIGHT_KG):
            return False
        if not (0 < d <= MAX_DISTANCE_KM):
            return False
        if not (0 <= v <= MAX_DECLARED_VALUE):
            return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value,
                      store_available=True, screening_outcome=None):
        # Step 2: validate
        if not self._valid(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected", "reason": "rejectedInvalidRequest"}

        # Step 2/3: store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, available=store_available)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable", "reason": "storeUnavailableError"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id, screening_outcome)
        except ScreeningError:
            # Case d: screening outage -> price, hold unscreened, no notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "statusHeldUnscreened", price_amount)
            return {"status": "held_unscreened", "quote_id": quote_id, "price": price_amount}

        # Step 4: apply screening decision
        if risk_index <= ACCEPT_MAX:
            # Case a: accept
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "statusQuoted", price_amount)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            except Exception:
                pass
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}

        if REVIEW_MIN < risk_index < REVIEW_MAX:
            # Case b: review hold
            self.quote_store.update_quote(quote_id, "statusReviewHold")
            return {"status": "review_hold", "quote_id": quote_id}

        # Case c: refuse (risk_index >= REFUSE_MIN)
        self.quote_store.update_quote(quote_id, "statusRefusedScreening")
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            pass
        return {"status": "refused", "quote_id": quote_id}


def _screening_outcome_from_request(request):
    for key in ("screening_result", "screening_status", "screening_service_result",
                "screening_service_status"):
        if key in request and request[key] is not None:
            return request[key]
    if "risk_index" in request:
        return request["risk_index"]
    return None


def _store_available_from_request(request):
    for key in ("quote_store_status", "store_status", "quote_store_result", "store_result"):
        if key in request and request[key] is not None:
            val = str(request[key]).lower()
            if val in ("error", "unavailable", "down"):
                return False
            if val in ("stored", "ok", "available"):
                return True
    if request.get("quote_store_exists") is False:
        return False
    return True


def handle(request: dict) -> dict:
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)

    shipper_id = request.get("shipper_id") or request.get("shipperId")
    if request.get("shipper_exists") is False or request.get("shipper_found") is False:
        shipper_id = None

    weight_kg = request.get("weight_kg", request.get("weightKg"))
    distance_km = request.get("distance_km", request.get("distanceKm"))
    declared_value = request.get("declared_value", request.get("declaredValue", 0))

    store_available = _store_available_from_request(request)
    screening_outcome = _screening_outcome_from_request(request)

    return api.request_quote(
        shipper_id, weight_kg, distance_km, declared_value,
        store_available=store_available, screening_outcome=screening_outcome)