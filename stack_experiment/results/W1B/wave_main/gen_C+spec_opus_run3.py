def _to_camel(alias):
    return "".join(p.capitalize() for p in alias.split("_"))


# --- Decision table constants (DT-V, DT-S, DT-P) ---

# DT-V: validation bounds
WEIGHT_MIN, WEIGHT_MAX = 1.0, 26000.0
DISTANCE_MIN, DISTANCE_MAX = 1.0, 3000.0
VALUE_MIN, VALUE_MAX = 0.0, 1_000_000.0

# DT-S: screening bands (higher risk index is worse)
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 69
REFUSE_MIN = 70

# DT-P: pricing coefficients
BASE_FEE = 25.0
RATE_PER_KG = 0.05
RATE_PER_KM = 0.10


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, result=None, status=None):
        if status == "error" or result == "error":
            raise ScreeningUnavailableError("screening service unavailable")
        if result is None:
            return 0
        return int(result)


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        return "delivered"

    def sendRefusalNotice(self, shipper_id, quote_id):
        return "delivered"


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff rules."""

    def price(self, weight_kg, distance_km):
        return round(BASE_FEE + RATE_PER_KG * weight_kg + RATE_PER_KM * distance_km, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._quotes = {}
        self._counter = 0

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value, status=None):
        if status == "error":
            raise StoreUnavailableError("quote store unavailable")
        self._counter += 1
        quote_id = "Q-%04d" % self._counter
        self._quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def updateQuote(self, quote_id, status, price_amount=None):
        record = self._quotes.get(quote_id)
        if record is None:
            raise StoreUnavailableError("quote not found")
        record["status"] = status
        if price_amount is not None:
            record["price"] = price_amount
        return quote_id


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class InvalidRequestError(Exception):
    pass


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, tariff_engine=None, quote_store=None,
                 screening_service=None, notification_service=None):
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    def _validate(self, request):
        for key in ("shipper_id", "weight_kg", "distance_km", "declared_value"):
            if request.get(key) is None:
                raise InvalidRequestError("missing %s" % key)
            if key.endswith("_exists") or key.endswith("_found"):
                continue
        if request.get("shipper_exists") is False or request.get("shipper_found") is False:
            raise InvalidRequestError("shipper not found")

        try:
            weight = float(request["weight_kg"])
            distance = float(request["distance_km"])
            value = float(request["declared_value"])
        except (TypeError, ValueError):
            raise InvalidRequestError("non-numeric field")

        if not (WEIGHT_MIN <= weight <= WEIGHT_MAX):
            raise InvalidRequestError("weight out of bounds")
        if not (DISTANCE_MIN <= distance <= DISTANCE_MAX):
            raise InvalidRequestError("distance out of bounds")
        if not (VALUE_MIN <= value <= VALUE_MAX):
            raise InvalidRequestError("declared_value out of bounds")

        if not str(request["shipper_id"]).strip():
            raise InvalidRequestError("empty shipper_id")

        return weight, distance, value

    def requestQuote(self, request):
        # Step 1: validate
        try:
            weight, distance, value = self._validate(request)
        except InvalidRequestError:
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]

        # Step 2: store draft
        try:
            quote_id = self.quote_store.storeDraft(
                shipper_id, weight, distance, value,
                status=request.get("store_status") or request.get("store_result"),
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        screen_input = request.get("screening_result")
        if screen_input is None:
            screen_input = request.get("screening_status")
        try:
            risk_index = self.screening_service.screen(
                shipper_id,
                result=request.get("screening_result"),
                status=request.get("screening_status"),
            )
        except ScreeningUnavailableError:
            # Screening outage: price anyway, hold, no notification
            price_amount = self.tariff_engine.price(weight, distance)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4-6: apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight, distance)
            self.quote_store.updateQuote(quote_id, "quoted", price_amount)
            self._notify_quote(shipper_id, quote_id, price_amount)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price_amount,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.updateQuote(quote_id, "refused_screening")
            self._notify_refusal(shipper_id, quote_id)
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }

    def _notify_quote(self, shipper_id, quote_id, price_amount):
        try:
            self.notification_service.sendQuoteDocument(shipper_id, quote_id, price_amount)
        except Exception:
            pass  # fire-and-forget

    def _notify_refusal(self, shipper_id, quote_id):
        try:
            self.notification_service.sendRefusalNotice(shipper_id, quote_id)
        except Exception:
            pass  # fire-and-forget


def handle(request: dict) -> dict:
    api = QuoteApi()
    return api.requestQuote(request)