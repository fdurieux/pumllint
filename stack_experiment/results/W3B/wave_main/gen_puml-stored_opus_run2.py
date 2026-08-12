MAX_WEIGHT_KG = 26000
MAX_DISTANCE_KM = 5000
MAX_DECLARED_VALUE = 1_000_000

ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70


class ValidationError(Exception):
    pass


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG = 0.15
    RATE_PER_KM = 0.40

    def price(self, weight_kg, distance_km):
        amount = self.BASE_FEE + (weight_kg * self.RATE_PER_KG) + (distance_km * self.RATE_PER_KM)
        return round(amount, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, available=True):
        if not available:
            raise StoreUnavailableError("storage unavailable")
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
        record = self._records.get(quote_id)
        if record is None:
            raise StoreUnavailableError("unknown quote")
        record["status"] = status
        if price is not None:
            record["price"] = price
        return quote_id


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, outcome=None):
        if outcome is None:
            return 10
        if isinstance(outcome, (int, float)):
            return outcome
        word = str(outcome).strip().lower()
        if word in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailableError("screening service unavailable")
        if word in ("approved", "accept", "accepted", "clear", "clean", "low"):
            return 10
        if word in ("review", "hold", "manual", "medium"):
            return 50
        if word in ("declined", "denied", "refuse", "refused", "high", "hit"):
            return 90
        try:
            return float(word)
        except ValueError:
            return 10


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine=None, quote_store=None,
                 screening_service=None, notification_service=None):
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    def _validate(self, weight_kg, distance_km, declared_value):
        if weight_kg is None or distance_km is None or declared_value is None:
            raise ValidationError("missing field")
        try:
            weight_kg = float(weight_kg)
            distance_km = float(distance_km)
            declared_value = float(declared_value)
        except (TypeError, ValueError):
            raise ValidationError("non-numeric field")
        if not (0 < weight_kg <= MAX_WEIGHT_KG):
            raise ValidationError("weight out of bounds")
        if not (0 < distance_km <= MAX_DISTANCE_KM):
            raise ValidationError("distance out of bounds")
        if not (0 < declared_value <= MAX_DECLARED_VALUE):
            raise ValidationError("declared value out of bounds")
        return weight_kg, distance_km, declared_value

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value,
                      store_available=True, screening_outcome=None):
        # DT-V: validate request bounds
        weight_kg, distance_km, declared_value = self._validate(
            weight_kg, distance_km, declared_value)

        # Store draft; on storage failure nothing else runs (DT-S note 3)
        quote_id = self.quote_store.store_draft(
            shipper_id, weight_kg, distance_km, declared_value, available=store_available)

        # Screening
        try:
            risk_index = self.screening_service.screen(shipper_id, outcome=screening_outcome)
        except ScreeningUnavailableError:
            # DT-S note 5: priced, stored on hold, not notified
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
            }

        if risk_index <= ACCEPT_MAX:
            # accept: price, quote, notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # DT-S note 1: review hold, no pricing, no notification
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        else:  # risk_index >= REFUSE_MIN
            # DT-S note 2: refusal IS notified, pricing never runs
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {
                "status": "refused",
                "quote_id": quote_id,
            }


def _screening_outcome_from_request(request):
    for key in ("screening_result", "screening_status", "screening_service_result",
                "screening_service_status"):
        if key in request and request[key] is not None:
            return request[key]
    return None


def handle(request: dict) -> dict:
    api = QuoteApi()

    shipper_id = request.get("shipper_id") or request.get("shipperId")

    # existence flag for shipper
    shipper_exists = request.get("shipper_exists", request.get("shipper_found", True))
    if not shipper_exists:
        return {"status": "rejected: invalid_request", "reason": "shipper not found"}

    weight_kg = request.get("weight_kg", request.get("weightKg"))
    distance_km = request.get("distance_km", request.get("distanceKm"))
    declared_value = request.get("declared_value", request.get("declaredValue"))

    # store availability
    store_available = True
    store_flag = request.get("store_result", request.get("store_status",
                             request.get("quote_store_result", request.get("quote_store_status"))))
    if store_flag is not None and str(store_flag).strip().lower() in (
            "error", "unavailable", "down"):
        store_available = False

    screening_outcome = _screening_outcome_from_request(request)

    try:
        return api.request_quote(
            shipper_id, weight_kg, distance_km, declared_value,
            store_available=store_available,
            screening_outcome=screening_outcome,
        )
    except ValidationError as exc:
        return {"status": "rejected: invalid_request", "reason": str(exc)}
    except StoreUnavailableError as exc:
        return {"status": "error: store_unavailable", "reason": str(exc)}
    except Exception as exc:  # pragma: no cover
        return {"status": "error: %s" % exc}