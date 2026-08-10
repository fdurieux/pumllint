def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def risk_index(self, shipper_id, outcome=None):
        if outcome is None:
            return 0
        if _is_number(outcome):
            return int(outcome)
        try:
            return int(outcome)
        except (TypeError, ValueError):
            return 0


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send(self, shipper_id, kind, fail=False):
        if fail:
            return "delivery_failed"
        return "delivered"


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

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
        self._counter = 0

    def store_draft(self, request, fail=False):
        if fail:
            return "error"
        self._counter += 1
        quote_id = "Q-%04d" % self._counter
        self._records[quote_id] = dict(request)
        self._records[quote_id]["status"] = "draft"
        return quote_id

    def update_status(self, quote_id, status):
        if quote_id in self._records:
            self._records[quote_id]["status"] = status
        return "updated"


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening/pricing, returns outcome."""

    def __init__(self, store=None, screening=None, tariff=None, notification=None):
        self.store = store or QuoteStore()
        self.screening = screening or ScreeningService()
        self.tariff = tariff or TariffEngine()
        self.notification = notification or NotificationService()

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False
        weight = request.get("weight_kg")
        if not _is_number(weight) or not (3 <= weight <= 19400):
            return False
        distance = request.get("distance_km")
        if not _is_number(distance) or not (25 <= distance <= 7150):
            return False
        value = request.get("declared_value")
        if not _is_number(value) or not (50 <= value <= 83000):
            return False
        return True

    def request_quote(self, request):
        # Step 1: validate (DT-V)
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        # Step 2: store draft
        store_fail = str(request.get("store_status", request.get("store_result", ""))).lower() == "error"
        quote_id = self.store.store_draft(request, fail=store_fail)
        if quote_id == "error":
            return {"status": "error: store_unavailable"}

        shipper_id = request["shipper_id"]

        # Step 3: screening
        screening_outage = str(
            request.get("screening_status", "")
        ).lower() in ("error", "unavailable", "outage", "down")
        if "screening_result" in request and request.get("screening_result") in (
            "error", "unavailable", "outage", "down",
        ):
            screening_outage = True

        notif_fail = str(request.get("notification_status", "")).lower() == "error"

        if screening_outage:
            price = self.tariff.price(request["weight_kg"], request["distance_km"])
            self.store.update_status(quote_id, "held_unscreened")
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        risk = self.screening.risk_index(
            shipper_id, request.get("screening_result")
        )

        # Step 4-6: apply DT-S
        if risk <= ACCEPT_MAX:
            self.store.update_status(quote_id, "quoted")
            price = self.tariff.price(request["weight_kg"], request["distance_km"])
            self.notification.send(shipper_id, "quote_document", fail=notif_fail)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif REVIEW_MIN <= risk <= REVIEW_MAX:
            self.store.update_status(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:
            self.store.update_status(quote_id, "refused_screening")
            self.notification.send(shipper_id, "refusal_notice", fail=notif_fail)
            return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    api = QuoteApi()
    return api.request_quote(request)