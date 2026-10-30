from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable for storing or updating quotes."""


class ScreeningUnavailableError(Exception):
    """Raised when the screening service is unavailable or cannot return a risk index."""


class QuoteStore:
    """Persistence layer for quotes.

    The real implementation is expected to raise StoreUnavailableError if
    the underlying storage is unavailable.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return a quote_id.

        May raise StoreUnavailableError on failure.
        """

        # Placeholder in-memory implementation; test harness is expected to stub.
        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote's status and optionally its price.

        May raise StoreUnavailableError on failure.
        """

        # Placeholder in-memory implementation; test harness is expected to stub.
        raise NotImplementedError


class TariffEngine:
    """Applies DT-P pricing rules."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # P1: base
        result = 0.87 * weight_kg + 1.13 * distance_km
        # P2: heavy surcharge
        if weight_kg > 1244:
            result += 341.00
        # P3: long-haul multiplier
        if distance_km >= 4912:
            result *= 1.19
        # P4: round to 2 decimals
        return round(result, 2)


class ScreeningService:
    """External screening provider interface."""

    def screen(self, shipper_id: str) -> int:
        """Return an integer risk index or raise ScreeningUnavailableError on outage."""

        raise NotImplementedError


class NotificationService:
    """External notification provider interface."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Fire-and-forget sending of a quote document.

        Any exception indicates delivery failure and must not affect the
        outcome or response.
        """

        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Fire-and-forget sending of a refusal notice."""

        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # Public API entry point -------------------------------------------------
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a CargoQuote request.

        request keys: shipper_id, weight_kg, distance_km, declared_value
        Returns a response dict with at least a "status" key.
        """

        # Step 1: Validate request per DT-V
        validation_error = self._validate(request)
        if validation_error is not None:
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # Step 2: Store draft quote with status draft
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            # REQ-05: storage failure → error: store_unavailable, nothing else runs
            return {"status": "error: store_unavailable"}

        # From this point on, quote_id exists and must be included in responses

        # Step 3: Request risk index from Screening Service
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage path (DT-S note 5 / REQ-06)
            price = self.tariff_engine.price(weight_kg, distance_km)
            # Update stored quote to held_unscreened with price
            self.quote_store.update_quote(quote_id, status="held_unscreened", price=price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4: Apply DT-S to risk_index
        if risk_index <= 41:
            # Accept row
            price = self.tariff_engine.price(weight_kg, distance_km)
            # Update stored quote to quoted with price
            self.quote_store.update_quote(quote_id, status="quoted", price=price)
            # Notify shipper with quote document (fire-and-forget)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                # Fire-and-forget: ignore delivery failures
                pass
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }
        elif 42 <= risk_index <= 66:
            # Review row: no price, no notification
            self.quote_store.update_quote(quote_id, status="review_hold", price=None)
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        else:
            # risk_index >= 67 → refuse row: no price, refusal notice sent
            self.quote_store.update_quote(quote_id, status="refused_screening", price=None)
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                # Fire-and-forget
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }

    # Internal helpers --------------------------------------------------------
    def _validate(self, request: Dict[str, Any]) -> Optional[str]:
        """Validate the request against DT-V.

        Returns None if valid, or a string describing the error otherwise.
        The specific error text is not surfaced in the API response, which
        only distinguishes valid vs invalid.
        """

        # V1: shipper_id present and non-empty
        if "shipper_id" not in request:
            return "missing shipper_id"
        shipper_id = request["shipper_id"]
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return "invalid shipper_id"

        # Helper to coerce numeric fields
        def _as_number(value: Any, field_name: str) -> Optional[float]:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        # V2: weight_kg number, 3 <= weight_kg <= 19400
        if "weight_kg" not in request:
            return "missing weight_kg"
        weight = _as_number(request["weight_kg"], "weight_kg")
        if weight is None or not (3 <= weight <= 19400):
            return "invalid weight_kg"

        # V3: distance_km number, 25 <= distance_km <= 7150
        if "distance_km" not in request:
            return "missing distance_km"
        distance = _as_number(request["distance_km"], "distance_km")
        if distance is None or not (25 <= distance <= 7150):
            return "invalid distance_km"

        # V4: declared_value number, 50 <= declared_value <= 83000
        if "declared_value" not in request:
            return "missing declared_value"
        declared = _as_number(request["declared_value"], "declared_value")
        if declared is None or not (50 <= declared <= 83000):
            return "invalid declared_value"

        return None


# Module-level handle function expected by the harness ------------------------

def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point that wires default collaborators.

    A test harness is expected to monkeypatch or stub the collaborators
    (QuoteStore, TariffEngine, ScreeningService, NotificationService)
    as needed.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
