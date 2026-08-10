def _round2(x):
    return round(x + 0.0, 2)


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, risk_index=None, status="ok"):
        if status in ("error", "unavailable", "down"):
            raise RuntimeError("screening_unavailable")
        if risk_index is None:
            return 12
        return int(risk_index)


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id, quote_id, price_amount, status="ok"):
        if status in ("error", "failed", "unavailable"):
            return "delivery_failed"
        return "delivered"

    def sendRefusalNotice(self, shipper_id, quote_id, status="ok"):
        if status in ("error", "failed", "unavailable"):
            return "delivery_failed"
        return "delivered"


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

    def price(self, weight_kg, distance_km):
        result = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            result += 316.00
        if distance_km >= 4912:
            result *= 1.19
        return _round2(result)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._seq = 0

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value, status="ok"):
        if status in ("error", "unavailable", "down"):
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

    def updateQuote(self, quote_id, status, price_amount=None):
        rec = self._records.get(quote_id)
        if rec is None:
            raise RuntimeError("unknown_quote")
        rec["status"] = status
        if price_amount is not None:
            rec["price"] = price_amount
        return quote_id


# DT-S symbolic boundaries
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

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False
        if not self._is_number(weight_kg) or not (3 <= weight_kg <= 19400):
            return False
        if not self._is_number(distance_km) or not (25 <= distance_km <= 7150):
            return False
        if not self._is_number(declared_value) or not (50 <= declared_value <= 83000):
            return False
        return True

    @staticmethod
    def _is_number(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def requestQuote(self, shipper_id, weight_kg, distance_km, declared_value,
                     store_status="ok", screening_status="ok", screening_risk=None,
                     notification_status="ok"):
        # Step 1: validate
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # Step 2: store draft
        try:
            quote_id = self.quote_store.storeDraft(
                shipper_id, weight_kg, distance_km, declared_value, status=store_status)
        except RuntimeError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(
                shipper_id, risk_index=screening_risk, status=screening_status)
        except RuntimeError:
            # screening outage: price anyway, hold, no notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4-6: apply DT-S
        if risk_index <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price_amount)
            self.notification_service.sendQuoteDocument(
                shipper_id, quote_id, price_amount, status=notification_status)
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.updateQuote(quote_id, "refused_screening")
            self.notification_service.sendRefusalNotice(
                shipper_id, quote_id, status=notification_status)
            return {"status": "refused_screening", "quote_id": quote_id}


def _resolve_screening(request):
    # Determine screening outcome from request keys
    status = "ok"
    risk = None
    for key in ("screening_status", "screening_result", "screening"):
        if key in request:
            val = request[key]
            if isinstance(val, str):
                if val.lower() in ("error", "unavailable", "down", "outage"):
                    status = "error"
                else:
                    try:
                        risk = int(val)
                    except ValueError:
                        pass
            elif isinstance(val, (int, float)) and not isinstance(val, bool):
                risk = int(val)
    return status, risk


def _resolve_store(request):
    for key in ("store_status", "store_result", "store"):
        if key in request:
            val = request[key]
            if isinstance(val, str) and val.lower() in ("error", "unavailable", "down"):
                return "error"
    if request.get("store_exists") is False or request.get("store_found") is False:
        return "error"
    return "ok"


def _resolve_notification(request):
    for key in ("notification_status", "notification_result", "notification"):
        if key in request:
            val = request[key]
            if isinstance(val, str) and val.lower() in ("error", "failed", "unavailable"):
                return "error"
    return "ok"


def handle(request: dict) -> dict:
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)

    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    store_status = _resolve_store(request)
    screening_status, screening_risk = _resolve_screening(request)
    notification_status = _resolve_notification(request)

    return api.requestQuote(
        shipper_id, weight_kg, distance_km, declared_value,
        store_status=store_status,
        screening_status=screening_status,
        screening_risk=screening_risk,
        notification_status=notification_status,
    )