from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the QuoteStore is unavailable."""


class ScreeningUnavailableError(Exception):
    """Raised when the ScreeningService is unavailable."""


class QuoteStore:
    def store_draft(self, quote_data: Dict[str, Any]) -> str:
        """Store a new draft quote and return its quote_id.

        May raise StoreUnavailableError on storage failure.
        """
        raise NotImplementedError

    def update_quote(self, quote_id: str, updates: Dict[str, Any]) -> None:
        """Update an existing quote.

        May raise StoreUnavailableError on storage failure.
        """
        raise NotImplementedError


class TariffEngine:
    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the freight price according to DT-P (P1-P4)."""
        # P1: base = 0.87 * weight_kg + 1.13 * distance_km  [A:dt:P1|formula@v1]
        base = 0.87 * weight_kg + 1.13 * distance_km

        # P2: heavy surcharge if weight_kg > 1244, add 316.00  [A:dt:P2|threshold@v1][A:dt:P2|surcharge@v1]
        if weight_kg > 1244:
            base += 316.00

        # P3: long-haul multiplier if distance_km >= 4912, multiply by 1.19, applied after P2
        # [A:dt:P3|threshold@v1][A:dt:P3|factor@v1][A:dt:P3|order@v1]
        if distance_km >= 4912:
            base *= 1.19

        # P4: price = round(result, 2)  [A:dt:P4|rounding@v1]
        price = round(base, 2)
        return price


class ScreeningService:
    def screen(self, shipper_id: str) -> int:
        """Return the risk_index for the given shipper_id.

        May raise ScreeningUnavailableError when screening is unavailable.
        """
        raise NotImplementedError


class NotificationService:
    def send_quote_document(self, quote_id: str) -> None:
        """Send the quote document notification (fire-and-forget)."""
        raise NotImplementedError

    def send_refusal_notice(self, quote_id: str) -> None:
        """Send the refusal notice notification (fire-and-forget)."""
        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # Screening thresholds from DT-S  [A:dt:S-accept|max@v1][A:dt:S-review|min@v1][A:dt:S-review|max@v1][A:dt:S-refuse|min@v1]
    ACCEPT_MAX: int = 41
    REVIEW_MIN: int = 42
    REVIEW_MAX: int = 66
    REFUSE_MIN: int = 67

    # Validation bounds  [A:dt:weight_kg|min@v1][A:dt:weight_kg|max@v1][A:dt:distance_km|min@v1][A:dt:distance_km|max@v1][A:dt:declared_value|min@v1][A:dt:declared_value|max@v1]
    MIN_WEIGHT: float = 3.0
    MAX_WEIGHT: float = 19400.0
    MIN_DISTANCE: float = 25.0
    MAX_DISTANCE: float = 7150.0
    MIN_DECLARED_VALUE: float = 50.0
    MAX_DECLARED_VALUE: float = 83000.0

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an instant freight quotation request.

        request keys: shipper_id, weight_kg, distance_km, declared_value.
        Returns a dict with at least a 'status' key, and conditionally
        'quote_id', 'price', and 'hold' according to the governed spec.
        """
        # Step 1: validate  [A:spec:flow|order@v1]
        validation_error = self._validate_request(request)
        if validation_error is not None:
            # Invalid request behaviour  [A:dt:invalid_request|behaviour@v1]
            return {
                "status": "rejected: invalid_request",
            }

        shipper_id = request["shipper_id"]
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # Step 2: store draft  [A:spec:flow|order@v1]
        try:
            quote_id = self.quote_store.store_draft(
                {
                    "shipper_id": shipper_id,
                    "weight_kg": weight_kg,
                    "distance_km": distance_km,
                    "declared_value": declared_value,
                    "status": "draft",
                }
            )
        except StoreUnavailableError:
            # On storage failure: status error: store_unavailable; no screening, pricing, notification
            # [A:spec:QuoteAPI|on_store_failure@v1]
            return {
                "status": "error: store_unavailable",
            }

        # Step 3: screen  [A:spec:flow|order@v1]
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_outage = False
        except ScreeningUnavailableError:
            risk_index = None
            screening_outage = True

        # If screening is unavailable, follow dedicated outage path
        if screening_outage:
            # On screening outage: price anyway, store as held_unscreened, do not notify, respond with price and hold:true
            # [A:spec:QuoteAPI|on_screening_outage@v1]
            price = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {
                        "status": "held_unscreened",
                        "price": price,
                    },
                )
            except StoreUnavailableError:
                # Storage failure after initial draft is not specified; we propagate as store_unavailable consistent with initial behaviour.
                # This relies on the same outcome as initial storage failure.  [A:spec:QuoteAPI|on_store_failure@v1]
                return {
                    "status": "error: store_unavailable",
                }

            response: Dict[str, Any] = {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }
            return response

        # Step 4: decide based on risk_index  [A:spec:flow|order@v1]
        assert risk_index is not None
        if risk_index <= self.ACCEPT_MAX:
            decision = "accept"
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            decision = "review"
        else:  # risk_index >= REFUSE_MIN
            decision = "refuse"

        # Step 5: price when required (only accept row is priced)  [A:dt:S-accept|priced@v1][A:dt:S-review|priced@v1][A:dt:S-refuse|priced@v1]
        price: Optional[float] = None
        if decision == "accept":
            price = self.tariff_engine.price(weight_kg, distance_km)

        # Step 6: update stored quote status (and price if present) and notify when required
        # Accept path
        if decision == "accept":
            status = "quoted"  # [A:dt:S-accept|status@v1]
            updates: Dict[str, Any] = {"status": status}
            if price is not None:
                updates["price"] = price
            try:
                self.quote_store.update_quote(quote_id, updates)
            except StoreUnavailableError:
                # See comment above: use same failure semantics as initial store failure.  [A:spec:QuoteAPI|on_store_failure@v1]
                return {
                    "status": "error: store_unavailable",
                }

            # Notification: quote document (fire-and-forget). Failures do not affect response. [A:dt:S-accept|notified@v1][A:dt:QuoteAPI|on_notification_failure@v1]
            try:
                self.notification_service.send_quote_document(quote_id)
            except Exception:
                # Fire-and-forget; ignore all errors.  [A:dt:QuoteAPI|on_notification_failure@v1]
                pass

            response = {
                "status": status,
                "quote_id": quote_id,
            }
            if price is not None:
                response["price"] = price
            return response

        # Review path
        if decision == "review":
            status = "review_hold"  # [A:dt:S-review|status@v1]
            try:
                self.quote_store.update_quote(quote_id, {"status": status})
            except StoreUnavailableError:
                return {
                    "status": "error: store_unavailable",
                }

            # No pricing, no notification  [A:dt:S-review|priced@v1][A:dt:S-review|notified@v1]
            response = {
                "status": status,
                "quote_id": quote_id,
            }
            return response

        # Refuse path
        status = "refused_screening"  # [A:dt:S-refuse|status@v1]
        try:
            self.quote_store.update_quote(quote_id, {"status": status})
        except StoreUnavailableError:
            return {
                "status": "error: store_unavailable",
            }

        # Notification: refusal notice (fire-and-forget).  [A:dt:S-refuse|notified@v1][A:dt:QuoteAPI|on_notification_failure@v1]
        try:
            self.notification_service.send_refusal_notice(quote_id)
        except Exception:
            pass

        response = {
            "status": status,
            "quote_id": quote_id,
        }
        return response

    def _validate_request(self, request: Dict[str, Any]) -> Optional[str]:
        """Validate request fields according to the contract.

        Returns None if valid, or a string describing the first error found.
        """
        # shipper_id present and non-empty  [A:dt:shipper_id|present@v1]
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or len(shipper_id) == 0:
            return "invalid shipper_id"

        # weight_kg bounds  [A:dt:weight_kg|min@v1][A:dt:weight_kg|max@v1]
        if "weight_kg" not in request:
            return "missing weight_kg"
        try:
            weight_kg = float(request["weight_kg"])
        except (TypeError, ValueError):
            return "invalid weight_kg"
        if not (self.MIN_WEIGHT <= weight_kg <= self.MAX_WEIGHT):
            return "out_of_range weight_kg"

        # distance_km bounds  [A:dt:distance_km|min@v1][A:dt:distance_km|max@v1]
        if "distance_km" not in request:
            return "missing distance_km"
        try:
            distance_km = float(request["distance_km"])
        except (TypeError, ValueError):
            return "invalid distance_km"
        if not (self.MIN_DISTANCE <= distance_km <= self.MAX_DISTANCE):
            return "out_of_range distance_km"

        # declared_value bounds  [A:dt:declared_value|min@v1][A:dt:declared_value|max@v1]
        if "declared_value" not in request:
            return "missing declared_value"
        try:
            declared_value = float(request["declared_value"])
        except (TypeError, ValueError):
            return "invalid declared_value"
        if not (self.MIN_DECLARED_VALUE <= declared_value <= self.MAX_DECLARED_VALUE):
            return "out_of_range declared_value"

        return None


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level handle function that uses the default collaborator implementations.

    In production, QuoteStore, TariffEngine, ScreeningService, and
    NotificationService should be subclassed or monkey-patched by the
    surrounding application or test harness.
    """
    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
