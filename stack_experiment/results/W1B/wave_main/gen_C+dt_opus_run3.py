def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return None
    return None


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
        base = 0.87 * weight_kg + 1.13 * distance_km  # P1
        total = base
        if weight_kg > 1244:  # P2 heavy surcharge
            total += 316.00
        if distance_km >= 4912:  # P3 long-haul multiplier, after P2
            total *= 1.19
        return round(total, 2)  # P4


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._seq = 0

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value, ok=True):
        if not ok:
            raise RuntimeError("store_unavailable")
        self._seq += 1
        quote_id = "Q%d" % self._seq
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def updateQuote(self, quote_id, status, price_amount=None):
        rec = self._records.get(quote_id)
        if rec is None:
            rec = {}
            self._records[quote_id] = rec
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        return quote_id


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id:  # V1
            return False
        w = _num(weight_kg)
        if w is None or not (3 <= w <= 19400):  # V2
            return False
        d = _num(distance_km)
        if d is None or not (25 <= d <= 7150):  # V3
            return False
        v = _num(declared_value)
        if v is None or not (50 <= v <= 83000):  # V4
            return False
        return True

    def requestQuote(self, request):
        shipper_id = request.get("shipper_id")
        weight_kg = request.get("weight_kg")
        distance_km = request.get("distance_km")
        declared_value = request.get("declared_value")

        # DT-V validation
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        weight_kg = _num(weight_kg)
        distance_km = _num(distance_km)
        declared_value = _num(declared_value)

        # storeDraft
        store_ok = self._flag(request, "store", ok_words=("stored", "ok", "active"))
        try:
            quote_id = self.quote_store.storeDraft(
                shipper_id, weight_kg, distance_km, declared_value, ok=store_ok
            )
        except RuntimeError:
            return {"status": "error: store_unavailable"}

        # Screening
        screening_status = request.get("screening_status", request.get("screening_result"))
        if isinstance(screening_status, str) and screening_status in ("error", "unavailable", "down"):
            # DT-S note 5: screening outage -> price, hold, not notified
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        risk_index = self._risk_index(request)
        if risk_index is None:
            # unable to determine risk -> treat as screening outage
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price_amount)
            self.notification_service.sendQuoteDocument(shipper_id, quote_id, price_amount)
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.updateQuote(quote_id, "refused_screening")
            self.notification_service.sendRefusalNotice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}

    def _flag(self, request, name, ok_words):
        status = request.get(name + "_status", request.get(name + "_result"))
        exists = request.get(name + "_exists", request.get(name + "_found"))
        if exists is False:
            return False
        if isinstance(status, str):
            if status in ("error", "unavailable", "down"):
                return False
            if status in ok_words:
                return True
        return True

    def _risk_index(self, request):
        val = request.get("screening_result", request.get("screening_status"))
        n = _num(val)
        if n is not None:
            return int(n)
        if isinstance(val, str):
            mapping = {
                "approved": 0,
                "accept": 0,
                "active": 0,
                "review": REVIEW_MIN,
                "declined": REFUSE_MIN,
                "refused": REFUSE_MIN,
                "assessed": 0,
            }
            if val in mapping:
                return self.screening_service.screen(
                    request.get("shipper_id"), mapping[val]
                )
        return None


def handle(request: dict) -> dict:
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)
    return api.requestQuote(request)