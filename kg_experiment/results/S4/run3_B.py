from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable for storing or updating."""


class ScreeningUnavailableError(Exception):
    """Raised when the screening service is unavailable (screening outage)."""


class QuoteStore:
    """Persistence collaborator for quotes.

    Methods are expected to raise StoreUnavailableError on storage failures.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a new draft quote and return its quote_id.

        In a real implementation this would insert into a database. Here this
        is a placeholder meant to be stubbed in tests.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: float | None = None) -> None:
        """Update an existing quote with its final status and optional price.

        May raise StoreUnavailableError on failure.
        """

        raise NotImplementedError


class TariffEngine:
    """Tariff calculation according to DT-P (pricing decision table)."""

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


class ScreeningService:
    """External screening provider returning a risk index for a shipper."""

    def screen(self, shipper_id: str) -> int:
        """Return risk_index, or raise ScreeningUnavailableError on outage."""

        raise NotImplementedError


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send the quote document. May raise on delivery failure, which must not affect response."""

        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send the refusal notice. May raise on delivery failure, which must not affect response."""

        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # Public API
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a quote request according to the CargoQuote specification."""

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
            # If storage fails: return error: store_unavailable; do nothing else.
            return {"status": "error: store_unavailable"}

        # From here on, we must include quote_id in successful responses.

        # 3. Request the shipper's risk index from the Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_outage = False
        except ScreeningUnavailableError:
            risk_index = None
            screening_outage = True

        if screening_outage:
            # Screening outage path per spec: price anyway, store held_unscreened,
            # do not notify, return price and hold: true.
            price = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(quote_id, status="held_unscreened", price=price)
            except StoreUnavailableError:
                # Spec does not define behavior for update failures after draft;
                # we do not alter the response.
                pass

            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4. Apply the screening decision (DT-S) to the risk index.
        assert risk_index is not None
        if risk_index <= 41:
            # Accept row
            status = "quoted"
            # 5. Price the quote (DT-P) — only on priced rows.
            price = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(quote_id, status=status, price=price)
            except StoreUnavailableError:
                # Update failure after initial storage is unspecified; ignore for response.
                pass

            # 6. Notify the shipper — fire-and-forget.
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                # Notification delivery failure must not change outcome or response.
                pass

            # 7. Return the response.
            return {
                "status": status,
                "quote_id": quote_id,
                "price": price,
            }
        elif 42 <= risk_index <= 66:
            # Review row
            status = "review_hold"
            try:
                self.quote_store.update_quote(quote_id, status=status, price=None)
            except StoreUnavailableError:
                pass

            # No pricing, no notification on review path.
            return {
                "status": status,
                "quote_id": quote_id,
            }
        else:
            # Refuse row: risk_index >= 67
            status = "refused_screening"
            try:
                self.quote_store.update_quote(quote_id, status=status, price=None)
            except StoreUnavailableError:
                pass

            # No pricing on refused.
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                # Fire-and-forget: ignore delivery failure.
                pass

            return {
                "status": status,
                "quote_id": quote_id,
            }

    # Internal helpers
    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Check DT-V validation rules on the request object."""

        # Required fields present
        required_fields = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for field in required_fields:
            if field not in request:
                return False

        shipper_id = request["shipper_id"]
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False

        # Numeric bounds as per DT-V, with basic type coercion.
        try:
            weight = float(request["weight_kg"])
            distance = float(request["distance_km"])
            declared = float(request["declared_value"])
        except (TypeError, ValueError):
            return False

        if not (3 <= weight <= 19400):
            return False
        if not (25 <= distance <= 7150):
            return False
        if not (50 <= declared <= 83000):
            return False

        return True


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point matching the project contract.

    Instantiates real collaborators; in tests these classes are
    expected to be stubbed or replaced.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
