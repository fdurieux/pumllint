class ScreeningUnavailableError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class InvalidRequestError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, config=None):
        self._config = config or {}

    def screen(self, shipper_id):
        status = str(self._config.get("screening_status",
                     self._config.get("screening_result", ""))).lower()
        if status in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailableError("screening service unavailable")

        raw = self._config.get("screening_result", self._config.get("screening_status"))
        if isinstance(raw, (int, float)):
            return float(raw)
        word = str(raw).lower() if raw is not None else "approved"
        mapping = {
            "approved": 10.0,
            "accept": 10.0,
            "clear": 10.0,
            "assessed": 10.0,
            "active": 10.0,
            "review": 50.0,
            "hold": 50.0,
            "declined": 90.0,
            "refuse": 90.0,
            "denied": 90.0,
        }
        return mapping.get(word, 10.0)


class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    BASE_FEE = 25.0
    PER_KG = 0.35
    PER_KM = 0.12

    def price(self, weight_kg, distance_km):
        return round(self.BASE_FEE + self.PER_KG * weight_kg + self.PER_KM * distance_km, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, config=None):
        self._config = config or {}
        self._seq = 0
        self._records = {}

    def _store_ok(self):
        status = str(self._config.get("store_status",
                     self._config.get("store_result", "stored"))).lower()
        if status in ("error", "unavailable", "down", "fail"):
            return False
        return True

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if not self._store_ok():
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

    def update_quote(self, quote_id, status, price=None):
        rec = self._records.get(quote_id, {})
        rec["status"] = status
        if price is not None:
            rec["price"] = price
        self._records[quote_id] = rec
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    ACCEPT_MAX = 30.0
    REVIEW_MIN = 30.0
    REVIEW_MAX = 70.0
    REFUSE_MIN = 70.0

    WEIGHT_MIN, WEIGHT_MAX = 3, 19400
    DISTANCE_MIN, DISTANCE_MAX = 25, 7150
    VALUE_MIN, VALUE_MAX = 50, 83000

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or len(shipper_id) < 1:
            raise InvalidRequestError("shipper_id")
        if request.get("shipper_exists") is False or request.get("shipper_found") is False:
            raise InvalidRequestError("shipper_not_found")

        try:
            weight = float(request["weight_kg"])
            distance = float(request["distance_km"])
            value = float(request["declared_value"])
        except (KeyError, TypeError, ValueError):
            raise InvalidRequestError("missing_or_nonnumeric")

        if not (self.WEIGHT_MIN <= weight <= self.WEIGHT_MAX):
            raise InvalidRequestError("weight_kg")
        if not (self.DISTANCE_MIN <= distance <= self.DISTANCE_MAX):
            raise InvalidRequestError("distance_km")
        if not (self.VALUE_MIN <= value <= self.VALUE_MAX):
            raise InvalidRequestError("declared_value")

        return shipper_id, weight, distance, value

    def request_quote(self, request):
        # Validation (DT-V)
        try:
            shipper_id, weight, distance, value = self._validate(request)
        except InvalidRequestError:
            return {"status": "rejected: invalid_request"}

        # Store draft
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight, distance, value)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Screening (DT-S)
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage: price, hold unscreened, no notification (note 5)
            price = self.tariff_engine.price(weight, distance)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        if risk_index <= self.ACCEPT_MAX:
            # Accept -> price, quote, notify
            price = self.tariff_engine.price(weight, distance)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif risk_index >= self.REFUSE_MIN:
            # Refuse -> no pricing, notify refusal (note 2)
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}
        else:
            # Review hold -> no pricing, no notification (note 1)
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}


def handle(request: dict) -> dict:
    request = dict(request or {})
    screening_service = ScreeningService(request)
    tariff_engine = TariffEngine()
    quote_store = QuoteStore(request)
    notification_service = NotificationService()
    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)
    try:
        return api.request_quote(request)
    except Exception as exc:  # pragma: no cover
        return {"status": "error: %s" % exc}