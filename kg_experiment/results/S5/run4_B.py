from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the Quote Store is unavailable for an operation."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service is unavailable or cannot return a risk index."""


class QuoteStore:
    """Persistence layer for quote records.

    The real implementation would talk to a database. In this module we
    only define the interface expected by QuoteAPI so that tests can stub
    or monkeypatch these methods.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a new draft quote and return its quote_id.

        May raise StoreUnavailableError on storage failure.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote's status and optional price.

        May raise StoreUnavailableError on storage failure.
        """

        raise NotImplementedError


class TariffEngine:
    """Pricing engine implementing DT-P."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the freight price according to DT-P.

        DT-P rules (contract/decision_table.md):
        - P1: base = 0.87 * weight_kg + 1.13 * distance_km
        - P2: if weight_kg > 1244, add 316.00
        - P3: if distance_km >= 4912, multiply running total by 1.19
        - P4: price = round(result, 2)
        """

        base = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            base += 316.00
        if distance_km >= 4912:
            base *= 1.19
        price = round(base, 2)
        return price


class ScreeningService:
    """External denied-party screening provider returning a risk index."""

    def screen(self, shipper_id: str) -> int:
        """Return the integer risk index for the given shipper.

        May raise ScreeningUnavailableError if screening cannot be performed.
        """

        raise NotImplementedError


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send the quote document for an accepted quote.

        Fire-and-forget: any delivery failures must not affect the API
        response or stored outcome.
        """

        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send the refusal notice for a refused quote.

        Fire-and-forget: any delivery failures must not affect the API
        response or stored outcome.
        """

        raise NotImplementedError


@dataclass
class QuoteRequest:
    shipper_id: Any
    weight_kg: Any
    distance_km: Any
    declared_value: Any


class QuoteAPI:
    """CargoQuote quotation orchestrator implementing the specified flow."""

    def __init__(
        self,
        quote_store: Optional[QuoteStore] = None,
        tariff_engine: Optional[TariffEngine] = None,
        screening_service: Optional[ScreeningService] = None,
        notification_service: Optional[NotificationService] = None,
    ) -> None:
        self.quote_store = quote_store or QuoteStore()
        self.tariff_engine = tariff_engine or TariffEngine()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    # --- Public API ---

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a quote request according to CargoQuote specification.

        The request dict is expected to provide the four required fields.
        The response always includes a `status` key and may include `quote_id`
        and `price` per the contract.
        """

        # Step 1: Validate request (DT-V). Invalid => rejected immediately.
        if not self._is_valid_request(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = str(request["shipper_id"])
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # Step 2: Store draft quote; on failure return error and stop.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # Step 3: Request risk index from Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Assumed policy: refuse unscreened quotes.
            status = "refused_screening"
            try:
                self.quote_store.update_quote(quote_id=quote_id, status=status)
            except StoreUnavailableError:
                # Specification does not define behaviour here; allow it to
                # propagate as a generic error rather than fabricate a status.
                raise

            # Notify refusal fire-and-forget; ignore all exceptions.
            try:
                self.notification_service.send_refusal_notice(
                    shipper_id=shipper_id,
                    quote_id=quote_id,
                )
            except Exception:
                pass

            return {"status": status, "quote_id": quote_id}

        # Step 4: Apply DT-S decision based on risk_index.
        if risk_index <= 41:
            # Accept row: priced yes, notified yes (quote document).
            status = "quoted"

            # Step 5: Price the quote (DT-P).
            price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)

            # Update stored quote with final status and price.
            try:
                self.quote_store.update_quote(quote_id=quote_id, status=status, price=price)
            except StoreUnavailableError:
                # Not specified; let it propagate instead of inventing status.
                raise

            # Step 6: Notify shipper (fire-and-forget); ignore any failures.
            try:
                self.notification_service.send_quote_document(
                    shipper_id=shipper_id,
                    quote_id=quote_id,
                    price=price,
                )
            except Exception:
                pass

            # Step 7: Return response with status, quote_id, and price.
            return {"status": status, "quote_id": quote_id, "price": price}

        if 42 <= risk_index <= 66:
            # Review row: priced no, notified no.
            status = "review_hold"
            try:
                self.quote_store.update_quote(quote_id=quote_id, status=status)
            except StoreUnavailableError:
                # Not specified; let it propagate.
                raise

            return {"status": status, "quote_id": quote_id}

        # Refuse row: risk_index >= 67, priced no, notified yes (refusal notice).
        status = "refused_screening"
        try:
            self.quote_store.update_quote(quote_id=quote_id, status=status)
        except StoreUnavailableError:
            # Not specified; let it propagate.
            raise

        try:
            self.notification_service.send_refusal_notice(
                shipper_id=shipper_id,
                quote_id=quote_id,
            )
        except Exception:
            pass

        return {"status": status, "quote_id": quote_id}

    # --- Internal helpers ---

    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Validate the request against DT-V bounds.

        Any missing field, wrong type, or out-of-bounds value makes the
        request invalid.
        """

        required_fields = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for field in required_fields:
            if field not in request:
                return False

        shipper_id = request["shipper_id"]
        if not isinstance(shipper_id, str) or not shipper_id:
            return False

        # Numeric bounds per DT-V; tolerate int/float but reject non-numeric.
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


# Module-level handle(required by harness)

_api_instance: Optional[QuoteAPI] = None


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point delegating to QuoteAPI.handle.

    A singleton QuoteAPI instance is used so that tests can monkeypatch
    collaborator classes on the module if desired.
    """

    global _api_instance
    if _api_instance is None:
        _api_instance = QuoteAPI()
    return _api_instance.handle(request)
