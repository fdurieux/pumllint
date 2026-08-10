def _price(weight_kg, distance_km):
    base = 0.87 * weight_kg + 1.13 * distance_km
    total = base
    if weight_kg > 1244:
        total += 316.00
    if distance_km >= 4912:
        total *= 1.19
    return round(total, 2)


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def risk_index(self, shipper_id, hint=None):
        if hint is not None:
            return int(hint)
        return 0


class ScreeningUnavailable(Exception):
    pass


class StoreUnavailable(Exception):
    pass


class TariffEngine:
    """Computes the freight price per the published tariff rules (DT-P)."""

    def price(self, weight_kg, distance_km):
        return _price(weight_kg, distance_km)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._counter = 0

    def store_draft(self, request):
        self._counter += 1
        quote_id = "Q-{:06d}".format(self._counter)
        self._records[quote_id] = {"status": "draft", "request": request}
        return quote_id

    def update_status(self, quote_id, status):
        if quote_id in self._records:
            self._records[quote_id]["status"] = status
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send(self, shipper_id, message, fail=False):
        if fail:
            return "failed"
        return "delivered"


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

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
        # 1. Validate (DT-V)
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        # 2. Store draft
        if _store_fails(request):
            return {"status": "error: store_unavailable"}
        quote_id = self.store.store_draft(request)

        shipper_id = request["shipper_id"]
        weight = request["weight_kg"]
        distance = request["distance_km"]

        # 3. Screening
        if _screening_unavailable(request):
            price = self.tariff.price(weight, distance)
            self.store.update_status(quote_id, "held_unscreened")
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        risk_index = self.screening.risk_index(
            shipper_id, request.get("screening_result")
        )

        # 4/5/6 Apply screening decision
        if risk_index <= ACCEPT_MAX:
            self.store.update_status(quote_id, "quoted")
            price = self.tariff.price(weight, distance)
            self.notification.send(
                shipper_id, "quote_document", fail=_notification_fails(request)
            )
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif risk_index <= REVIEW_MAX:
            self.store.update_status(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:
            self.store.update_status(quote_id, "refused_screening")
            self.notification.send(
                shipper_id, "refusal_notice", fail=_notification_fails(request)
            )
            return {"status": "refused_screening", "quote_id": quote_id}


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _store_fails(request):
    status = str(request.get("store_status") or request.get("store_result") or "").lower()
    if status in ("error", "unavailable", "down", "failed"):
        return True
    if request.get("store_exists") is False or request.get("store_found") is False:
        return True
    return False


def _screening_unavailable(request):
    status = str(request.get("screening_status") or "").lower()
    if status in ("error", "unavailable", "down", "outage", "timeout"):
        return True
    result = request.get("screening_result")
    if isinstance(result, str) and result.lower() in (
        "error",
        "unavailable",
        "down",
        "outage",
    ):
        return True
    return False


def _notification_fails(request):
    status = str(
        request.get("notification_status") or request.get("notification_result") or ""
    ).lower()
    return status in ("error", "unavailable", "failed", "down")


def handle(request: dict) -> dict:
    api = QuoteApi()
    return api.request_quote(dict(request))