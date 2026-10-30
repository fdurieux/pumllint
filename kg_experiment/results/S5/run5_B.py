from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the QuoteStore is unavailable for storing or updating quotes."""


class ScreeningUnavailableError(Exception):
    """Raised when the ScreeningService cannot provide a risk index (outage)."""


class QuoteStore:
    """Persistence layer for quotes.

    Methods are expected to raise StoreUnavailableError on storage failures.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        In a real implementation this would persist to a database.
        Here we provide a stub that can be overridden in tests.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote with final status and optional price."""

        raise NotImplementedError


class TariffEngine:
    """Computes prices according to DT-P (pricing decision table)."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the freight price following DT-P rules.

        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: heavy surcharge: if weight_kg > 1244, add 316.00 (flat)
        P3: long-haul multiplier: if distance_km >= 4912, multiply the running
            total by 1.19, applied after P2
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
    """External screening provider returning a risk index for a shipper."""

    def screen(self, shipper_id: str) -> int:
        """Return an integer risk index for the given shipper.

        May raise ScreeningUnavailableError to signal an outage.
        """

        raise NotImplementedError


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send a quote document to the shipper (fire-and-forget)."""

        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice to the shipper (fire-and-forget)."""

        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    def _validate(self, request: Dict[str, Any]) -> bool:
        """Validate the incoming request according to DT-V.

        A request is valid iff all required fields are present and within
        their numeric bounds. Any violation yields invalid_request.
        """

        # Required fields
        required_fields = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for field in required_fields:
            if field not in request:
                return False

        # shipper_id: present and non-empty string
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False

        # Numeric bounds per DT-V
        try:
            weight_kg = float(request.get("weight_kg"))
            distance_km = float(request.get("distance_km"))
            declared_value = float(request.get("declared_value"))
        except (TypeError, ValueError):
            return False

        if not (3 <= weight_kg <= 19400):
            return False
        if not (25 <= distance_km <= 7150):
            return False
        if not (50 <= declared_value <= 83000):
            return False

        return True

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a quote request and return the outcome response dict.

        The orchestration follows the flow and decision rules defined in the
        specification and decision tables.
        """

        # Step 1: Validate the request (DT-V). Invalid -> reject, stop.
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # Step 2: Store the draft quote with status draft.
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

        # From this point on, the response must include quote_id.
        response: Dict[str, Any] = {"quote_id": quote_id}

        # Step 3: Request the shipper's risk index from the Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Assumed policy for screening outage: treat as refused_screening.
            status = "refused_screening"
            try:
                self.quote_store.update_quote(quote_id, status=status)
            except StoreUnavailableError:
                # Behaviour not specified; allow to propagate.
                raise

            response["status"] = status
            # Notify with refusal notice (fire-and-forget); failures ignored.
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass
            return response

        # Step 4: Apply DT-S to the risk index and update stored quote accordingly.
        # Accept band: risk_index <= 41
        if risk_index <= 41:
            status = "quoted"
            # Step 5: Price the quote (DT-P) – only on priced rows.
            price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)
            # Update stored quote with status and price.
            try:
                self.quote_store.update_quote(quote_id, status=status, price=price)
            except StoreUnavailableError:
                # Behaviour for update failure is unspecified; propagate.
                raise

            response["status"] = status
            response["price"] = price

            # Step 6: Notify shipper – quote document, fire-and-forget.
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                # Delivery failure must not change outcome or response.
                pass

            return response

        # Review band: 42 <= risk_index <= 66
        if 42 <= risk_index <= 66:
            status = "review_hold"
            try:
                self.quote_store.update_quote(quote_id, status=status)
            except StoreUnavailableError:
                # Behaviour for update failure is unspecified; propagate.
                raise

            response["status"] = status
            # No price, no notification on this path.
            return response

        # Refuse band: risk_index >= 67
        status = "refused_screening"
        try:
            self.quote_store.update_quote(quote_id, status=status)
        except StoreUnavailableError:
            # Behaviour for update failure is unspecified; propagate.
            raise

        response["status"] = status
        # Notify with refusal notice, fire-and-forget.
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            # Delivery failure never changes outcome or response.
            pass

        return response


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point expected by the harness.

    Constructs default collaborators. In production, these would be wired to
    real implementations; in tests, the classes and methods can be monkey-
    patched or stubbed by name.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
