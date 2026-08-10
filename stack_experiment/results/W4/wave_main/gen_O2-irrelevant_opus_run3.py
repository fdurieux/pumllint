def _price(weight_kg, distance_km):
    base = 0.87 * weight_kg + 1.13 * distance_km
    total = base
    if weight_kg > 1244:
        total += 316.00
    if distance_km >= 4912:
        total *= 1.19
    return round(total, 2)


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class NotificationError(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, ctx=None):
        ctx = ctx or {}
        status = str(ctx.get("screening_status", "")).lower()
        if status in ("error", "unavailable", "down", "outage", "timeout"):
            raise ScreeningUnavailableError("screening_unavailable")
        result = ctx.get("screening_result", ctx.get("risk_index"))
        if result is None:
            return 0
        try:
            return int(result)
        except (TypeError, ValueError):
            word = str(result).lower()
            if word in ("error", "unavailable"):
                raise ScreeningUnavailableError("screening_unavailable")
            return 0


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price_amount, ctx=None):
        return self._deliver(ctx)

    def send_refusal_notice(self, shipper_id, quote_id, ctx=None):
        return self._deliver(ctx)

    def _deliver(self, ctx):
        ctx = ctx or {}
        status = str(ctx.get("notification_status", "")).lower()
        if status in ("error", "failed", "fail", "unavailable"):
            raise NotificationError("notification_failed")
        return "delivered"


class TariffEngine:
    """Computes the freight price from weight and distance per the published tariff."""

    def price(self, weight_kg, distance_km):
        return _price(weight_kg, distance_km)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, ctx=None):
        ctx = ctx or {}
        status = str(ctx.get("store_status", ctx.get("store_result", ""))).lower()
        if status in ("error", "unavailable", "down", "fail", "failed"):
            raise StoreUnavailableError("store_unavailable")
        self._seq += 1
        quote_id = "Q-{:06d}".format(self._seq)
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id, status, price_amount=None):
        rec = self._records.get(quote_id)
        if rec is not None:
            rec["status"] = status
            if price_amount is not None:
                rec["price"] = price_amount
        return quote_id


# DT-V bounds
_V = {
    "weight_kg": (3, 19400),
    "distance_km": (25, 7150),
    "declared_value": (50, 83000),
}

# DT-S symbolic bands
ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, request):
        shipper_id = request.get("shipper_id")
        if not shipper_id or not str(shipper_id).strip():
            return False
        for field, (lo, hi) in _V.items():
            val = request.get(field)
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                return False
            if not (lo <= val <= hi):
                return False
        return True

    def request_quote(self, request):
        # Step 1: validate
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request.get("shipper_id")
        weight_kg = request.get("weight_kg")
        distance_km = request.get("distance_km")
        declared_value = request.get("declared_value")

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, request
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id, request)
        except ScreeningUnavailableError:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4/5/6: apply DT-S
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            try:
                self.notification_service.send_quote_document(
                    shipper_id, quote_id, price_amount, request
                )
            except NotificationError:
                pass
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}

        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        else:  # risk_index >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            try:
                self.notification_service.send_refusal_notice(
                    shipper_id, quote_id, request
                )
            except NotificationError:
                pass
            return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)
    return api.request_quote(request or {})