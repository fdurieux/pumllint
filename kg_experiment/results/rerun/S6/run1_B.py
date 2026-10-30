from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the Quote Store is unavailable for storing or updating quotes."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service is unavailable (screening outage)."""


class QuoteStore:
    """Persistence layer for quotes.

    In a real implementation, this would talk to a database. Here it's a
    stub-friendly interface: tests can monkeypatch methods or subclass.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its identifier.

        May raise StoreUnavailableError when storage fails.
        """

        # Placeholder implementation suitable for stubbing in tests.
        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote's status and optional price.

        May raise StoreUnavailableError when storage fails.
        """

        raise NotImplementedError


class TariffEngine:
    """Pricing engine implementing DT-P rules."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the freight price per DT-P.

        DT-P:
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: heavy surcharge: if weight_kg > 1244, add 341.00
        P3: long-haul multiplier: if distance_km >= 4912, multiply running total by 1.19
        P4: price = round(result, 2)
        """

        base = 0.87 * float(weight_kg) + 1.13 * float(distance_km)
        result = base
        if float(weight_kg) > 1244:
            result += 341.00
        if float(distance_km) >= 4912:
            result *= 1.19
        price = round(result, 2)
        return price


class ScreeningService:
    """External screening provider interface."""

    def screen(self, shipper_id: str) -> int:
        """Return the shipper's risk index.

        May raise ScreeningUnavailableError on outage.
        """

        raise NotImplementedError


class NotificationService:
    """External notification provider interface."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send a quote document to the shipper.

        Fire-and-forget: any delivery failure must not change the
        outcome or response. Implementations may raise, but QuoteAPI
        must swallow such errors.
        """

        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice to the shipper.

        Fire-and-forget; see send_quote_document.
        """

        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # Validation helpers implementing DT-V
    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Validate the request against DT-V bounds.

        A request is valid iff:
        - shipper_id present and non-empty
        - weight_kg number, 3 <= weight_kg <= 19400
        - distance_km number, 25 <= distance_km <= 7150
        - declared_value number, 50 <= declared_value <= 83000
        """

        # shipper_id
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False

        # weight_kg
        if "weight_kg" not in request:
            return False
        weight_kg = request["weight_kg"]
        if not isinstance(weight_kg, (int, float)):
            return False
        if not (3 <= float(weight_kg) <= 19400):
            return False

        # distance_km
        if "distance_km" not in request:
            return False
        distance_km = request["distance_km"]
        if not isinstance(distance_km, (int, float)):
            return False
        if not (25 <= float(distance_km) <= 7150):
            return False

        # declared_value
        if "declared_value" not in request:
            return False
        declared_value = request["declared_value"]
        if not isinstance(declared_value, (int, float)):
            return False
        if not (50 <= float(declared_value) <= 83000):
            return False

        return True

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a quote request according to the CargoQuote spec.

        Orchestrates validation, storage, screening, pricing, and
        notification to produce the response object.
        """

        # 1. Validate request (DT-V). Invalid -> reject, stop.
        if not self._is_valid_request(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # 2. Store draft quote with status draft.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            # storage failure -> error status, nothing else runs
            return {"status": "error: store_unavailable"}

        # Prepare base response with quote_id for all paths after draft store
        response: Dict[str, Any] = {"status": None, "quote_id": quote_id}

        # 3. Request risk index from Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_outage = False
        except ScreeningUnavailableError:
            risk_index = None  # unused in outage path
            screening_outage = True

        if screening_outage:
            # Screening outage path per DT-S note 5 / REQ-06
            price = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(quote_id, status="held_unscreened", price=price)
            except StoreUnavailableError:
                # Spec does not define behavior for update failures after draft;
                # allow exception to propagate or be handled by caller.
                raise

            response["status"] = "held_unscreened"
            response["price"] = price
            response["hold"] = True
            return response

        # 4. Apply DT-S based on risk_index when screening succeeded.
        # Determine band and act accordingly.
        if risk_index <= 41:
            # accept row -> quoted, priced, notified with quote document
            price = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(quote_id, status="quoted", price=price)
            except StoreUnavailableError:
                # Underspecified; propagate error.
                raise

            # Fire-and-forget notification: swallow failures.
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                pass

            response["status"] = "quoted"
            response["price"] = price
            return response

        if 42 <= risk_index <= 66:
            # review row -> review_hold, no price, no notification
            try:
                self.quote_store.update_quote(quote_id, status="review_hold", price=None)
            except StoreUnavailableError:
                raise

            response["status"] = "review_hold"
            return response

        # risk_index >= 67 -> refuse row
        if risk_index >= 67:
            try:
                self.quote_store.update_quote(quote_id, status="refused_screening", price=None)
            except StoreUnavailableError:
                raise

            # Fire-and-forget refusal notice.
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass

            response["status"] = "refused_screening"
            return response

        # The decision table defines the three exhaustive bands; falling
        # through would indicate an inconsistent risk_index. For safety,
        # raise rather than invent a status.
        raise ValueError(f"Unexpected risk_index value: {risk_index}")


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point wrapping QuoteAPI.handle.

    Instantiates default collaborator instances, suitable for stubbing
    in tests by replacing class attributes or monkeypatching methods.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
