from typing import Any


class ACCEPT_MAX:
    pass


ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class ScreeningServiceUnavailable(Exception):
    pass


class StoreUnavailable(Exception):
    pass


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id: str, risk_index: int = 0, available: bool = True) -> int:
        if not available:
            raise ScreeningServiceUnavailable("screening_unavailable")
        return int(risk_index)


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price_amount: float) -> str:
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class TariffEngine:
    """Computes the freight price per DT-P."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        base = 0.87 * weight_kg + 1.13 * distance_km
        result = base
        if weight_kg > 1244:
            result += 316.00
        if distance_km >= 4912:
            result *= 1.19
        return round(result, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records = {}
        self._counter = 0

    def store_draft(self, shipper_id, weight_kg, distance_km, declared_value, available: bool = True) -> str:
        if not available:
            raise StoreUnavailable("store_unavailable")
        self._counter += 1
        quote_id = "Q%04d" % self._counter
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id: str, status: str, price_amount: float = None) -> str:
        rec = self._records.get(quote_id)
        if rec is not None:
            rec["status"] = status
            if price_amount is not None:
                rec["price"] = price_amount
        return quote_id


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine=None, quote_store=None,
                 screening_service=None, notification_service=None):
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    def _validate(self, shipper_id, weight_kg, distance_km, declared_value) -> bool:
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
    def _is_number(v) -> bool:
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def request_quote(self, shipper_id, weight_kg, distance_km, declared_value,
                      store_available=True, screening_available=True, risk_index=0):
        # Step 1: validate
        if not self._validate(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}

        # Step 2: store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, available=store_available)
        except StoreUnavailable:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk = self.screening_service.screen(
                shipper_id, risk_index=risk_index, available=screening_available)
        except ScreeningServiceUnavailable:
            # Screening outage: price anyway, hold, do not notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price_amount)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price_amount,
                "hold": True,
            }

        # Step 4/5/6: apply screening decision
        if risk <= ACCEPT_MAX:
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price_amount)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price_amount)
            except Exception:
                pass
            return {"status": "quoted", "quote_id": quote_id, "price": price_amount}
        elif REVIEW_MIN <= risk <= REVIEW_MAX:
            self.quote_store.update_quote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk >= REFUSE_MIN
            self.quote_store.update_quote(quote_id, "refused_screening")
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass
            return {"status": "refused_screening", "quote_id": quote_id}


def _resolve_store_available(request: dict) -> bool:
    status = request.get("store_status") or request.get("store_result")
    if status is not None:
        if str(status).lower() in ("error", "unavailable", "down", "fail", "failure"):
            return False
        return True
    if "store_available" in request:
        return bool(request["store_available"])
    for key in ("store_exists", "store_found"):
        if key in request:
            return bool(request[key])
    return True


def _resolve_screening(request: dict):
    status = request.get("screening_status")
    result = request.get("screening_result")

    # Determine availability
    available = True
    for v in (status, result):
        if isinstance(v, str) and v.lower() in ("error", "unavailable", "down", "outage", "fail", "failure"):
            available = False
    if "screening_available" in request:
        available = bool(request["screening_available"])

    # Determine risk index
    risk = 0
    for v in (result, status, request.get("risk_index")):
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            risk = int(v)
            break
        if isinstance(v, str):
            try:
                risk = int(v)
                break
            except ValueError:
                continue

    return available, risk


def handle(request: dict) -> dict:
    api = QuoteApi()

    shipper_id = request.get("shipper_id", request.get("shipperId"))
    weight_kg = request.get("weight_kg", request.get("weightKg"))
    distance_km = request.get("distance_km", request.get("distanceKm"))
    declared_value = request.get("declared_value", request.get("declaredValue"))

    store_available = _resolve_store_available(request)
    screening_available, risk_index = _resolve_screening(request)

    try:
        return api.request_quote(
            shipper_id, weight_kg, distance_km, declared_value,
            store_available=store_available,
            screening_available=screening_available,
            risk_index=risk_index,
        )
    except Exception as exc:
        return {"status": "error: %s" % str(exc)}