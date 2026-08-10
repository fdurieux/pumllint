from typing import Any, Optional


# --- Decision table constants (DT-V, DT-S, DT-P) ---
WEIGHT_MIN, WEIGHT_MAX = 3, 19400
DISTANCE_MIN, DISTANCE_MAX = 25, 7150
VALUE_MIN, VALUE_MAX = 50, 83000

ACCEPT_MAX = 41
REVIEW_MIN, REVIEW_MAX = 42, 66
REFUSE_MIN = 67


# --- Internal exceptions modelling failure paths ---
class StoreUnavailableError(Exception):
    pass


class ScreeningUnavailableError(Exception):
    pass


class InvalidRequestError(Exception):
    pass


# --- External systems (outside the boundary) ---
class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def __init__(self, risk_index: Optional[int] = 0, unavailable: bool = False):
        self._risk_index = risk_index
        self._unavailable = unavailable

    def screen(self, shipper_id: str) -> int:
        if self._unavailable:
            raise ScreeningUnavailableError("screening_unavailable")
        return int(self._risk_index)


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def __init__(self, deliverable: bool = True):
        self._deliverable = deliverable

    def sendQuoteDocument(self, shipper_id: str, quote_id: str, price: float) -> bool:
        # Fire-and-forget: delivery outcome never changes the response.
        return bool(self._deliverable)

    def sendRefusalNotice(self, shipper_id: str, quote_id: str) -> bool:
        return bool(self._deliverable)


# --- System containers ---
class TariffEngine:
    """Computes the freight price per DT-P."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        result = 0.87 * weight_kg + 1.13 * distance_km  # P1
        if weight_kg > 1244:  # P2
            result += 316.00
        if distance_km >= 4912:  # P3 (after P2)
            result *= 1.19
        return round(result, 2)  # P4


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self, available: bool = True):
        self._available = available
        self._records = {}
        self._seq = 0

    def storeDraft(self, shipper_id, weight_kg, distance_km, declared_value) -> str:
        if not self._available:
            raise StoreUnavailableError("store_unavailable")
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

    def updateQuote(self, quote_id: str, status: str, price: Optional[float] = None) -> str:
        rec = self._records.get(quote_id)
        if rec is not None:
            rec["status"] = status
            if price is not None:
                rec["price"] = price
        return quote_id


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine: TariffEngine, quote_store: QuoteStore,
                 screening_service: ScreeningService, notification_service: NotificationService):
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, request: dict) -> None:
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id == "":
            raise InvalidRequestError("V1")
        weight = request.get("weight_kg")
        if not _is_number(weight) or not (WEIGHT_MIN <= weight <= WEIGHT_MAX):
            raise InvalidRequestError("V2")
        distance = request.get("distance_km")
        if not _is_number(distance) or not (DISTANCE_MIN <= distance <= DISTANCE_MAX):
            raise InvalidRequestError("V3")
        value = request.get("declared_value")
        if not _is_number(value) or not (VALUE_MIN <= value <= VALUE_MAX):
            raise InvalidRequestError("V4")

    def requestQuote(self, request: dict) -> dict:
        # Step 1: validate (DT-V)
        try:
            self._validate(request)
        except InvalidRequestError:
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]

        # Step 2: store draft
        try:
            quote_id = self.quote_store.storeDraft(shipper_id, weight_kg, distance_km, declared_value)
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage: price anyway, hold unscreened, do not notify (DT-S note 5)
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4-6: apply screening decision (DT-S)
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price)
            self.notification_service.sendQuoteDocument(shipper_id, quote_id, price)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.updateQuote(quote_id, "refused_screening")
            self.notification_service.sendRefusalNotice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _resolve_risk(request: dict):
    """Return (risk_index, unavailable) derived from the request's screening keys."""
    for key in ("screening_result", "screening_status", "risk_index", "screening_score"):
        if key in request and request[key] is not None:
            val = request[key]
            if _is_number(val):
                return int(val), False
            word = str(val).strip().lower()
            if word in ("error", "unavailable", "outage", "down", "timeout"):
                return 0, True
            if word in ("approved", "accept", "accepted", "active", "assessed", "clear", "ok"):
                return 0, False
            if word in ("review", "hold", "manual"):
                return REVIEW_MIN, False
            if word in ("declined", "refused", "refuse", "denied", "reject", "rejected"):
                return REFUSE_MIN, False
            # numeric-looking string
            try:
                return int(float(word)), False
            except ValueError:
                return 0, False
    return 0, False


def _resolve_store(request: dict) -> bool:
    for key in ("quote_store_result", "store_status", "quote_store_status", "store_result"):
        if key in request and request[key] is not None:
            word = str(request[key]).strip().lower()
            if word in ("error", "unavailable", "down", "fail", "failed"):
                return False
            return True
    if request.get("quote_store_exists") is False:
        return False
    return True


def _resolve_notification(request: dict) -> bool:
    for key in ("notification_result", "notification_status"):
        if key in request and request[key] is not None:
            word = str(request[key]).strip().lower()
            if word in ("error", "unavailable", "down", "fail", "failed"):
                return False
            return True
    return True


def handle(request: dict) -> dict:
    """Run one end-to-end quotation flow."""
    request = dict(request or {})

    risk_index, screening_unavailable = _resolve_risk(request)
    store_available = _resolve_store(request)
    notification_ok = _resolve_notification(request)

    tariff_engine = TariffEngine()
    quote_store = QuoteStore(available=store_available)
    screening_service = ScreeningService(risk_index=risk_index, unavailable=screening_unavailable)
    notification_service = NotificationService(deliverable=notification_ok)

    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)
    return api.requestQuote(request)