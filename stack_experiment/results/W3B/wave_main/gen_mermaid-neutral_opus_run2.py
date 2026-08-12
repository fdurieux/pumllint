def _to_camel(alias):
    return "".join(part.capitalize() for part in alias.split("_"))


# Screening thresholds (decision table DT-S)
ACCEPT_MAX = 29
REVIEW_MIN = 30
REVIEW_MAX = 69
REFUSE_MIN = 70

# Validation bounds (decision table DT-V)
WEIGHT_MIN = 1
WEIGHT_MAX = 30000
DISTANCE_MIN = 1
DISTANCE_MAX = 5000
VALUE_MIN = 1
VALUE_MAX = 10_000_000


class ScreeningService:
    """External denied-party screening provider (returns a shipper risk index)."""

    def screen(self, shipper_id, outcome=None):
        if outcome is None:
            return 10
        if isinstance(outcome, (int, float)):
            return outcome
        word = str(outcome).lower()
        if word in ("error", "unavailable", "timeout", "down"):
            return "screeningUnavailableError"
        if word in ("approved", "active", "clear", "accept"):
            return 10
        if word in ("review", "assessed", "hold", "manual"):
            return 50
        if word in ("declined", "refused", "denied", "refuse"):
            return 90
        # try numeric string
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


class TariffEngine:
    """Computes the freight price from weight and distance."""

    BASE_RATE = 5.0
    WEIGHT_RATE = 0.10
    DISTANCE_RATE = 0.75

    def price(self, weight_kg, distance_km):
        return round(
            self.BASE_RATE
            + self.WEIGHT_RATE * weight_kg
            + self.DISTANCE_RATE * distance_km,
            2,
        )


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, available=True):
        if not available:
            return "storeUnavailableError"
        self._seq += 1
        quote_id = "Q-%04d" % self._seq
        self._records[quote_id] = {
            "shipperId": shipper_id,
            "weightKg": weight_kg,
            "distanceKm": distance_km,
            "declaredValue": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        record = self._records.get(quote_id)
        if record is None:
            return "unknownQuote"
        record["status"] = status
        if price_amount is not None:
            record["price"] = price_amount
        return "updatedQuote"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

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
        if not (VALUE_MIN <= v <= VALUE_MAX):
            return False
        return True

    def request_quote(
        self,
        shipper_id,
        weight_kg,
        distance_km,
        declared_value,
        store_available=True,
        screening_outcome=None,
    ):
        # Validation (DT-V)
        if not self._valid(weight_kg, distance_km, declared_value):
            return {"status": "error: invalid_request"}

        # Store draft
        quote_id = self.quote_store.store_draft(
            shipper_id, weight_kg, distance_km, declared_value, available=store_available
        )
        if quote_id == "storeUnavailableError":
            return {"status": "error: store_unavailable"}

        # Screening (DT-S)
        risk_index = self.screening_service.screen(shipper_id, screening_outcome)

        if risk_index == "screeningUnavailableError":
            # Screening outage: priced, held on hold, not notified (note 5)
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "statusHeldUnscreened", price_amount)
            return {
                "status": "held",
                "quoteId": quote_id,
                "price": price_amount,
            }

        if risk_index <= ACCEPT_MAX:
            # Accept: price, quote, notify (note ...)
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "statusQuoted", price_amount)
            self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            return {
                "status": "confirmed",
                "quoteId": quote_id,
                "price": price_amount,
            }

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # Review hold: no pricing, no notification (note 1)
            self.quote_store.update_quote(quote_id, "statusReviewHold")
            return {"status": "review", "quoteId": quote_id}

        # riskIndex >= REFUSE_MIN: refuse, notify, no pricing (note 2)
        self.quote_store.update_quote(quote_id, "statusRefusedScreening")
        self.notification_service.send_refusal_notice(shipper_id, quote_id)
        return {"status": "rejected", "quoteId": quote_id}


def handle(request: dict) -> dict:
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)

    shipper_id = request.get("shipper_id", request.get("shipperId", "unknown"))
    weight_kg = request.get("weight_kg", request.get("weightKg"))
    distance_km = request.get("distance_km", request.get("distanceKm"))
    declared_value = request.get("declared_value", request.get("declaredValue"))

    # Store availability
    store_available = True
    if "store_result" in request or "store_status" in request:
        val = str(request.get("store_result", request.get("store_status"))).lower()
        if val in ("error", "unavailable", "down", "fail", "failed"):
            store_available = False

    # Existence flag for shipper
    if request.get("shipper_exists") is False or request.get("shipper_found") is False:
        return {"status": "error: shipper_not_found"}

    # Screening outcome
    screening_outcome = None
    if "screening_result" in request:
        screening_outcome = request["screening_result"]
    elif "screening_status" in request:
        screening_outcome = request["screening_status"]

    return api.request_quote(
        shipper_id,
        weight_kg,
        distance_km,
        declared_value,
        store_available=store_available,
        screening_outcome=screening_outcome,
    )