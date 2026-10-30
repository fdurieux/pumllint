from dataclasses import dataclass
from typing import Any, Dict


class StoreUnavailableError(Exception):
    """Raised when the Quote Store is unavailable for storing drafts or updates."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service is unavailable (screening outage)."""


class QuoteStore:
    """Persistence layer for quotes.

    Methods are expected to raise StoreUnavailableError on storage failure.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        May raise StoreUnavailableError on failure.
        """
        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: float | None = None) -> None:
        """Update an existing quote with the final status and optional price.

        Behavior on failure is unspecified in the docs; for this implementation
        we assume it either succeeds or raises StoreUnavailableError, but
        callers are not required to handle update failures specially.
        """
        raise NotImplementedError


class TariffEngine:
    """Implements pricing rules DT-P."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # P1: base = 0.87 * weight_kg + 1.13 * distance_km
        base = 0.87 * weight_kg + 1.13 * distance_km

        # P2: heavy surcharge: if weight_kg > 1244, add 316.00 flat
        if weight_kg > 1244:
            base += 316.00

        # P3: long-haul multiplier: if distance_km >= 4912, multiply running total by 1.19
        if distance_km >= 4912:
            base *= 1.19

        # P4: price = round(result, 2)
        return round(base, 2)


class ScreeningService:
    """External screening provider returning a shipper risk index."""

    def screen(self, shipper_id: str) -> int:
        """Return integer risk index or raise ScreeningUnavailableError on outage."""
        raise NotImplementedError


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Fire-and-forget; any exception must not affect response semantics."""
        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Fire-and-forget; any exception must not affect response semantics."""
        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # --- Public entry point ---

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Main quotation flow implementing the CargoQuote specification."""
        # 1. Validate request (DT-V). Invalid -> reject, stop.
        if not self._is_valid_request(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # 2. Store draft with status draft. On failure -> error: store_unavailable, stop.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Prepare base response fields
        response: Dict[str, Any] = {"quote_id": quote_id}

        # 3. Request risk index; handle screening outage branch specially.
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_outage = False
        except ScreeningUnavailableError:
            risk_index = None  # not used in outage branch
            screening_outage = True

        if screening_outage:
            # Screening outage branch per DT-S note 5
            price = self.tariff_engine.price(weight_kg, distance_km)
            # Update quote to held_unscreened with price
            try:
                self.quote_store.update_quote(quote_id, status="held_unscreened", price=price)
            except StoreUnavailableError:
                # Spec does not define behavior; we do not alter the response.
                pass

            response.update({
                "status": "held_unscreened",
                "price": price,
                "hold": True,
            })
            # No notification on outage
            return response

        # 4. Apply screening decision DT-S based on risk_index.
        assert isinstance(risk_index, int)
        if risk_index <= 41:
            status = "quoted"
            priced = True
            notified = "quote_document"
        elif 42 <= risk_index <= 66:
            status = "review_hold"
            priced = False
            notified = "none"
        else:  # risk_index >= 67
            status = "refused_screening"
            priced = False
            notified = "refusal_notice"

        # 5. Price where DT-S marks priced (accept row only).
        price: float | None = None
        if priced:
            price = self.tariff_engine.price(weight_kg, distance_km)

        # 4/5 continued: update stored quote to resulting status (and price if present).
        try:
            self.quote_store.update_quote(quote_id, status=status, price=price)
        except StoreUnavailableError:
            # Underspecified; no change to outward behavior.
            pass

        # 6. Notify where DT-S marks notified; swallow any delivery failures.
        if notified == "quote_document" and price is not None:
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                # Fire-and-forget per spec; do not change response.
                pass
        elif notified == "refusal_notice":
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                # Fire-and-forget; ignore.
                pass

        # 7. Build and return response per API contract.
        response["status"] = status
        if price is not None and status in ("quoted", "held_unscreened"):
            response["price"] = price
        if status == "held_unscreened":
            response["hold"] = True

        return response

    # --- Internal helpers ---

    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Check DT-V validation rules against the incoming request."""
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
        if not isinstance(shipper_id, str) or not shipper_id:
            return False

        # Numeric fields must be numbers (int or float) and within bounds.
        if not isinstance(weight_kg, (int, float)):
            return False
        if not isinstance(distance_km, (int, float)):
            return False
        if not isinstance(declared_value, (int, float)):
            return False

        # V2: 3 <= weight_kg <= 19400
        if not (3 <= float(weight_kg) <= 19400):
            return False

        # V3: 25 <= distance_km <= 7150
        if not (25 <= float(distance_km) <= 7150):
            return False

        # V4: 50 <= declared_value <= 83000
        if not (50 <= float(declared_value) <= 83000):
            return False

        return True


# Top-level function required by the harness

def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level façade that wires real collaborators.

    In production this would construct concrete implementations of the
    collaborators; for this exercise, we instantiate the base classes so
    that a test harness can monkeypatch or subclass them as needed.
    """
    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
