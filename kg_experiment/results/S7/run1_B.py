from dataclasses import dataclass
from typing import Any, Dict


class StoreUnavailableError(Exception):
    """Raised when the Quote Store is unavailable for storing or updating quotes."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service is unavailable (screening outage)."""


class QuoteStore:
    """Persistence component for quotes.

    In this implementation, methods are stubs meant to be overridden or
    monkeypatched by a test harness.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        May raise StoreUnavailableError if storage fails.
        """
        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: float | None = None) -> None:
        """Update an existing quote's status and optional price.

        May raise StoreUnavailableError if storage fails, though behavior on such
        failures is not normatively specified.
        """
        raise NotImplementedError


class TariffEngine:
    """Tariff engine implementing DT-P pricing rules."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # P1: base calculation
        base = 0.87 * weight_kg + 1.13 * distance_km

        # P2: heavy surcharge
        if weight_kg > 1244:
            base += 316.00

        # P3: long-haul multiplier
        if distance_km >= 4912:
            base *= 1.19

        # P4: rounding to 2 decimals
        price = round(base, 2)
        return price


class ScreeningService:
    """External screening service.

    The screen method returns an integer risk_index, or raises
    ScreeningUnavailableError on outage.
    """

    def screen(self, shipper_id: str) -> int:
        raise NotImplementedError


class NotificationService:
    """Fire-and-forget notification service for quote documents and refusals."""

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

    # Validation according to DT-V
    def _validate(self, request: Dict[str, Any]) -> bool:
        # Check required fields presence
        required_fields = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for key in required_fields:
            if key not in request:
                return False

        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]

        # V1: shipper_id present and non-empty
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False

        # V2: weight_kg numeric and within bounds 3 <= weight_kg <= 19400
        if not isinstance(weight_kg, (int, float)):
            return False
        if weight_kg < 3 or weight_kg > 19400:
            return False

        # V3: distance_km numeric and within bounds 25 <= distance_km <= 7150
        if not isinstance(distance_km, (int, float)):
            return False
        if distance_km < 25 or distance_km > 7150:
            return False

        # V4: declared_value numeric and within bounds 50 <= declared_value <= 83000
        if not isinstance(declared_value, (int, float)):
            return False
        if declared_value < 50 or declared_value > 83000:
            return False

        return True

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point implementing the CargoQuote quotation flow."""

        # 1. Validate request (DT-V). Invalid -> reject, stop.
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        shipper_id: str = request["shipper_id"]
        weight_kg: float = float(request["weight_kg"])
        distance_km: float = float(request["distance_km"])
        declared_value: float = float(request["declared_value"])

        # 2. Store draft quote with status draft. On failure, return error and stop.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # From here on, response should include quote_id on all non-error/non-reject paths

        # 3. Request risk index; handle screening outage specially
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_outage = False
        except ScreeningUnavailableError:
            risk_index = None
            screening_outage = True

        # Screening outage path: price anyway, hold_unscreened, no notification
        if screening_outage:
            price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)

            # Update stored quote to held_unscreened with price
            self.quote_store.update_quote(quote_id=quote_id, status="held_unscreened", price=price)

            # No notification sent
            response: Dict[str, Any] = {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }
            return response

        # 4. Apply DT-S based on risk_index when screening succeeded
        assert risk_index is not None

        if risk_index <= 41:
            # Accept row: price, update to quoted, notify with quote document
            price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)

            self.quote_store.update_quote(quote_id=quote_id, status="quoted", price=price)

            # Fire-and-forget notification; swallow all errors
            try:
                self.notification_service.send_quote_document(
                    shipper_id=shipper_id,
                    quote_id=quote_id,
                    price=price,
                )
            except Exception:
                # Fire-and-forget: do not change outcome or response
                pass

            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }

        if 42 <= risk_index <= 66:
            # Review row: update to review_hold, no pricing, no notification
            self.quote_store.update_quote(quote_id=quote_id, status="review_hold", price=None)

            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }

        # risk_index >= 67: refuse row
        self.quote_store.update_quote(quote_id=quote_id, status="refused_screening", price=None)

        # Fire-and-forget refusal notice; swallow all errors
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


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level handle function delegating to QuoteAPI.

    In production, collaborators would be real implementations; here we
    instantiate the base classes so that a test harness can monkeypatch
    their methods or replace the classes entirely.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
