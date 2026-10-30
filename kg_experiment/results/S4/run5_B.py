from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable for storing or updating."""


class ScreeningUnavailableError(Exception):
    """Raised when the screening service is unavailable (screening outage)."""


class QuoteStore:
    """Persistence interface for quote records.

    The actual storage backend is out of scope; this class is intended to be
    stubbed or overridden by tests.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        May raise StoreUnavailableError on failure.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: float | None = None) -> None:
        """Update an existing quote's status and optionally its price.

        May raise StoreUnavailableError on failure.
        """

        raise NotImplementedError


class TariffEngine:
    """Pricing engine implementing DT-P (decision_table.md)."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute price per DT-P.

        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: heavy surcharge: if weight_kg > 1244, add 316.00
        P3: long-haul multiplier: if distance_km >= 4912, multiply running total by 1.19
        P4: price = round(result, 2)
        """

        base = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            base += 316.00
        if distance_km >= 4912:
            base *= 1.19
        return round(base, 2)


class ScreeningService:
    """External service providing a risk index for a shipper."""

    def screen(self, shipper_id: str) -> int:
        """Return risk index for the given shipper.

        May raise ScreeningUnavailableError on outage.
        """

        raise NotImplementedError


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send quote document to the shipper.

        Fire-and-forget: any delivery failure must not affect the outcome.
        """

        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send refusal notice to the shipper.

        Fire-and-forget: any delivery failure must not affect the outcome.
        """

        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    def _validate(self, request: Dict[str, Any]) -> bool:
        """Validate request according to DT-V.

        Returns True if valid, False otherwise.
        """

        # Required fields
        required_fields = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for field in required_fields:
            if field not in request:
                return False

        shipper_id = request.get("shipper_id")
        weight_kg = request.get("weight_kg")
        distance_km = request.get("distance_km")
        declared_value = request.get("declared_value")

        # V1: shipper_id present and non-empty
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False

        # Helper to check numeric values and bounds
        def is_number(value: Any) -> bool:
            return isinstance(value, (int, float)) and not isinstance(value, bool)

        # V2: weight_kg: number, 3 <= weight_kg <= 19400
        if not is_number(weight_kg):
            return False
        if not (3 <= float(weight_kg) <= 19400):
            return False

        # V3: distance_km: number, 25 <= distance_km <= 7150
        if not is_number(distance_km):
            return False
        if not (25 <= float(distance_km) <= 7150):
            return False

        # V4: declared_value: number, 50 <= declared_value <= 83000
        if not is_number(declared_value):
            return False
        if not (50 <= float(declared_value) <= 83000):
            return False

        return True

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a quote request according to the CargoQuote specification.

        The request dict must contain shipper_id, weight_kg, distance_km,
        and declared_value. The response dict always has a status field and
        may include quote_id, price, and hold in the cases defined by the
        contract.
        """

        # 1. Validate the request (DT-V). Invalid → reject, stop.
        if not self._validate(request):
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
            # On storage failure: status error: store_unavailable; nothing else runs.
            return {"status": "error: store_unavailable"}

        # From here on, a draft was stored; quote_id must be present in responses.

        # 3. Request the shipper's risk index from the Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage path.
            # Price anyway (DT-P), update stored quote to held_unscreened,
            # do not notify, and return price with hold: true.
            price = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(quote_id, status="held_unscreened", price=price)
            except StoreUnavailableError:
                # Assumption: propagate or ignore is unspecified; we ignore update
                # failure here with respect to the response, keeping the normative
                # API behavior.
                pass
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4. Apply the screening decision (DT-S) to the risk index.
        if risk_index <= 41:
            # Accept row: priced and notified; status quoted.
            price = self.tariff_engine.price(weight_kg, distance_km)
            # Update stored quote to quoted with price.
            self.quote_store.update_quote(quote_id, status="quoted", price=price)

            # Notify the shipper with quote document; fire-and-forget.
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                # Notification delivery failure must not change outcome or response.
                pass

            return {"status": "quoted", "quote_id": quote_id, "price": price}

        if 42 <= risk_index <= 66:
            # Review row: not priced, not notified; status review_hold.
            self.quote_store.update_quote(quote_id, status="review_hold", price=None)
            return {"status": "review_hold", "quote_id": quote_id}

        # Refuse row: risk_index >= 67
        self.quote_store.update_quote(quote_id, status="refused_screening", price=None)

        # Notify refusal; fire-and-forget.
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            # Notification delivery failure must not change outcome or response.
            pass

        return {"status": "refused_screening", "quote_id": quote_id}


# Module-level handle function required by the task.

def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point that wires default collaborators and handles the request.

    For production, QuoteStore, TariffEngine, ScreeningService, and
    NotificationService should be provided by the surrounding application.
    Here we instantiate the bare classes so that tests can monkeypatch or
    subclass them as needed.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
