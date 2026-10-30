from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


class StoreUnavailableError(Exception):
    """Raised when the Quote Store is unavailable for storage operations."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service is unavailable (screening outage)."""


class QuoteStore:
    """Persistence gateway for quotes.

    Methods are expected to raise StoreUnavailableError on storage failures.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        May raise StoreUnavailableError if storage is unavailable.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: float | None = None) -> None:
        """Update an existing quote's status (and optionally price).

        May raise StoreUnavailableError if storage is unavailable.
        """

        raise NotImplementedError


class TariffEngine:
    """Tariff pricing engine implementing DT-P (pricing decision table)."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute price according to DT-P.

        DT-P (contract/decision_table.md):
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: heavy surcharge: if weight_kg > 1244, add 316.00 (flat)
        P3: long-haul multiplier: if distance_km >= 4912, multiply running total by 1.19
            (applied after P2)
        P4: price = round(result, 2)
        """

        base = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            base += 316.0
        if distance_km >= 4912:
            base *= 1.19
        price = round(base, 2)
        return price


class ScreeningService:
    """External screening provider returning a risk index for a shipper."""

    def screen(self, shipper_id: str) -> int:
        """Return risk_index as integer, or raise ScreeningUnavailableError on outage."""

        raise NotImplementedError


class NotificationService:
    """External notification provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send a quote document. Failures must not affect outcome/response."""

        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice. Failures must not affect outcome/response."""

        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    def _validate(self, request: Dict[str, Any]) -> bool:
        """Validate request according to DT-V.

        DT-V rules (contract/decision_table.md):
        V1: shipper_id present and non-empty
        V2: weight_kg is number, 3 <= weight_kg <= 19400
        V3: distance_km is number, 25 <= distance_km <= 7150
        V4: declared_value is number, 50 <= declared_value <= 83000
        """

        # Presence and basic type/emptiness checks
        if "shipper_id" not in request or not isinstance(request["shipper_id"], str) or not request["shipper_id"]:
            return False

        for field, min_v, max_v in (
            ("weight_kg", 3, 19400),
            ("distance_km", 25, 7150),
            ("declared_value", 50, 83000),
        ):
            if field not in request:
                return False
            value = request[field]
            if not isinstance(value, (int, float)):
                return False
            if value < min_v or value > max_v:
                return False

        return True

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an instant freight quotation request per the CargoQuote spec.

        Implements the flow and decision semantics described in:
        - contract/spec.md
        - contract/decision_table.md (DT-V, DT-S, DT-P)
        - kit/requirements.md
        """

        # 1. Validate the request (DT-V). Invalid → reject, stop.
        #    Response: status 'rejected: invalid_request'.
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = float(request["weight_kg"])  # safe per validation
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # 2. Store the draft quote with status 'draft'. On failure: error status, stop.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # 3. Request risk index from Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage path: price anyway, update to held_unscreened, no notification.
            price = self.tariff_engine.price(weight_kg, distance_km)
            # Update stored quote status and price. If this fails, spec is silent; let it raise.
            self.quote_store.update_quote(quote_id, status="held_unscreened", price=price)
            return {"status": "held_unscreened", "quote_id": quote_id, "price": price, "hold": True}

        # 4. Apply screening decision (DT-S) based on risk_index.
        #    Map risk_index to outcome band.
        response: Dict[str, Any] = {"quote_id": quote_id}

        if risk_index <= 41:
            # Accept row: priced, notified (quote document), status 'quoted'.
            price = self.tariff_engine.price(weight_kg, distance_km)
            # Update stored quote with final status and price.
            self.quote_store.update_quote(quote_id, status="quoted", price=price)

            # Fire-and-forget notification: swallow any delivery failure.
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                # Per spec, delivery failure never changes stored quote or response.
                pass

            response["status"] = "quoted"
            response["price"] = price
            return response

        if 42 <= risk_index <= 66:
            # Review row: no price, no notification, status 'review_hold'.
            self.quote_store.update_quote(quote_id, status="review_hold", price=None)
            response["status"] = "review_hold"
            return response

        # Refuse row: risk_index >= 67
        # No price, refusal notice sent, status 'refused_screening'.
        self.quote_store.update_quote(quote_id, status="refused_screening", price=None)

        # Fire-and-forget refusal notice; swallow failures.
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            pass

        response["status"] = "refused_screening"
        return response


# Module-level handle function for the test harness.

def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point that wires default collaborators and delegates to QuoteAPI.

    In production/tests, collaborators can be monkeypatched or subclassed by class
    and method name as required by the harness.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
