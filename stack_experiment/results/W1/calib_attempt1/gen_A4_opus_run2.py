def _round2(x):
    return round(x + 0, 2)


class TariffEngine:
    """Computes the freight price per DT-P."""

    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def price(self, weight_kg, distance_km):
        base = 0.87 * weight_kg + 1.13 * distance_km  # P1
        total = base
        if weight_kg > 1244:  # P2
            total += 316.00
        if distance_km >= 4912:  # P3
            total *= 1.19
        return round(total, 2)  # P4


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._store = {}
        self._counter = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value,
                    available=True):
        if not available:
            raise StoreUnavailableError("store_unavailable")
        self._counter += 1
        quote_id = "Q-%04d" % self._counter
        self._store[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price=None):
        rec = self._store.get(quote_id)
        if rec is None:
            raise KeyError(quote_id)
        rec["status"] = status
        if price is not None:
            rec["price"] = price
        return dict(rec)


class ScreeningService:
    """External denied-party screening provider returning a risk index."""

    def screen(self, shipper_id, outcome=None):
        if outcome is None:
            return 0
        if isinstance(outcome, (int, float)) and not isinstance(outcome, bool):
            return int(outcome)
        text = str(outcome).strip().lower()
        if text in ("error", "unavailable", "down", "timeout"):
            raise ScreeningUnavailableError("screening_unavailable")
        try:
            return int(float(text))
        except ValueError:
            return 0


class NotificationService:
    """External messaging provider delivering quote docs and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price, fail=False):
        if fail:
            return False  # fire-and-forget: failure ignored by caller
        return True

    def send_refusal_notice(self, shipper_id, quote_id, fail=False):
        if fail:
            return False
        return True


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class InvalidRequestError(Exception):
    pass


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine=None, quote_store=None,
                 screening_service=None, notification_service=None):
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    # DT-V
    def _validate(self, req):
        shipper_id = req.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            raise InvalidRequestError("shipper_id")

        def _num(key, lo, hi):
            v = req.get(key)
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise InvalidRequestError(key)
            if not (lo <= v <= hi):
                raise InvalidRequestError(key)
            return v

        weight_kg = _num("weight_kg", 3, 19400)         # V2
        distance_km = _num("distance_km", 25, 7150)     # V3
        declared_value = _num("declared_value", 50, 83000)  # V4
        return shipper_id, weight_kg, distance_km, declared_value

    def request_quote(self, req):
        # Step 1 — validate
        try:
            shipper_id, weight_kg, distance_km, declared_value = self._validate(req)
        except InvalidRequestError:
            return {"status": "rejected: invalid_request"}

        # Step 2 — store draft
        store_available = self._flag(req, "store", True)
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value,
                available=store_available)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3 — screening
        screening_outcome = self._screening_outcome(req)
        try:
            risk_index = self.screening_service.screen(shipper_id, screening_outcome)
        except ScreeningUnavailableError:
            # DT-S note 5: price anyway, hold, no notification
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {"status": "held_unscreened", "quote_id": quote_id,
                    "price": price, "hold": True}

        notify_fail = self._flag(req, "notification", True) is False

        # Step 4/5/6 — apply DT-S banding
        if risk_index <= TariffEngine.ACCEPT_MAX:  # accept
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price, fail=notify_fail)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif risk_index <= TariffEngine.REVIEW_MAX:  # review
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # refuse
            self.quote_store.update_quote(quote_id, "refused_screening")
            self.notification_service.send_refusal_notice(
                shipper_id, quote_id, fail=notify_fail)
            return {"status": "refused_screening", "quote_id": quote_id}

    # --- helpers for interpreting request-level external outcomes ---
    @staticmethod
    def _flag(req, system, default):
        for key in ("%s_status" % system, "%s_result" % system):
            if key in req:
                val = str(req[key]).strip().lower()
                if val in ("error", "unavailable", "down", "fail", "failed",
                           "timeout"):
                    return False
                if val in ("ok", "stored", "available", "delivered", "sent",
                           "success", "up"):
                    return True
        return default

    @staticmethod
    def _screening_outcome(req):
        for key in ("risk_index", "screening_result", "screening_status",
                    "screening_score"):
            if key in req:
                return req[key]
        return None


def handle(request: dict) -> dict:
    api = QuoteApi()
    return api.request_quote(request)