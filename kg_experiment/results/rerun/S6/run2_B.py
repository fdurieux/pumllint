from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the Quote Store is unavailable for storage operations."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service is unavailable/outaged."""


class QuoteStore:
    """Persistence boundary for quotes.

    Methods are designed to be stubbed by tests. On storage failure they
    must raise StoreUnavailableError as per requirements.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        May raise StoreUnavailableError on failure.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote with the final status and optional price.

        The specification only defines behavior for failure of the initial
        draft store; any errors here are considered out of scope.
        """

        raise NotImplementedError


class TariffEngine:
    """Tariff/pricing engine implementing DT-P."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the freight price according to DT-P.

        DT-P rules (contract/decision_table.md):
        - P1: base = 0.87 * weight_kg + 1.13 * distance_km
        - P2: if weight_kg > 1244, add 341.00 (flat)
        - P3: if distance_km >= 4912, multiply running total by 1.19 (after P2)
        - P4: price = round(result, 2)
        """

        # P1: base calculation
        result = 0.87 * weight_kg + 1.13 * distance_km

        # P2: heavy surcharge
        if weight_kg > 1244:
            result += 341.00

        # P3: long-haul multiplier
        if distance_km >= 4912:
            result *= 1.19

        # P4: rounding
        return round(result, 2)


class ScreeningService:
    """External screening provider boundary."""

    def screen(self, shipper_id: str) -> int:
        """Return the risk_index for the given shipper.

        May raise ScreeningUnavailableError on outage.
        """

        raise NotImplementedError


class NotificationService:
    """External messaging provider boundary."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send a quote document to the shipper.

        Delivery failure must not change the response; the implementation
        of this method may raise, but QuoteAPI will ignore such errors.
        """

        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice to the shipper.

        Delivery failure must not change the response; the implementation
        of this method may raise, but QuoteAPI will ignore such errors.
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
        """Handle a CargoQuote quote request.

        Expects a dict with keys: shipper_id, weight_kg, distance_km,
        declared_value. Returns a dict with at least key "status".
        """

        # 1. Validate the request (DT-V). Invalid → reject, stop.
        if not self._is_request_valid(request):
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
            # storage failure → error: store_unavailable, nothing else runs
            return {"status": "error: store_unavailable"}

        # 3. Request the shipper's risk index from the Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # screening outage path (DT-S note 5 / spec step 3)
            price = self.tariff_engine.price(weight_kg, distance_km)
            # Update stored quote to held_unscreened with price
            self.quote_store.update_quote(quote_id, status="held_unscreened", price=price)
            # No notification is sent on this path.
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4. Apply the screening decision (DT-S) to the risk index.
        # Determine DT-S band based on risk_index.
        if risk_index <= 41:
            # Accept row
            price = self.tariff_engine.price(weight_kg, distance_km)
            # Update stored quote to quoted with price
            self.quote_store.update_quote(quote_id, status="quoted", price=price)

            # Notify shipper with quote document (fire-and-forget)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                # Notification delivery failure must not change outcome/response
                pass

            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }

        if 42 <= risk_index <= 66:
            # Review row: no price, no notification
            self.quote_store.update_quote(quote_id, status="review_hold", price=None)
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }

        # risk_index >= 67 → refused row
        self.quote_store.update_quote(quote_id, status="refused_screening", price=None)

        # Notify shipper with refusal notice (fire-and-forget)
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            # Notification delivery failure must not change outcome/response
            pass

        return {
            "status": "refused_screening",
            "quote_id": quote_id,
        }

    # --- Internal helpers ---

    def _is_request_valid(self, request: Dict[str, Any]) -> bool:
        """Check DT-V validation rules on the incoming request.

        Rules (contract/decision_table.md DT-V):
        - V1 shipper_id: present and non-empty
        - V2 weight_kg: number, 3 <= weight_kg <= 19400
        - V3 distance_km: number, 25 <= distance_km <= 7150
        - V4 declared_value: number, 50 <= declared_value <= 83000
        """

        # Required keys presence
        required_keys = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for key in required_keys:
            if key not in request:
                return False

        shipper_id = request["shipper_id"]
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False

        # Numeric bounds with tolerant casting to float
        try:
            weight_kg = float(request["weight_kg"])
            distance_km = float(request["distance_km"])
            declared_value = float(request["declared_value"])
        except (TypeError, ValueError):
            return False

        if not (3 <= weight_kg <= 19400):
            return False
        if not (25 <= distance_km <= 7150):
            return False
        if not (50 <= declared_value <= 83000):
            return False

        return True


# Module-level handler expected by the harness

def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point wrapping QuoteAPI for ease of testing.

    This constructs concrete collaborators; tests may monkeypatch these
    classes or methods by name to provide stubs.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
