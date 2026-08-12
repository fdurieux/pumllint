def _to_camel(alias):
    return "".join(part.capitalize() for part in alias.split("_"))


# Screening decision thresholds (decision table DT-S)
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71

# Validation bounds (decision table DT-V)
WEIGHT_MIN = 1
WEIGHT_MAX = 30000
DISTANCE_MIN = 1
DISTANCE_MAX = 5000
VALUE_MIN = 1
VALUE_MAX = 10_000_000


class ScreeningError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ValidationError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, outcome=None):
        if outcome is None:
            return 10
        if isinstance(outcome, (int, float)):
            return outcome
        text = str(outcome).lower()
        if text in ("error", "unavailable", "timeout"):
            raise ScreeningError("screening service unavailable")
        mapping = {
            "approved": 10,
            "clear": 5,
            "low": 10,
            "accept": 10,
            "review": 50,
            "hold": 50,
            "medium": 50,
            "declined": 90,
            "refused": 90,
            "high": 90,
            "denied": 95,
        }
        if text in mapping:
            return mapping[text]
        try:
            return float(text)
        except ValueError:
            return 10


class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG = 0.5
    RATE_PER_KM = 0.12

    def price(self, weight_kg, distance_km):
        return round(
            self.BASE_FEE
            + weight_kg * self.RATE_PER_KG
            + distance_km * self.RATE_PER_KM,
            2,
        )


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._quotes = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, available=True):
        if not available:
            raise StoreUnavailableError("quote store unavailable")
        self._seq += 1
        quote_id = "Q-%04d" % self._seq
        self._quotes[quote_id] = {
            "quoteId": quote_id,
            "shipperId": shipper_id,
            "weightKg": weight_kg,
            "distanceKm": distance_km,
            "declaredValue": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price=None):
        record = self._quotes.get(quote_id)
        if record is None:
            raise StoreUnavailableError("quote not found")
        record["status"] = status
        if price is not None:
            record["price"] = price
        return dict(record)


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            raise ValidationError("missing shipperId")
        for name, val, lo, hi in (
            ("weightKg", weight_kg, WEIGHT_MIN, WEIGHT_MAX),
            ("distanceKm", distance_km, DISTANCE_MIN, DISTANCE_MAX),
            ("declaredValue", declared_value, VALUE_MIN, VALUE_MAX),
        ):
            if val is None or not isinstance(val, (int, float)):
                raise ValidationError("invalid %s" % name)
            if val < lo or val > hi:
                raise ValidationError("out of bounds %s" % name)

    def request_quote(
        self,
        shipper_id,
        weight_kg,
        distance_km,
        declared_value,
        screening_outcome=None,
        store_available=True,
    ):
        # Validation (DT-V)
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as exc:
            return {"status": "rejected: invalid request", "reason": str(exc)}

        # Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, available=store_available
            )
        except StoreUnavailableError as exc:
            return {"status": "error: store unavailable", "reason": str(exc)}

        # Screening (DT-S)
        try:
            risk_index = self.screening_service.screen(shipper_id, screening_outcome)
        except ScreeningError:
            # Screening outage: price, hold unscreened, no notification (note 5)
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quoteId": quote_id,
                "price": price_amount,
            }

        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quoteId": quote_id, "price": price_amount}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quoteId": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused", "quoteId": quote_id}


def _build_api():
    return QuoteApi(
        TariffEngine(),
        QuoteStore(),
        ScreeningService(),
        NotificationService(),
    )


def handle(request: dict) -> dict:
    api = _build_api()

    shipper_id = request.get("shipperId", request.get("shipper_id"))
    weight_kg = request.get("weightKg", request.get("weight_kg"))
    distance_km = request.get("distanceKm", request.get("distance_km"))
    declared_value = request.get("declaredValue", request.get("declared_value"))

    # Store availability
    store_available = True
    store_status = request.get("store_status", request.get("store_result"))
    if store_status is not None and str(store_status).lower() in (
        "error",
        "unavailable",
        "down",
    ):
        store_available = False

    # Screening outcome
    screening_outcome = request.get("screening_result", request.get("screening_status"))

    return api.request_quote(
        shipper_id,
        weight_kg,
        distance_km,
        declared_value,
        screening_outcome=screening_outcome,
        store_available=store_available,
    )