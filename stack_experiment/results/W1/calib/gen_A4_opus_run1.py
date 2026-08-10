def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id, risk_index=12):
        return risk_index


class TariffEngine:
    """Computes the freight price per DT-P."""

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

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value):
        self._seq += 1
        quote_id = "Q{:06d}".format(self._seq)
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
        }
        return quote_id

    def update_quote(self, quote_id, status, price=None):
        rec = self._records.get(quote_id, {})
        rec["status"] = status
        if price is not None:
            rec["price"] = price
        self._records[quote_id] = rec
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id, quote_id, price):
        return "sent"

    def send_refusal_notice(self, shipper_id, quote_id):
        return "sent"


class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


# DT-S symbolic bounds
ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

# DT-V bounds
WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    def __init__(self, screening_service, tariff_engine, quote_store,
                 notification_service):
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.notification_service = notification_service

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value):
        if not shipper_id or not str(shipper_id).strip():
            return False
        for val, lo, hi in (
            (weight_kg, WEIGHT_MIN, WEIGHT_MAX),
            (distance_km, DISTANCE_MIN, DISTANCE_MAX),
            (declared_value, VALUE_MIN, VALUE_MAX),
        ):
            if val is None or not (lo <= val <= hi):
                return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value,
                      store_ok=True, screening_outage=False, risk_index=12,
                      notification_ok=True):
        # 1. Validate (DT-V)
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # 2. Store draft
        if not store_ok:
            return {"status": "error: store_unavailable"}
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # 3. Screening
        if screening_outage:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        risk = self.screening_service.screen(shipper_id, risk_index)

        # 4/5/6. Apply DT-S
        if risk <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            if notification_ok:
                try:
                    self.notification_service.send_quote_document(
                        shipper_id, quote_id, price)
                except Exception:
                    pass
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        if REVIEW_MIN <= risk <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # risk >= REFUSE_MIN
        self.quote_store.update_quote(quote_id, "refused_screening")
        if notification_ok:
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass
        return {"status": "refused_screening", "quote_id": quote_id}


def _is_failure_word(v):
    return isinstance(v, str) and v.lower() in (
        "error", "unavailable", "down", "outage", "fail", "failed")


def handle(request: dict) -> dict:
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    api = QuoteApi(screening_service, tariff_engine, quote_store,
                   notification_service)

    shipper_id = request.get("shipper_id")
    weight_kg = _num(request.get("weight_kg"))
    distance_km = _num(request.get("distance_km"))
    declared_value = _num(request.get("declared_value"))

    # Store outcome
    store_ok = True
    store_val = request.get("store_result", request.get("store_status",
                request.get("quote_store_result",
                request.get("quote_store_status"))))
    if store_val is not None and _is_failure_word(store_val):
        store_ok = False
    if request.get("store_exists") is False or request.get("store_found") is False:
        store_ok = False

    # Screening outcome
    screening_outage = False
    risk_index = 12
    scr_val = request.get("screening_result", request.get("screening_status",
              request.get("risk_index")))
    if scr_val is not None:
        if _is_failure_word(scr_val):
            screening_outage = True
        else:
            n = _num(scr_val)
            if n is not None:
                risk_index = int(n)
    if request.get("screening_exists") is False or \
            request.get("screening_found") is False:
        screening_outage = True

    # Notification outcome
    notification_ok = True
    notif_val = request.get("notification_result",
                request.get("notification_status"))
    if notif_val is not None and _is_failure_word(notif_val):
        notification_ok = False

    return api.request_quote(
        shipper_id, weight_kg, distance_km, declared_value,
        store_ok=store_ok, screening_outage=screening_outage,
        risk_index=risk_index, notification_ok=notification_ok)