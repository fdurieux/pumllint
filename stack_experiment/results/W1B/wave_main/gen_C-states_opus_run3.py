def _to_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, outcome=None):
        # outcome may be a number (risk index) or an outage marker.
        if outcome in ("error", "unavailable", "down", "outage", "timeout"):
            raise RuntimeError("screening_unavailable")
        num = _to_number(outcome)
        if num is None:
            return 0
        return int(num)


class TariffEngine:
    """Computes the freight price per the published tariff rules (DT-P)."""

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
        self._seq = 0
        self._records = {}

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, available=True):
        if not available:
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

    def update_quote(self, quote_id, status, price=None):
        rec = self._records.get(quote_id)
        if rec is not None:
            rec["status"] = status
            if price is not None:
                rec["price"] = price
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price, deliver=True):
        # Fire-and-forget: failures never change the response.
        return "sent" if deliver else "failed"

    def send_refusal_notice(self, shipper_id, quote_id, deliver=True):
        return "sent" if deliver else "failed"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def __init__(self, screening_service, tariff_engine, quote_store, notification_service):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id or not isinstance(shipper_id, str):
            return False
        w = _to_number(weight_kg)
        if w is None or not (3 <= w <= 19400):
            return False
        d = _to_number(distance_km)
        if d is None or not (25 <= d <= 7150):
            return False
        v = _to_number(declared_value)
        if v is None or not (50 <= v <= 83000):
            return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value,
                      store_available=True, screening_outcome=None, notify_deliver=True):
        # Step 1: validate
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        weight_kg = float(weight_kg)
        distance_km = float(distance_km)
        declared_value = float(declared_value)

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, available=store_available)
        except RuntimeError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id, outcome=screening_outcome)
        except RuntimeError:
            # Screening outage: price anyway, hold, no notification.
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {"status": "held_unscreened", "quote_id": quote_id,
                    "price": price, "hold": True}

        # Step 4/5/6: apply screening decision
        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price, deliver=notify_deliver)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(
                shipper_id, quote_id, deliver=notify_deliver)
            return {"status": "refused_screening", "quote_id": quote_id}


def _store_available(request):
    for key in ("store_status", "store_result", "quote_store_status", "quote_store_result"):
        if key in request:
            val = str(request[key]).lower()
            if val in ("stored", "ok", "available", "success"):
                return True
            if val in ("error", "unavailable", "down", "fail", "failed"):
                return False
    if request.get("store_exists") is False:
        return False
    return True


def _screening_outcome(request):
    for key in ("screening_result", "screening_status", "screening_service_result",
                "screening_service_status"):
        if key in request:
            return request[key]
    if "risk_index" in request:
        return request["risk_index"]
    return None


def _notify_deliver(request):
    for key in ("notification_status", "notification_result",
                "notification_service_status", "notification_service_result"):
        if key in request:
            val = str(request[key]).lower()
            if val in ("error", "unavailable", "down", "fail", "failed"):
                return False
    return True


def handle(request: dict) -> dict:
    api = QuoteApi(
        screening_service=ScreeningService(),
        tariff_engine=TariffEngine(),
        quote_store=QuoteStore(),
        notification_service=NotificationService(),
    )
    return api.request_quote(
        shipper_id=request.get("shipper_id"),
        weight_kg=request.get("weight_kg"),
        distance_km=request.get("distance_km"),
        declared_value=request.get("declared_value"),
        store_available=_store_available(request),
        screening_outcome=_screening_outcome(request),
        notify_deliver=_notify_deliver(request),
    )