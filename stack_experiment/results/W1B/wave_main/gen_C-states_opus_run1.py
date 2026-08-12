import uuid


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, risk_index=0):
        return risk_index


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        return "sent"

    def sendRefusalNotice(self, shipper_id, quote_id):
        return "sent"


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff rules."""

    def price(self, weight_kg, distance_km):
        base = 0.87 * weight_kg + 1.13 * distance_km
        total = base
        if weight_kg > 1244:
            total += 316.00
        if distance_km >= 4912:
            total *= 1.19
        return round(total, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value, available=True):
        if not available:
            raise StoreUnavailableError("store_unavailable")
        quote_id = str(uuid.uuid4())
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
        }
        return quote_id

    def updateQuote(self, quote_id, status, price_amount=None):
        rec = self._records.get(quote_id, {})
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        self._records[quote_id] = rec
        return quote_id


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class InvalidRequestError(Exception):
    pass


# DT-S symbolic bounds
ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, store=None, screening=None, tariff=None, notification=None):
        self.store = store or QuoteStore()
        self.screening = screening or ScreeningService()
        self.tariff = tariff or TariffEngine()
        self.notification = notification or NotificationService()

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:
            raise InvalidRequestError("V1")
        if not isinstance(weight_kg, (int, float)) or not (3 <= weight_kg <= 19400):
            raise InvalidRequestError("V2")
        if not isinstance(distance_km, (int, float)) or not (25 <= distance_km <= 7150):
            raise InvalidRequestError("V3")
        if not isinstance(declared_value, (int, float)) or not (50 <= declared_value <= 83000):
            raise InvalidRequestError("V4")

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value,
                     store_available=True, screening_available=True, risk_index=0):
        # Step 1: validate
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except InvalidRequestError:
            return {"status": "rejected: invalid_request"}

        # Step 2: store draft
        try:
            quote_id = self.store.storeDraft(
                shipper_id, weight_kg, distance_km, declared_value, available=store_available)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        if not screening_available:
            price_amount = self.tariff.price(weight_kg, distance_km)
            self.store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        risk = self.screening.screen(shipper_id, risk_index)

        # Step 4-6: apply DT-S
        if risk <= ACCEPT_MAX:
            price_amount = self.tariff.price(weight_kg, distance_km)
            self.store.updateQuote(quote_id, "quoted", price_amount)
            try:
                self.notification.sendQuoteDocument(shipper_id, quote_id, price_amount)
            except Exception:
                pass
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
        elif REVIEW_MIN <= risk <= REVIEW_MAX:
            self.store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk >= REFUSE_MIN
            self.store.updateQuote(quote_id, "refused_screening")
            try:
                self.notification.sendRefusalNotice(shipper_id, quote_id)
            except Exception:
                pass
            return {"status": "refused_screening", "quote_id": quote_id}


def _word_indicates_unavailable(val):
    if val is None:
        return False
    return str(val).lower() in ("error", "unavailable", "down", "lapsed", "failed")


def handle(request: dict) -> dict:
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    # store availability
    store_available = True
    if "store_exists" in request and not request["store_exists"]:
        store_available = False
    store_signal = request.get("store_result", request.get("store_status"))
    if store_signal is not None and str(store_signal).lower() not in ("stored", "ok", "available"):
        if _word_indicates_unavailable(store_signal):
            store_available = False

    # screening availability and risk index
    screening_available = True
    risk_index = 0
    screening_signal = request.get("screening_result", request.get("screening_status"))
    if request.get("screening_score") is not None:
        try:
            risk_index = int(request["screening_score"])
        except (ValueError, TypeError):
            pass
    if request.get("risk_index") is not None:
        try:
            risk_index = int(request["risk_index"])
        except (ValueError, TypeError):
            pass
    if screening_signal is not None:
        s = str(screening_signal).lower()
        if _word_indicates_unavailable(screening_signal):
            screening_available = False
        else:
            try:
                risk_index = int(screening_signal)
            except (ValueError, TypeError):
                pass

    api = QuoteApi()
    return api.requestQuote(
        shipper_id, weight_kg, distance_km, declared_value,
        store_available=store_available,
        screening_available=screening_available,
        risk_index=risk_index,
    )