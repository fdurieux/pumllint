from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
import math


class StoreUnavailableError(Exception):
    """Raised when the Quote Store is unavailable for storing drafts or updates."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service is unavailable (screening outage)."""


class QuoteStore:
    """Persistence boundary for quote drafts and updates.

    Methods are expected to raise StoreUnavailableError on storage failures.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        On failure, must raise StoreUnavailableError.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: float | None = None) -> None:
        """Update an existing quote's status, and optionally its price.

        Error behavior is not specified beyond initial storage failure; any
        StoreUnavailableError here is not handled specially by the flow.
        """

        raise NotImplementedError


class TariffEngine:
    """Pricing engine implementing DT-P."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute price according to DT-P.

        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00
        P3: if distance_km >= 4912, multiply running total by 1.19
        P4: price = round(result, 2)
        """

        base = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            base += 316.00
        if distance_km >= 4912:
            base *= 1.19
        price = round(base, 2)
        return price


class ScreeningService:
    """External screening provider boundary."""

    def screen(self, shipper_id: str) -> int:
        """Return integer risk_index for the given shipper.

        On screening outage, must raise ScreeningUnavailableError.
        """

        raise NotImplementedError


class NotificationService:
    """External notification provider boundary.

    Delivery failures must not affect the main flow outcome; methods are
    therefore called in a fire-and-forget style and any exceptions are
    swallowed by QuoteAPI.
    """

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # --- Public entry point ---

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an instant freight quotation request.

        Implements the flow defined in spec.md and decision_table.md.
        """

        # 1. Validate the request (DT-V). Invalid → reject, stop.
        if not self._is_valid_request(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # 2. Store the draft quote in the Quote Store with status `draft`.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            # storage failure → error status; nothing else runs
            return {"status": "error: store_unavailable"}

        # 3. Request the shipper's risk index from the Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage path: price anyway, update to held_unscreened,
            # no notification, response carries price and hold: true.
            price = self.tariff_engine.price(weight_kg, distance_km)
            # Stored with status held_unscreened and price.
            self.quote_store.update_quote(quote_id, status="held_unscreened", price=price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4. Apply the screening decision (DT-S) to the risk index.
        # Determine band according to DT-S boundaries.
        if risk_index <= 41:
            # Accept row: priced, notified with quote document, status quoted.
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, status="quoted", price=price)
            # Fire-and-forget notification: failures must not affect outcome.
            try:
                self.notification_service.send_quote_document(
                    shipper_id=shipper_id,
                    quote_id=quote_id,
                    price=price,
                )
            except Exception:
                # Explicitly ignore any notification delivery failure.
                pass
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }

        if 42 <= risk_index <= 66:
            # Review row: not priced, not notified, status review_hold.
            self.quote_store.update_quote(quote_id, status="review_hold", price=None)
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }

        # risk_index >= 67 → refuse row.
        self.quote_store.update_quote(quote_id, status="refused_screening", price=None)
        # Fire-and-forget refusal notice.
        try:
            self.notification_service.send_refusal_notice(
                shipper_id=shipper_id,
                quote_id=quote_id,
            )
        except Exception:
            pass
        return {
            "status": "refused_screening",
            "quote_id": quote_id,
        }

    # --- Internal helpers ---

    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Validate request per DT-V bounds.

        A request is valid iff all of:
        - shipper_id present and non-empty string
        - weight_kg is a number, 3 <= weight_kg <= 19400
        - distance_km is a number, 25 <= distance_km <= 7150
        - declared_value is a number, 50 <= declared_value <= 83000
        """

        # Presence checks
        required_fields = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for field in required_fields:
            if field not in request:
                return False

        # shipper_id: present and non-empty string
        shipper_id = request["shipper_id"]
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False

        # Numeric fields with inclusive bounds
        if not self._valid_number_in_range(request["weight_kg"], 3, 19400):
            return False
        if not self._valid_number_in_range(request["distance_km"], 25, 7150):
            return False
        if not self._valid_number_in_range(request["declared_value"], 50, 83000):
            return False

        return True

    @staticmethod
    def _valid_number_in_range(value: Any, minimum: float, maximum: float) -> bool:
        """Return True if value is a finite number within [minimum, maximum]."""

        if not isinstance(value, (int, float)):
            return False
        if isinstance(value, bool):
            # bool is subclass of int; explicitly reject to avoid surprises.
            return False
        if not math.isfinite(float(value)):
            return False
        numeric = float(value)
        if numeric < minimum or numeric > maximum:
            return False
        return True


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level handle function delegating to QuoteAPI.

    This is the function expected by the harness.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
