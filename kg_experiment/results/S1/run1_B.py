from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the Quote Store is unavailable for storage operations."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service is unavailable."""


class QuoteStore:
    """Persistence adapter for quote drafts and updates.

    Methods are expected to raise StoreUnavailableError when storage fails.
    """

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """Store a new draft quote and return its quote_id.

        May raise StoreUnavailableError on failure.
        """
        raise NotImplementedError

    def update_quote(
        self,
        quote_id: str,
        status: str,
        price: Optional[float] = None,
    ) -> None:
        """Update an existing quote's status (and optionally price).

        May raise StoreUnavailableError on failure.
        """
        raise NotImplementedError


class TariffEngine:
    """Tariff engine implementing DT-P pricing rules."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the freight price according to DT-P.

        DT-P:
          P1: base = 0.87 * weight_kg + 1.13 * distance_km
          P2: if weight_kg > 1244, add 316.00
          P3: if distance_km >= 4912, multiply running total by 1.19 (after P2)
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
    """External screening provider for shipper risk index."""

    def screen(self, shipper_id: str) -> int:
        """Return the risk_index for the given shipper.

        May raise ScreeningUnavailableError when the service is unavailable.
        """
        raise NotImplementedError


class NotificationService:
    """External notification provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send a quote document to the shipper.

        Delivery failures must not change the response or stored outcome.
        """
        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice to the shipper.

        Delivery failures must not change the response or stored outcome.
        """
        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # --- Public entry point ---

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a CargoQuote request as per the specification.

        The request dict must contain: shipper_id (str), weight_kg (number),
        distance_km (number), declared_value (number). Validation follows DT-V.
        """
        # 1. Validate the request (DT-V). Invalid -> reject, stop.
        #    On invalid: no draft stored, no screening, no pricing, no notification.
        validation_error = self._validate(request)
        if validation_error is not None:
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
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
            # storage failure -> error: store_unavailable, nothing else runs
            return {"status": "error: store_unavailable"}

        # From here on, a draft was stored; response must include quote_id.

        # 3. Request risk_index from Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage: price anyway, update to held_unscreened, no notify,
            # return price and hold: true.
            price = self.tariff_engine.price(weight_kg, distance_km)
            # Update stored quote status and price. Any StoreUnavailableError here
            # is not specified; allow it to propagate.
            self.quote_store.update_quote(
                quote_id=quote_id,
                status="held_unscreened",
                price=price,
            )
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4. Apply DT-S to the risk_index and drive subsequent steps.
        if risk_index <= 41:
            # Accept row: priced, notified (quote document), status quoted.
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(
                quote_id=quote_id,
                status="quoted",
                price=price,
            )
            # Notification is fire-and-forget: swallow any exception.
            try:
                self.notification_service.send_quote_document(
                    shipper_id=shipper_id,
                    quote_id=quote_id,
                    price=price,
                )
            except Exception:
                # Explicitly ignore notification failures.
                pass
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        if 42 <= risk_index <= 66:
            # Review row: stored as review_hold, no pricing, no notification.
            self.quote_store.update_quote(
                quote_id=quote_id,
                status="review_hold",
                price=None,
            )
            return {"status": "review_hold", "quote_id": quote_id}

        if risk_index >= 67:
            # Refuse row: refused_screening, no pricing, notified (refusal notice).
            self.quote_store.update_quote(
                quote_id=quote_id,
                status="refused_screening",
                price=None,
            )
            try:
                self.notification_service.send_refusal_notice(
                    shipper_id=shipper_id,
                    quote_id=quote_id,
                )
            except Exception:
                # Fire-and-forget: ignore delivery failures.
                pass
            return {"status": "refused_screening", "quote_id": quote_id}

        # The spec defines DT-S bands that cover all integers, but if an
        # out-of-range value somehow appears, treat it as implementation error.
        raise ValueError(f"Unexpected risk_index value: {risk_index}")

    # --- Internal helpers ---

    def _validate(self, request: Dict[str, Any]) -> Optional[str]:
        """Validate request according to DT-V.

        Returns None if valid, or a string describing the first error
        (for debugging/logging). The handle() method only cares about
        valid vs invalid to set status.
        """
        # V1: shipper_id present and non-empty
        if "shipper_id" not in request:
            return "missing shipper_id"
        shipper_id = request["shipper_id"]
        if not isinstance(shipper_id, str) or shipper_id == "":
            return "invalid shipper_id"

        # Helper to extract numeric fields and check bounds
        def _num_field(name: str, min_v: float, max_v: float) -> Optional[str]:
            if name not in request:
                return f"missing {name}"
            value = request[name]
            try:
                num = float(value)
            except (TypeError, ValueError):
                return f"non-numeric {name}"
            if num < min_v or num > max_v:
                return f"out-of-bounds {name}"
            return None

        # V2: weight_kg number, 3 <= weight_kg <= 19400
        err = _num_field("weight_kg", 3.0, 19400.0)
        if err is not None:
            return err

        # V3: distance_km number, 25 <= distance_km <= 7150
        err = _num_field("distance_km", 25.0, 7150.0)
        if err is not None:
            return err

        # V4: declared_value number, 50 <= declared_value <= 83000
        err = _num_field("declared_value", 50.0, 83000.0)
        if err is not None:
            return err

        return None


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level handle function delegating to QuoteAPI.

    A simple default wiring that can be replaced/stubbed in tests by
    monkeypatching the collaborator classes or QuoteAPI.
    """
    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
