def _round2(x):
    return round(x + 1e-9, 2)


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, config=None):
        config = config or {}
        self._status = str(config.get("screening_status", "")).lower()
        self._result = config.get("screening_result", None)

    def screen(self, shipper_id):
        if self._status in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailableError("screening service unavailable")
        if self._result is not None:
            try:
                return float(self._result)
            except (TypeError, ValueError):
                if str(self._result).lower() in ("error", "unavailable"):
                    raise ScreeningUnavailableError("screening service unavailable")
                return 10.0
        return 10.0


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff."""

    WEIGHT_RATE = 0.87
    DISTANCE_RATE = 1.13

    def price(self, weight_kg, distance_km):
        return _round2(self.WEIGHT_RATE * weight_kg + self.DISTANCE_RATE * distance_km)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, config=None):
        config = config or {}
        self._status = str(config.get("store_status", "")).lower()
        self._records = {}
        self._counter = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        if self._status in ("error", "unavailable", "down"):
            raise StoreUnavailableError("quote store unavailable")
        self._counter += 1
        quote_id = "Q-%04d" % self._counter
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
        rec = self._records.get(quote_id, {})
        rec["status"] = status
        if price is not None:
            rec["price"] = price
        self._records[quote_id] = rec
        return "updated:" + quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, config=None):
        config = config or {}
        self._status = str(config.get("notification_status", "")).lower()

    def _deliver(self):
        if self._status in ("error", "fail", "failed", "unavailable"):
            raise RuntimeError("notification delivery failed")
        return True

    def send_quote_document(self, shipper_id, quote_id, price):
        return self._deliver()

    def send_refusal_notice(self, shipper_id, quote_id):
        return self._deliver()


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    # DT-V validation bounds
    WEIGHT_MIN = 5.0
    WEIGHT_MAX = 26000.0
    DISTANCE_MIN = 1.0
    DISTANCE_MAX = 4000.0
    VALUE_MIN = 1.0
    VALUE_MAX = 10_000_000.0

    # DT-S screening bands
    ACCEPT_MAX = 30.0
    REVIEW_MIN = 31.0
    REVIEW_MAX = 69.0
    REFUSE_MIN = 70.0

    def __init__(self, store, screening, tariff, notifier):
        self.store = store
        self.screening = screening
        self.tariff = tariff
        self.notifier = notifier

    def _valid(self, weight_kg, distance_km, declared_value):
        try:
            w = float(weight_kg)
            d = float(distance_km)
            v = float(declared_value)
        except (TypeError, ValueError):
            return False
        if not (self.WEIGHT_MIN <= w <= self.WEIGHT_MAX):
            return False
        if not (self.DISTANCE_MIN <= d <= self.DISTANCE_MAX):
            return False
        if not (self.VALUE_MIN <= v <= self.VALUE_MAX):
            return False
        return True

    def _notify(self, kind, *args):
        try:
            if kind == "quote":
                self.notifier.send_quote_document(*args)
            else:
                self.notifier.send_refusal_notice(*args)
        except Exception:
            # fire-and-forget: delivery failure never changes the response
            pass

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value):
        # Validation (DT-V)
        if not self._valid(weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        weight_kg = float(weight_kg)
        distance_km = float(distance_km)
        declared_value = float(declared_value)

        # Store draft
        try:
            quote_id = self.store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Screening
        try:
            risk_index = self.screening.screen(shipper_id)
        except ScreeningUnavailableError:
            # Outage: price, hold, no notification (DT-S note 5)
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Accept band
        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "quoted", price)
            self._notify("quote", shipper_id, quote_id, price)
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        # Review band
        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # Refuse band
        if risk_index >= self.REFUSE_MIN:
            self.store.update_quote(quote_id, "refused_screening")
            self._notify("refusal", shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}

        # Fallback (gap between bands) -> treat as review hold
        self.store.update_quote(quote_id, "review_hold")
        return {"status": "review_hold", "quote_id": quote_id}


def handle(request: dict) -> dict:
    request = request or {}

    screening = ScreeningService(request)
    store = QuoteStore(request)
    tariff = TariffEngine()
    notifier = NotificationService(request)
    api = QuoteApi(store, screening, tariff, notifier)

    shipper_id = request.get("shipper_id", request.get("shipper", "UNKNOWN"))
    weight_kg = request.get("weight_kg", 620)
    distance_km = request.get("distance_km", 1400)
    declared_value = request.get("declared_value", 20000)

    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)