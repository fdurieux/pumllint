from typing import Optional


# --- Exceptions (internal failure signalling) -------------------------------

class StoreUnavailable(Exception):
    pass


class ScreeningUnavailable(Exception):
    pass


# --- Decision-table constants -----------------------------------------------

ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000


# --- External systems (outside the boundary) --------------------------------

class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, risk_index: int = 0, available: bool = True):
        self._risk_index = risk_index
        self._available = available

    def screen(self, shipper_id: str) -> int:
        if not self._available:
            raise ScreeningUnavailable("screening service unavailable")
        return self._risk_index


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, deliverable: bool = True):
        self._deliverable = deliverable

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        if not self._deliverable:
            raise RuntimeError("delivery failed")
        return "delivered"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        if not self._deliverable:
            raise RuntimeError("delivery failed")
        return "delivered"


# --- Internal containers ----------------------------------------------------

class TariffEngine:
    """Computes the freight price per DT-P."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        base = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            base += 316.00
        if distance_km >= 4912:
            base *= 1.19
        return round(base, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available: bool = True):
        self._available = available
        self._records = {}
        self._seq = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value) -> str:
        if not self._available:
            raise StoreUnavailable("store unavailable")
        self._seq += 1
        quote_id = "Q{:06d}".format(self._seq)
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> str:
        rec = self._records.get(quote_id)
        if rec is not None:
            rec["status"] = status
            if price is not None:
                rec["price"] = price
        return quote_id


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening/pricing, returns outcome."""

    def __init__(self, tariff_engine, quote_store, screening_service, notification_service):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    # --- DT-V validation ---
    @staticmethod
    def _is_number(v) -> bool:
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def _valid(self, shipper_id, weight_kg, distance_km, declared_value) -> bool:
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False
        if not self._is_number(weight_kg) or not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            return False
        if not self._is_number(distance_km) or not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            return False
        if not self._is_number(declared_value) or not (VALUE_MIN <= declared_value <= VALUE_MAX):
            return False
        return True

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value) -> dict:
        # Step 1 — validate
        if not self._valid(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # Step 2 — store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value
            )
        except StoreUnavailable:
            return {"status": "error: store_unavailable"}

        # Step 3 — screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailable:
            # DT-S note 5: price, hold, do not notify
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4/5/6 — apply DT-S decision
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            self._notify_quote(shipper_id, quote_id, price)
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}

        # risk_index >= REFUSE_MIN
        self.quote_store.update_quote(quote_id, "refused_screening")
        self._notify_refusal(shipper_id, quote_id)
        return {"status": "refused_screening", "quote_id": quote_id}

    # --- fire-and-forget notification wrappers (DT-S note 4) ---
    def _notify_quote(self, shipper_id, quote_id, price):
        try:
            self.notification_service.send_quote_document(shipper_id, quote_id, price)
        except Exception:
            pass

    def _notify_refusal(self, shipper_id, quote_id):
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            pass


# --- Module-level entry point -----------------------------------------------

def _store_available(request: dict) -> bool:
    val = request.get("store_result", request.get("store_status",
          request.get("quote_store_result", request.get("quote_store_status"))))
    if isinstance(val, str) and val.lower() in ("error", "unavailable", "down", "fail", "failed"):
        return False
    if request.get("store_exists") is False or request.get("store_found") is False:
        return False
    return True


def _screening_config(request: dict):
    """Return (risk_index, available)."""
    if "risk_index" in request:
        return int(request["risk_index"]), True

    val = request.get("screening_result", request.get("screening_status"))
    if isinstance(val, bool):
        return 0, True
    if isinstance(val, (int, float)):
        return int(val), True
    if isinstance(val, str):
        s = val.strip().lower()
        if s in ("error", "unavailable", "down", "outage", "fail", "failed"):
            return 0, False
        if s == "declined" or s == "refused":
            return REFUSE_MIN, True
        if s == "review":
            return REVIEW_MIN, True
        if s in ("approved", "accepted", "clear", "assessed"):
            return 0, True
        try:
            return int(float(s)), True
        except ValueError:
            pass
    return 0, True


def _notification_deliverable(request: dict) -> bool:
    val = request.get("notification_result", request.get("notification_status"))
    if isinstance(val, str) and val.lower() in ("error", "unavailable", "fail", "failed", "declined"):
        return False
    return True


def handle(request: dict) -> dict:
    request = request or {}

    risk_index, screening_available = _screening_config(request)

    tariff_engine = TariffEngine()
    quote_store = QuoteStore(available=_store_available(request))
    screening_service = ScreeningService(risk_index=risk_index, available=screening_available)
    notification_service = NotificationService(deliverable=_notification_deliverable(request))

    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)

    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    return api.request_quote(shipper_id, weight_kg, distance_km, declared_value)