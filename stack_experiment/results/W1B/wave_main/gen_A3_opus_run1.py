import uuid


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class InvalidRequestError(Exception):
    pass


# --- DT-S symbolic bounds ---
ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

# --- DT-V bounds ---
WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000

_ERROR_WORDS = {"error", "unavailable", "down", "fail", "failure", "lapsed"}


class TariffEngine:
    """Computes the freight price per DT-P."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km  # P1
        if weight_kg > 1244:                            # P2
            result += 316.00
        if distance_km >= 4912:                         # P3
            result *= 1.19
        return round(result, 2)                         # P4


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, store_outcome):
        if str(store_outcome).lower() in _ERROR_WORDS:
            raise StoreUnavailableError()
        return "Q-" + uuid.uuid4().hex[:12]

    def update_quote(self, quote_id, status, price=None):
        return {"quote_id": quote_id, "status": status, "price": price}


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, screening_outcome):
        val = screening_outcome
        if isinstance(val, str):
            low = val.lower()
            if low in _ERROR_WORDS:
                raise ScreeningUnavailableError()
            try:
                return int(val)
            except ValueError:
                # non-numeric non-error word (e.g. "approved"/"assessed") -> accept band
                if low in ("approved", "active", "assessed", "stored"):
                    return 0
                raise ScreeningUnavailableError()
        return int(val)


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class QuoteApi:
    """Receives quote requests, orchestrates screening and pricing, returns outcome."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    # --- DT-V validation ---
    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            raise InvalidRequestError()
        if request.get("shipper_exists") is False or request.get("shipper_found") is False:
            raise InvalidRequestError()
        weight = request.get("weight_kg")
        distance = request.get("distance_km")
        value = request.get("declared_value")
        for v in (weight, distance, value):
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise InvalidRequestError()
        if not (WEIGHT_MIN <= weight <= WEIGHT_MAX):
            raise InvalidRequestError()
        if not (DISTANCE_MIN <= distance <= DISTANCE_MAX):
            raise InvalidRequestError()
        if not (VALUE_MIN <= value <= VALUE_MAX):
            raise InvalidRequestError()

    @staticmethod
    def _store_outcome(request):
        for k in ("quote_store_result", "store_result", "quote_store_status", "store_status"):
            if k in request:
                return request[k]
        return "stored"

    @staticmethod
    def _screening_outcome(request):
        for k in ("risk_index", "screening_service_result", "screening_result",
                  "screening_service_status", "screening_status"):
            if k in request:
                return request[k]
        return 0

    def request_quote(self, request):
        # 1. Validate (DT-V)
        try:
            self._validate(request)
        except InvalidRequestError:
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight = request["weight_kg"]
        distance = request["distance_km"]
        value = request["declared_value"]

        # 2. Store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight, distance, value, self._store_outcome(request)
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # 3. Screening
        try:
            risk_index = self.screening_service.screen(
                shipper_id, self._screening_outcome(request)
            )
        except ScreeningUnavailableError:
            # DT-S note 5: price anyway, hold, no notification
            price = self.tariff_engine.price(weight, distance)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {"status": "held_unscreened", "quote_id": quote_id,
                    "price": price, "hold": True}

        # 4/5/6. Apply DT-S decision
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight, distance)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self._notify_quote(shipper_id, quote_id, price)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            self._notify_refusal(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}

    # Notification is fire-and-forget (DT-S note 4)
    def _notify_quote(self, shipper_id, quote_id, price):
        try:
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
        except Exception:
            pass

    def _notify_refusal(self, shipper_id, quote_id):
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            pass


def _build_api():
    return QuoteApi(
        tariff_engine=TariffEngine(),
        quote_store=QuoteStore(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )


def handle(request: dict) -> dict:
    api = _build_api()
    return api.request_quote(request)