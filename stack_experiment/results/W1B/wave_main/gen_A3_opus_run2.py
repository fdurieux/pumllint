def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, request=None):
        request = request or {}
        result = request.get("screening_service_result",
                             request.get("screening_service_status"))
        if isinstance(result, str):
            r = result.strip().lower()
            if r in ("error", "unavailable", "down", "outage", "timeout"):
                raise RuntimeError("screening_unavailable")
            try:
                return int(float(r))
            except ValueError:
                return 0
        if result is None:
            return 0
        return int(float(result))


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            result += 316.00
        if distance_km >= 4912:
            result *= 1.19
        return round(result, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._seq = 0
        self._records = {}

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value, request=None):
        request = request or {}
        result = request.get("quote_store_result",
                             request.get("quote_store_status"))
        if isinstance(result, str) and result.strip().lower() in (
                "error", "unavailable", "down", "fail", "failure"):
            raise RuntimeError("store_unavailable")
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

    def updateQuote(self, quote_id, status, price=None):
        rec = self._records.get(quote_id, {})
        rec["status"] = status
        if price is not None:
            rec["price"] = price
        self._records[quote_id] = rec
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount):
        return "sent"

    def sendRefusalNotice(self, shipper_id, quote_id):
        return "sent"


class QuoteApi:
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def __init__(self, tariff_engine=None, quote_store=None,
                 screening_service=None, notification_service=None):
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False
        w = _num(weight_kg)
        if w is None or not (3 <= w <= 19400):
            return False
        d = _num(distance_km)
        if d is None or not (25 <= d <= 7150):
            return False
        v = _num(declared_value)
        if v is None or not (50 <= v <= 83000):
            return False
        return True

    def requestQuote(self, request):
        shipper_id = request.get("shipper_id")
        weight_kg = request.get("weight_kg")
        distance_km = request.get("distance_km")
        declared_value = request.get("declared_value")

        # Step 1: validate (DT-V)
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        weight_kg = _num(weight_kg)
        distance_km = _num(distance_km)
        declared_value = _num(declared_value)

        # Step 2: store draft
        try:
            quote_id = self.quote_store.storeDraft(
                shipper_id, weight_kg, distance_km, declared_value, request)
        except RuntimeError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id, request)
        except RuntimeError:
            # Screening outage: price anyway, hold, no notification (DT-S note 5)
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4-6: apply screening decision
        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price_amount)
            self.notification_service.sendQuoteDocument(shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.updateQuote(quote_id, "refused_screening")
            self.notification_service.sendRefusalNotice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    api = QuoteApi()
    try:
        return api.requestQuote(request)
    except Exception as exc:  # pragma: no cover
        return {"status": "error: %s" % exc}