#!/usr/bin/env python3
"""CargoQuote — Instant Freight Quotation System (quotation scope)."""

from __future__ import annotations


# --- Validation bounds (Decision table DT-V) ---
WEIGHT_MIN = 1.0
WEIGHT_MAX = 26000.0
DISTANCE_MIN = 1.0
DISTANCE_MAX = 4000.0
VALUE_MIN = 0.01
VALUE_MAX = 10_000_000.0

# --- Screening decision thresholds (Decision table DT-S) ---
ACCEPT_MAX = 30
REVIEW_MIN = 31
REVIEW_MAX = 70
REFUSE_MIN = 71


# --- Tariff constants ---
BASE_RATE = 25.0
RATE_PER_KG = 0.15
RATE_PER_KM = 0.40
RATE_PER_KG_KM = 0.0002


class ValidationError(Exception):
    """Raised when a quote request fails validation (DT-V)."""


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable."""


class ScreeningUnavailableError(Exception):
    """Raised when the screening service is unavailable."""


class TariffEngine:
    """Computes the freight price from weight and distance per the tariff."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        amount = (
            BASE_RATE
            + RATE_PER_KG * weight_kg
            + RATE_PER_KM * distance_km
            + RATE_PER_KG_KM * weight_kg * distance_km
        )
        return round(amount, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self) -> None:
        self._records: dict[str, dict] = {}
        self._counter = 0

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
        available: bool = True,
    ) -> str:
        if not available:
            raise StoreUnavailableError("storeUnavailableError")
        self._counter += 1
        quote_id = f"Q{self._counter:06d}"
        self._records[quote_id] = {
            "shipperId": shipper_id,
            "weightKg": weight_kg,
            "distanceKm": distance_km,
            "declaredValue": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(
        self,
        quote_id: str,
        status: str,
        price_amount: float | None = None,
    ) -> str:
        record = self._records.get(quote_id)
        if record is not None:
            record["status"] = status
            if price_amount is not None:
                record["price"] = price_amount
        return quote_id


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id: str, risk_index: int = 0, available: bool = True) -> int:
        if not available:
            raise ScreeningUnavailableError("screeningUnavailableError")
        return risk_index


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(
        self, shipper_id: str, quote_id: str, price_amount: float
    ) -> str:
        return "sent"

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        return "sent"


class QuoteAPI:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    def __init__(
        self,
        tariff_engine: TariffEngine,
        quote_store: QuoteStore,
        screening_service: ScreeningService,
        notification_service: NotificationService,
    ) -> None:
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> None:
        if not shipper_id:
            raise ValidationError("missing shipperId")
        if weight_kg is None or not (WEIGHT_MIN <= weight_kg <= WEIGHT_MAX):
            raise ValidationError("weight out of bounds")
        if distance_km is None or not (DISTANCE_MIN <= distance_km <= DISTANCE_MAX):
            raise ValidationError("distance out of bounds")
        if declared_value is None or not (VALUE_MIN <= declared_value <= VALUE_MAX):
            raise ValidationError("declared value out of bounds")

    def request_quote(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
        store_available: bool = True,
        screening_available: bool = True,
        risk_index: int = 0,
    ) -> dict:
        # Step 2: validation
        try:
            self._validate(shipper_id, weight_kg, distance_km, declared_value)
        except ValidationError as exc:
            return {"status": "rejectedInvalidRequest", "reason": str(exc)}

        # Step 2/3: store draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id, weight_kg, distance_km, declared_value, store_available
            )
        except StoreUnavailableError:
            return {"status": "storeUnavailableError"}

        # Step 3: screening
        try:
            index = self.screening_service.screen(
                shipper_id, risk_index, screening_available
            )
        except ScreeningUnavailableError:
            # Step 4d: screening outage — price, hold unscreened, no notify
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id, "statusHeldUnscreened", price_amount
            )
            return {
                "status": "heldUnscreenedResponse",
                "quoteId": quote_id,
                "price": price_amount,
            }

        # Step 4: apply screening decision
        if index <= ACCEPT_MAX:
            # 4a: accept
            price_amount = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "statusQuoted", price_amount)
            self.notification_service.send_quote_document(
                shipper_id, quote_id, price_amount
            )
            return {
                "status": "quotedResponse",
                "quoteId": quote_id,
                "price": price_amount,
            }
        elif index <= REVIEW_MAX:
            # 4b: review hold
            self.quote_store.update_quote(quote_id, "statusReviewHold")
            return {"status": "reviewHoldResponse", "quoteId": quote_id}
        else:
            # 4c: refuse
            self.quote_store.update_quote(quote_id, "statusRefusedScreening")
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
            return {"status": "refusedScreeningResponse", "quoteId": quote_id}


# --- Module-level orchestration ---

_STATUS_MAP = {
    "rejectedInvalidRequest": "rejected",
    "storeUnavailableError": "error: store unavailable",
    "quotedResponse": "confirmed",
    "reviewHoldResponse": "review",
    "refusedScreeningResponse": "refused",
    "heldUnscreenedResponse": "held_unscreened",
}


def _resolve_store_available(request: dict) -> bool:
    for key in ("store_result", "store_status", "quote_store_result", "quote_store_status"):
        val = request.get(key)
        if isinstance(val, str) and val.lower() in ("error", "unavailable", "down"):
            return False
    if request.get("store_exists") is False or request.get("store_found") is False:
        return False
    return True


def _resolve_screening(request: dict) -> tuple[bool, int]:
    """Return (available, risk_index)."""
    available = True
    risk_index = 0
    for key in ("screening_result", "screening_status", "screening_service_result",
                "screening_service_status"):
        val = request.get(key)
        if val is None:
            continue
        if isinstance(val, (int, float)):
            risk_index = int(val)
        elif isinstance(val, str):
            word = val.lower()
            if word in ("error", "unavailable", "down"):
                available = False
            elif word in ("approved", "accept", "accepted", "clear", "active"):
                risk_index = ACCEPT_MAX
            elif word in ("review", "hold", "assessed"):
                risk_index = REVIEW_MIN
            elif word in ("declined", "refuse", "refused", "denied"):
                risk_index = REFUSE_MIN
            else:
                try:
                    risk_index = int(word)
                except ValueError:
                    pass
    # explicit numeric risk override
    for key in ("risk_index", "riskIndex", "screening_score", "risk"):
        val = request.get(key)
        if isinstance(val, (int, float)):
            risk_index = int(val)
    return available, risk_index


def handle(request: dict) -> dict:
    """Run one end-to-end quotation flow."""
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    api = QuoteAPI(tariff_engine, quote_store, screening_service, notification_service)

    shipper_id = (
        request.get("shipper_id")
        or request.get("shipperId")
        or request.get("shipper")
        or ""
    )
    if request.get("shipper_exists") is False or request.get("shipper_found") is False:
        shipper_id = ""

    weight_kg = request.get("weight_kg", request.get("weightKg"))
    distance_km = request.get("distance_km", request.get("distanceKm"))
    declared_value = request.get(
        "declared_value", request.get("declaredValue")
    )

    store_available = _resolve_store_available(request)
    screening_available, risk_index = _resolve_screening(request)

    result = api.request_quote(
        shipper_id,
        weight_kg,
        distance_km,
        declared_value,
        store_available=store_available,
        screening_available=screening_available,
        risk_index=risk_index,
    )

    outcome = dict(result)
    outcome["status"] = _STATUS_MAP.get(result["status"], result["status"])
    outcome["outcome"] = result["status"]
    return outcome