def _num(v):
    try:
        if isinstance(v, bool):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, risk_index=12, unavailable=False):
        if unavailable:
            raise RuntimeError("screening_unavailable")
        return int(risk_index)


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff rules."""

    PER_KG = 0.87
    PER_KM = 1.13
    HEAVY_THRESHOLD = 1244
    HEAVY_SURCHARGE = 316.00
    LONGHAUL_THRESHOLD = 4912
    LONGHAUL_FACTOR = 1.19

    def price(self, weight_kg, distance_km):
        total = self.PER_KG * weight_kg + self.PER_KM * distance_km
        if weight_kg > self.HEAVY_THRESHOLD:
            total += self.HEAVY_SURCHARGE
        if distance_km >= self.LONGHAUL_THRESHOLD:
            total *= self.LONGHAUL_FACTOR
        return round(total, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, unavailable=False):
        if unavailable:
            raise RuntimeError("store_unavailable")
        self._seq += 1
        quote_id = "Q-%04d" % self._seq
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
        rec = self._records.get(quote_id)
        if rec is None:
            raise RuntimeError("unknown_quote")
        rec["status"] = status
        if price is not None:
            rec["price"] = price
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount, fail=False):
        if fail:
            raise RuntimeError("delivery_failed")
        return "delivered"

    def send_refusal_notice(self, shipper_id, quote_id, fail=False):
        if fail:
            raise RuntimeError("delivery_failed")
        return "delivered"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def __init__(self, store=None, tariff=None, screening=None, notification=None):
        self.store = store or QuoteStore()
        self.tariff = tariff or TariffEngine()
        self.screening = screening or ScreeningService()
        self.notification = notification or NotificationService()

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False
        if weight_kg is None or not (3 <= weight_kg <= 19400):
            return False
        if distance_km is None or not (25 <= distance_km <= 7150):
            return False
        if declared_value is None or not (50 <= declared_value <= 83000):
            return False
        return True

    def request_quote(self, request):
        shipper_id = request.get("shipper_id")
        weight_kg = _num(request.get("weight_kg"))
        distance_km = _num(request.get("distance_km"))
        declared_value = _num(request.get("declared_value"))

        # Step 1: validate (DT-V)
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # Step 2: store draft
        store_unavailable = self._flag(request, "store", bad_words={"error", "unavailable", "down", "fail"})
        try:
            quote_id = self.store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, unavailable=store_unavailable
            )
        except RuntimeError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        screening_unavailable = self._flag(request, "screening", bad_words={"error", "unavailable", "down", "fail"})
        try:
            risk_index = self.screening.screen(
                shipper_id,
                risk_index=self._risk_value(request),
                unavailable=screening_unavailable,
            )
        except RuntimeError:
            # Screening outage: price anyway, hold, no notification
            price_amount = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4/5/6: apply screening decision
        notify_fail = self._flag(request, "notification", bad_words={"error", "fail", "undelivered"})

        if risk_index <= self.ACCEPT_MAX:
            price_amount = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "quoted", price_amount)
            try:
                self.notification.send_quote_document(shipper_id, quote_id, price_amount, fail=notify_fail)
            except RuntimeError:
                pass  # fire-and-forget
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}

        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # risk_index >= REFUSE_MIN
        self.store.update_quote(quote_id, "refused_screening")
        try:
            self.notification.send_refusal_notice(shipper_id, quote_id, fail=notify_fail)
        except RuntimeError:
            pass  # fire-and-forget
        return {"status": "refused_screening", "quote_id": quote_id}

    @staticmethod
    def _flag(request, system, bad_words):
        for key in (system + "_result", system + "_status"):
            val = request.get(key)
            if isinstance(val, str) and val.strip().lower() in bad_words:
                return True
        return False

    @staticmethod
    def _risk_value(request):
        for key in ("screening_result", "screening_status", "risk_index"):
            val = request.get(key)
            n = _num(val)
            if n is not None:
                return int(n)
        return 12


def handle(request: dict) -> dict:
    api = QuoteApi()
    return api.request_quote(request or {})