from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable for storing or updating."""


class ScreeningUnavailableError(Exception):
    """Raised when the screening service is unavailable/outaged."""


class QuoteStore:
    """Persistence layer for quotes.

    This default implementation is a stub meant to be overridden by tests.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its identifier.

        May raise StoreUnavailableError on failure.
        """

        # Simple in-memory stub: generate a dummy ID.
        # In real use, this would persist to a database.
        return "Q-1"

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote with new status and optional price.

        May raise StoreUnavailableError on failure.
        """

        # Stub: do nothing.
        return None


class TariffEngine:
    """Tariff rules engine implementing DT-P pricing."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # P1: base = 0.87 * weight_kg + 1.13 * distance_km
        result = 0.87 * weight_kg + 1.13 * distance_km
        # P2: heavy surcharge
        if weight_kg > 1244:
            result += 316.00
        # P3: long-haul multiplier after P2
        if distance_km >= 4912:
            result *= 1.19
        # P4: round to 2 decimal places
        price = round(result, 2)
        return price


class ScreeningService:
    """External screening provider returning a shipper risk index."""

    def screen(self, shipper_id: str) -> int:
        """Return an integer risk index for the given shipper.

        May raise ScreeningUnavailableError on outage.
        """

        # Stub: always low risk.
        return 0


class NotificationService:
    """External notification provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send a quote document to the shipper.

        Failures are fire-and-forget at the caller: any exception here
        must not change the response of the API.
        """

        # Stub: do nothing.
        return None

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice to the shipper.

        Failures are fire-and-forget at the caller.
        """

        # Stub: do nothing.
        return None


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # --- Public API ---

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point implementing the CargoQuote quotation flow.

        The request dict must contain shipper_id, weight_kg, distance_km,
        and declared_value. The response dict will contain at least a
        status field and possibly quote_id, price, and hold.
        """

        # 1. Validate the request (DT-V). Invalid -> reject, stop.
        if not self._is_valid_request(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = str(request["shipper_id"])
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # 2. Store the draft quote with status draft.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            # Storage failure -> error: store_unavailable, nothing else runs.
            return {"status": "error: store_unavailable"}

        # From here on, we have a stored draft and must include quote_id.

        # 3. Request risk index from Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage path.
            price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)
            # Update stored quote to held_unscreened with price.
            self.quote_store.update_quote(quote_id=quote_id, status="held_unscreened", price=price)
            # No notification on outage; response carries price and hold: true.
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4. Apply screening decision (DT-S) using risk_index.
        # Assumed thresholds: accept < 40; 40-65 review; > 65 refuse.
        if risk_index < 40:
            # Accept row: priced and notified.
            price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)
            # Update stored quote to quoted with price.
            self.quote_store.update_quote(quote_id=quote_id, status="quoted", price=price)

            # Notify shipper with quote document (fire-and-forget).
            try:
                self.notification_service.send_quote_document(
                    shipper_id=shipper_id,
                    quote_id=quote_id,
                    price=price,
                )
            except Exception:
                # Fire-and-forget: ignore failures.
                pass

            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }

        if 40 <= risk_index <= 65:
            # Review row: held for manual review, not priced, not notified.
            self.quote_store.update_quote(quote_id=quote_id, status="review_hold", price=None)
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }

        # Refuse row: refused, not priced, refusal notice sent.
        self.quote_store.update_quote(quote_id=quote_id, status="refused_screening", price=None)

        try:
            self.notification_service.send_refusal_notice(shipper_id=shipper_id, quote_id=quote_id)
        except Exception:
            # Fire-and-forget: ignore failures.
            pass

        return {
            "status": "refused_screening",
            "quote_id": quote_id,
        }

    # --- Internal helpers ---

    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Validate request according to DT-V rules.

        Returns True iff all DT-V constraints hold, otherwise False.
        Any missing or malformed field results in invalid.
        """

        required_keys = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for key in required_keys:
            if key not in request:
                return False

        shipper_id = request["shipper_id"]
        if not isinstance(shipper_id, str) or not shipper_id:
            return False

        # Helper to extract numeric with bounds.
        def in_range_numeric(value: Any, lower: float, upper: float) -> bool:
            try:
                num = float(value)
            except (TypeError, ValueError):
                return False
            return lower <= num <= upper

        if not in_range_numeric(request["weight_kg"], 3, 19400):
            return False
        if not in_range_numeric(request["distance_km"], 25, 7150):
            return False
        if not in_range_numeric(request["declared_value"], 50, 83000):
            return False

        return True


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level handle function delegating to QuoteAPI.

    Constructs default collaborator instances which can be replaced
    by stubbing the respective classes/methods in tests.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
