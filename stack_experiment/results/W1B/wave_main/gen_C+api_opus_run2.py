ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70

WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000


class InvalidRequestError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, config=None):
        self.config = config or {}

    def screen(self, shipper_id):
        status = self.config.get("screening_status")
        if status is None:
            status = self.config.get("screening_result")
        if isinstance(status, str) and status.lower() in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailableError("screening service unavailable")
        if status is not None:
            try:
                return float(status)
            except (ValueError, TypeError):
                pass
            s = str(status).lower()
            if s in ("approved", "accept", "accepted", "clear", "assessed", "active"):
                return 10.0
            if s in ("review", "hold", "manual"):
                return 50.0
            if s in ("declined", "refused", "denied", "reject", "rejected", "lapsed"):
                return 90.0
        return 10.0


class TariffEngine:
    """Computes the freight price from weight and distance per the published tariff."""

    BASE = 25.0
    RATE_PER_KG = 0.5
    RATE_PER_KM = 0.1

    def price(self, weight_kg, distance_km):
        return round(self.BASE + weight_kg * self.RATE_PER_KG + distance_km * self.RATE_PER_KM, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, config=None):
        self.config = config or {}
        self._counter = 0
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        status = self.config.get("store_status")
        if status is None:
            status = self.config.get("store_result")
        if isinstance(status, str) and status.lower() in ("error", "unavailable", "down"):
            raise StoreUnavailableError("store unavailable")
        self._counter += 1
        quote_id = "Q-{}".format(self._counter)
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

    def send_quote_document(self, shipper_id, quote_id, price):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, quote_store, screening_service, tariff_engine, notification_service):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or len(shipper_id) < 1:
            raise InvalidRequestError("shipper_id")
        for name, value, lo, hi in (
            ("weight_kg", weight_kg, WEIGHT_MIN, WEIGHT_MAX),
            ("distance_km", distance_km, DISTANCE_MIN, DISTANCE_MAX),
            ("declared_value", declared_value, VALUE_MIN, VALUE_MAX),
        ):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise InvalidRequestError(name)
            if value < lo or value > hi:
                raise InvalidRequestError(name)

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value, shipper_exists=True):
        # DT-V validation
        try:
            if not shipper_exists:
                raise InvalidRequestError("shipper_not_found")
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except InvalidRequestError:
            return {"status": "rejected: invalid_request"}

        # Store draft
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # DT-S note 5: priced, stored on hold, not notified
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {"status": "held_unscreened", "quote_id": quote_id, "price": price, "hold": True}

        # DT-S decisions
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif risk_index >= REFUSE_MIN:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}
        else:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}


def handle(request: dict) -> dict:
    request = request or {}
    quote_store = QuoteStore(request)
    screening_service = ScreeningService(request)
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    api = QuoteApi(quote_store, screening_service, tariff_engine, notification_service)

    shipper_exists = request.get("shipper_exists", request.get("shipper_found", True))

    return api.request_quote(
        request.get("shipper_id"),
        request.get("weight_kg"),
        request.get("distance_km"),
        request.get("declared_value"),
        shipper_exists=shipper_exists,
    )