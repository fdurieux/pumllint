import math


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id, risk_index=None, unavailable=False):
        if unavailable:
            raise RuntimeError("screening_unavailable")
        if risk_index is None:
            return 0
        return int(risk_index)


class TariffEngine:
    """Company tariff / pricing computation."""

    def price(self, weight_kg, distance_km):
        base = 0.87 * weight_kg + 1.13 * distance_km
        total = base
        if weight_kg > 1244:
            total += 316.00
        if distance_km >= 4912:
            total = total * 1.19
        return round(total, 2)


class QuoteStore:
    """Persistent store for quote drafts and updates."""

    def __init__(self):
        self._quotes = {}
        self._counter = 0

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value,
                   unavailable=False):
        if unavailable:
            raise RuntimeError("store_unavailable")
        self._counter += 1
        quote_id = "Q-%04d" % self._counter
        self._quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
        }
        return quote_id

    def updateQuote(self, quote_id, status, price=None):
        record = self._quotes.get(quote_id, {})
        record["status"] = status
        if price is not None:
            record["price"] = price
        self._quotes[quote_id] = record
        return quote_id


class NotificationService:
    """External notification provider (fire-and-forget)."""

    def sendQuoteDocument(self, shipper_id, quote_id, price, fail=False):
        if fail:
            raise RuntimeError("delivery_failed")
        return "sent"

    def sendRefusalNotice(self, shipper_id, quote_id, fail=False):
        if fail:
            raise RuntimeError("delivery_failed")
        return "sent"


class QuoteApi:
    """Front-line service orchestrating the quotation flow."""

    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def __init__(self, screening=None, tariff=None, store=None, notifier=None):
        self.screening = screening or ScreeningService()
        self.tariff = tariff or TariffEngine()
        self.store = store or QuoteStore()
        self.notifier = notifier or NotificationService()

    def _validate(self, req):
        shipper_id = req.get("shipper_id")
        if not shipper_id or not isinstance(shipper_id, str):
            return False
        weight = req.get("weight_kg")
        distance = req.get("distance_km")
        value = req.get("declared_value")
        if not isinstance(weight, (int, float)) or isinstance(weight, bool):
            return False
        if not isinstance(distance, (int, float)) or isinstance(distance, bool):
            return False
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False
        if not (3 <= weight <= 19400):
            return False
        if not (25 <= distance <= 7150):
            return False
        if not (50 <= value <= 83000):
            return False
        return True

    def requestQuote(self, req):
        # Step 1: validate
        if not self._validate(req):
            return {"status": "rejected: invalid_request"}

        shipper_id = req["shipper_id"]
        weight = req["weight_kg"]
        distance = req["distance_km"]
        value = req["declared_value"]

        # Step 2: store draft
        store_unavailable = self._is_error(req.get("store_status")) or \
            self._is_error(req.get("store_result"))
        try:
            quote_id = self.store.storeDraft(
                shipper_id, weight, distance, value,
                unavailable=store_unavailable)
        except RuntimeError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        screening_unavailable, risk_index = self._read_screening(req)

        if screening_unavailable:
            price = self.tariff.price(weight, distance)
            self.store.updateQuote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        risk = self.screening.screen(shipper_id, risk_index=risk_index)

        notify_fail = self._is_truthy(req.get("notification_status")) is False and \
            self._is_error(req.get("notification_status")) or \
            self._is_error(req.get("notification_result"))

        # Step 4/5/6: apply DT-S
        if risk <= self.ACCEPT_MAX:
            price = self.tariff.price(weight, distance)
            self.store.updateQuote(quote_id, "quoted", price)
            try:
                self.notifier.sendQuoteDocument(shipper_id, quote_id, price,
                                                fail=notify_fail)
            except RuntimeError:
                pass
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        if self.REVIEW_MIN <= risk <= self.REVIEW_MAX:
            self.store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # risk >= REFUSE_MIN
        self.store.updateQuote(quote_id, "refused_screening")
        try:
            self.notifier.sendRefusalNotice(shipper_id, quote_id,
                                            fail=notify_fail)
        except RuntimeError:
            pass
        return {"status": "refused_screening", "quote_id": quote_id}

    @staticmethod
    def _is_error(value):
        if isinstance(value, str):
            return value.lower() in ("error", "unavailable", "down", "outage")
        return False

    @staticmethod
    def _is_truthy(value):
        return bool(value)

    def _read_screening(self, req):
        for key in ("screening_result", "screening_status", "risk_index"):
            if key in req:
                v = req[key]
                if self._is_error(v):
                    return True, None
                if isinstance(v, bool):
                    continue
                if isinstance(v, (int, float)):
                    return False, int(v)
                if isinstance(v, str):
                    try:
                        return False, int(float(v))
                    except ValueError:
                        continue
        if req.get("screening_unavailable"):
            return True, None
        return False, 0


def handle(request: dict) -> dict:
    api = QuoteApi()
    return api.requestQuote(request)