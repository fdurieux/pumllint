from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the Quote Store is unavailable or fails a storage operation."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service is unavailable (screening outage)."""


class QuoteStore:
    """Collaborator responsible for persisting quotes.

    Methods are expected to raise StoreUnavailableError on storage failures.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        On failure, raises StoreUnavailableError.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote's status and optionally its price.

        On failure, raises StoreUnavailableError.
        """

        raise NotImplementedError


class TariffEngine:
    """Collaborator responsible for pricing according to DT-P."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the freight price using DT-P rules.

        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: heavy surcharge: if weight_kg > 1244, add 341.00 (flat)
        P3: long-haul multiplier: if distance_km >= 4912, multiply running total by 1.19
        P4: price = round(result, 2)
        """

        base = 0.87 * weight_kg + 1.13 * distance_km
        # Heavy surcharge
        if weight_kg > 1244:
            base += 341.00
        # Long-haul multiplier applied after surcharge
        if distance_km >= 4912:
            base *= 1.19
        price = round(base, 2)
        return price


class ScreeningService:
    """Collaborator responsible for obtaining the risk index for a shipper.

    The screen method raises ScreeningUnavailableError on screening outage.
    """

    def screen(self, shipper_id: str) -> int:
        """Return an integer risk index for the given shipper.

        On outage, raises ScreeningUnavailableError.
        """

        raise NotImplementedError


class NotificationService:
    """Collaborator responsible for sending quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send the quote document to the shipper (fire-and-forget)."""

        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send the refusal notice to the shipper (fire-and-forget)."""

        raise NotImplementedError


@dataclass
class QuoteAPI:
    """Implements the CargoQuote quotation flow as specified.

    This class orchestrates validation (DT-V), storage, screening (DT-S),
    pricing (DT-P), and notification according to the normative documents.
    """

    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # Public entry point corresponding to the required handle(request) behavior.
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a quote request dict and return a response dict.

        Expected request keys: shipper_id, weight_kg, distance_km, declared_value.
        """

        # Step 1: Validate the request (DT-V). Invalid -> reject, stop.
        if not self._is_valid_request(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]

        # Step 2: Store the draft quote with status draft.
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

        # From here on, a draft was stored; response should carry quote_id.
        # Step 3: Request the shipper's risk index from the Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage path: price anyway (DT-P), update to held_unscreened,
            # do not notify, return price with hold: true.
            price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)
            # Update stored quote status and price; if this fails, it is outside
            # current spec's explicit error mapping and is allowed to raise.
            self.quote_store.update_quote(quote_id=quote_id, status="held_unscreened", price=price)

            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4: Apply the screening decision (DT-S) to the risk index.
        # Determine status and priced/notified behavior based on DT-S bands.
        if risk_index <= 41:
            # Accept band: priced, notified with quote document, status quoted.
            # Step 5: Price the quote (DT-P).
            price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)
            # Update stored quote with final status and price.
            self.quote_store.update_quote(quote_id=quote_id, status="quoted", price=price)

            # Step 6: Notify the shipper (fire-and-forget).
            try:
                self.notification_service.send_quote_document(
                    shipper_id=shipper_id,
                    quote_id=quote_id,
                    price=price,
                )
            except Exception:
                # Fire-and-forget: delivery failure must not change outcome/response.
                pass

            # Step 7: Return the response.
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }

        if 42 <= risk_index <= 66:
            # Review band: no price, no notification, status review_hold.
            self.quote_store.update_quote(quote_id=quote_id, status="review_hold", price=None)
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }

        # risk_index >= 67 -> refuse band: no price, refusal notice sent.
        self.quote_store.update_quote(quote_id=quote_id, status="refused_screening", price=None)
        try:
            self.notification_service.send_refusal_notice(
                shipper_id=shipper_id,
                quote_id=quote_id,
            )
        except Exception:
            # Fire-and-forget: ignore delivery failures.
            pass

        return {
            "status": "refused_screening",
            "quote_id": quote_id,
        }

    # Internal helpers

    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Check DT-V bounds for the request fields.

        V1: shipper_id present and non-empty
        V2: weight_kg number, 3 <= weight_kg <= 19400
        V3: distance_km number, 25 <= distance_km <= 7150
        V4: declared_value number, 50 <= declared_value <= 83000
        """

        # V1: shipper_id present and non-empty
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False

        # V2: weight_kg bounds
        weight_kg = request.get("weight_kg")
        if not isinstance(weight_kg, (int, float)):
            return False
        if not (3 <= weight_kg <= 19400):
            return False

        # V3: distance_km bounds
        distance_km = request.get("distance_km")
        if not isinstance(distance_km, (int, float)):
            return False
        if not (25 <= distance_km <= 7150):
            return False

        # V4: declared_value bounds
        declared_value = request.get("declared_value")
        if not isinstance(declared_value, (int, float)):
            return False
        if not (50 <= declared_value <= 83000):
            return False

        return True


# Top-level function required by the task.

def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level handle function delegating to QuoteAPI.

    This function wires concrete collaborator instances, which can be
    replaced or stubbed by a test harness by monkeypatching the
    class definitions in this module.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
