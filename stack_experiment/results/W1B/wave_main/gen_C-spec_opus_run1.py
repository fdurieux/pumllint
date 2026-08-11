def ACCEPT_MAX(): return 41

ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000


class ScreeningError(Exception):
    pass


class StoreError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, risk_index=None, status=None):
        if status in ("error", "unavailable") or risk_index == "error":
            raise ScreeningError("screening_unavailable")
        if risk_index is None:
            return 0
        return int(risk_index)


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km  # P1
        if weight_kg > 1244:  # P2
            result += 316.00
        if distance_km >= 4912:  # P3
            result *= 1.19
        return round(result, 2)  # P4


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._seq = 0
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, status=None):
        if status in ("error", "unavailable"):
            raise StoreError("store_unavailable")
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
        rec = self._records.get(quote_id)
        if rec is None:
            raise StoreError("unknown_quote")
        rec["status"] = status
        if price is not None:
            rec["price"] = price
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and pricing."""

    def __init__(self, store, screening, tariff, notification):
        self.store = store
        self.screening = screening
        self.tariff = tariff
        self.notification = notification

    def _validate(self, req):
        shipper_id = req.get("shipper_id")
        if not shipper_id or not str(shipper_id).strip():
            return False
        for key, lo, hi in (
            ("weight_kg", WEIGHT_MIN, WEIGHT_MAX),
            ("distance_km", DISTANCE_MIN, DISTANCE_MAX),
            ("declared_value", VALUE_MIN, VALUE_MAX),
        ):
            val = req.get(key)
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                return False
            if not (lo <= val <= hi):
                return False
        return True

    def request_quote(self, req):
        # DT-V validation
        if not self._validate(req):
            return {"status": "rejected: invalid_request"}

        shipper_id = req["shipper_id"]
        weight_kg = req["weight_kg"]
        distance_km = req["distance_km"]
        declared_value = req["declared_value"]

        # store draft
        try:
            quote_id = self.store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value,
                status=req.get("store_result") or req.get("store_status"),
            )
        except StoreError:
            return {"status": "error: store_unavailable"}

        # screening
        try:
            risk_index = self.screening.screen(
                shipper_id,
                risk_index=req.get("screening_result"),
                status=req.get("screening_status"),
            )
        except ScreeningError:
            # DT-S note 5: screening outage -> price and hold, no notification
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        if risk_index <= ACCEPT_MAX:
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "quoted", price)
            self.notification.send_quote_document(shipper_id, quote_id, price)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.store.update_quote(quote_id, "refused_screening")
            self.notification.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    store = QuoteStore()
    screening = ScreeningService()
    tariff = TariffEngine()
    notification = NotificationService()
    api = QuoteApi(store, screening, tariff, notification)
    return api.request_quote(dict(request))