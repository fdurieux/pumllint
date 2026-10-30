from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


class StoreUnavailableError(Exception):
    """Raised when the Quote Store cannot persist or update a record."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service cannot return a risk index."""


@dataclass
class QuoteStore:
    """Persistence collaborator for quote drafts and updates.

    In this implementation, methods are stubs intended to be overridden or
    monkey-patched in tests.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        May raise StoreUnavailableError on failure.
        """

        # Simple in-memory stub; real implementation would persist to a DB.
        # Here we just return a dummy ID.
        return "QUOTE-1"

    def update_quote(self, quote_id: str, status: str, price: float | None = None) -> None:
        """Update an existing quote with new status and optional price.

        May raise StoreUnavailableError on failure.
        """

        # Stub: no-op.
        return None


@dataclass
class TariffEngine:
    """Tariff engine implementing DT-P pricing rules."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # P1: base = 0.87 * weight_kg + 1.13 * distance_km
        base = 0.87 * weight_kg + 1.13 * distance_km

        # P2: heavy surcharge
        if weight_kg > 1244:
            base += 316.00

        # P3: long-haul multiplier
        if distance_km >= 4912:
            base *= 1.19

        # P4: round to 2 decimals
        price = round(base, 2)
        return price


@dataclass
class ScreeningService:
    """External screening service returning a risk index."""

    def screen(self, shipper_id: str) -> int:
        """Return integer risk index for the shipper.

        May raise ScreeningUnavailableError on outage.
        """

        # Stub: always low risk.
        return 0


@dataclass
class NotificationService:
    """External notification provider (fire-and-forget semantics)."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send a quote document to the shipper.

        Any delivery failure may be signaled by raising an exception, which the
        QuoteAPI must ignore (fire-and-forget, response unchanged).
        """

        # Stub: do nothing.
        return None

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice to the shipper.

        Any delivery failure may be signaled by raising an exception, which the
        QuoteAPI must ignore.
        """

        # Stub: do nothing.
        return None


class QuoteAPI:
    """Implements the CargoQuote instant freight quotation flow."""

    def __init__(self) -> None:
        self.store = QuoteStore()
        self.tariff = TariffEngine()
        self.screening = ScreeningService()
        self.notifier = NotificationService()

    # --- Public entry point ---

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a quotation request and return a response dict.

        The request dict must have keys: shipper_id, weight_kg, distance_km,
        declared_value. This method implements the flow order and error policy
        defined in the CargoQuote spec and decision tables.
        """

        # 1. Validate request (DT-V). Invalid => reject, stop.
        if not self._is_valid_request(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = str(request["shipper_id"])
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # 2. Store the draft quote in the Quote Store with status draft.
        try:
            quote_id = self.store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            # On storage failure: error status, nothing else runs.
            return {"status": "error: store_unavailable"}

        # 3. Request risk index from Screening Service.
        try:
            risk_index = self.screening.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage path: price anyway, store held_unscreened, no notify.
            price = self.tariff.price(weight_kg=weight_kg, distance_km=distance_km)
            # Update stored quote; on failure we let exception propagate as undefined.
            self.store.update_quote(quote_id=quote_id, status="held_unscreened", price=price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4. Apply screening decision (DT-S) to risk_index.
        # Numeric bands are assumed (see assumptions):
        #   accept: risk_index <= 39
        #   review: 40 <= risk_index <= 65
        #   refuse: risk_index >= 66
        if risk_index <= 39:
            # Accept row: price, update to quoted, notify with quote document.
            price = self.tariff.price(weight_kg=weight_kg, distance_km=distance_km)
            self.store.update_quote(quote_id=quote_id, status="quoted", price=price)

            # Fire-and-forget notification: ignore any delivery failure.
            try:
                self.notifier.send_quote_document(shipper_id=shipper_id, quote_id=quote_id, price=price)
            except Exception:
                # Outcome and response unchanged.
                pass

            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }

        if 40 <= risk_index <= 65:
            # Review row: update to review_hold, no price, no notification.
            self.store.update_quote(quote_id=quote_id, status="review_hold", price=None)
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }

        # Refuse row (anything higher): update to refused_screening, notify refusal.
        self.store.update_quote(quote_id=quote_id, status="refused_screening", price=None)

        try:
            self.notifier.send_refusal_notice(shipper_id=shipper_id, quote_id=quote_id)
        except Exception:
            # Fire-and-forget: ignore failure.
            pass

        return {
            "status": "refused_screening",
            "quote_id": quote_id,
        }

    # --- Internal helpers ---

    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Check DT-V validation rules against the request dict."""

        # Required keys
        required_keys = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for key in required_keys:
            if key not in request:
                return False

        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]

        # V1: shipper_id present and non-empty string
        if not isinstance(shipper_id, str) or not shipper_id.strip():
            return False

        # V2: weight_kg is number, 3 <= weight_kg <= 19400
        if not isinstance(weight_kg, (int, float)):
            return False
        if weight_kg < 3 or weight_kg > 19400:
            return False

        # V3: distance_km is number, 25 <= distance_km <= 7150
        if not isinstance(distance_km, (int, float)):
            return False
        if distance_km < 25 or distance_km > 7150:
            return False

        # V4: declared_value is number, 50 <= declared_value <= 83000
        if not isinstance(declared_value, (int, float)):
            return False
        if declared_value < 50 or declared_value > 83000:
            return False

        return True


# Module-level handle entry point
_api_instance = QuoteAPI()


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level facade delegating to QuoteAPI.handle."""

    return _api_instance.handle(request)
