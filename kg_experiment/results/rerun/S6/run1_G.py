from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable."""


class ScreeningUnavailableError(Exception):
    """Raised when the screening service is unavailable."""


class QuoteStore:
    """Abstraction over the quote storage system."""

    def store_draft(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Store a draft quote and return a quote record including quote_id and status.

        May raise StoreUnavailableError when storage fails.
        """
        raise NotImplementedError

    def update_quote(self, quote_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing quote with the given fields and return the updated record.

        May raise StoreUnavailableError when storage fails.
        """
        raise NotImplementedError


class TariffEngine:
    """Pricing engine implementing DT-P (P1-P4).

    Tests may stub this; a simple compliant implementation is provided.
    """

    # Constants derived from approved tariff assertions
    BASE_WEIGHT_COEFF = 0.87  # A:dt:P1|formula@v1
    BASE_DISTANCE_COEFF = 1.13  # A:dt:P1|formula@v1
    HEAVY_SURCHARGE_THRESHOLD = 1244  # A:dt:P2|threshold@v2
    HEAVY_SURCHARGE_AMOUNT = 341.00  # A:dt:P2|surcharge@v2
    LONG_HAUL_THRESHOLD = 4912  # A:dt:P3|threshold@v1
    LONG_HAUL_FACTOR = 1.19  # A:dt:P3|factor@v1

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the price according to DT-P.

        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 341.00 (flat)
        P3: if distance_km >= 4912, multiply running total by 1.19 (after P2)
        P4: price = round(result, 2)
        """
        # P1
        base = (
            self.BASE_WEIGHT_COEFF * float(weight_kg)
            + self.BASE_DISTANCE_COEFF * float(distance_km)
        )

        result = base

        # P2 heavy surcharge
        if float(weight_kg) > self.HEAVY_SURCHARGE_THRESHOLD:
            result += self.HEAVY_SURCHARGE_AMOUNT

        # P3 long-haul multiplier (applied after P2)
        if float(distance_km) >= self.LONG_HAUL_THRESHOLD:
            result *= self.LONG_HAUL_FACTOR

        # P4 rounding
        price = round(result, 2)
        return price


class ScreeningService:
    """Abstraction over the external screening service."""

    def screen(self, shipper_id: str) -> float:
        """Return the risk index for the given shipper.

        Raises ScreeningUnavailableError on outage as per specification.
        """
        raise NotImplementedError


class NotificationService:
    """Abstraction over notification delivery (fire-and-forget)."""

    def send_quote_document(self, quote: Dict[str, Any]) -> None:
        """Send the quote document notification.

        Any delivery failure must not affect stored state or response.
        """
        raise NotImplementedError

    def send_refusal_notice(self, quote: Dict[str, Any]) -> None:
        """Send the refusal notice notification.

        Any delivery failure must not affect stored state or response.
        """
        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # Screening thresholds from DT-S
    ACCEPT_MAX = 41  # A:dt:S-accept|max@v1
    REVIEW_MIN = 42  # A:dt:S-review|min@v1
    REVIEW_MAX = 66  # A:dt:S-review|max@v1
    REFUSE_MIN = 67  # A:dt:S-refuse|min@v1

    # Validation bounds from DT-V
    MIN_WEIGHT = 3  # A:dt:weight_kg|min@v1
    MAX_WEIGHT = 19400  # A:dt:weight_kg|max@v1
    MIN_DISTANCE = 25  # A:dt:distance_km|min@v1
    MAX_DISTANCE = 7150  # A:dt:distance_km|max@v1
    MIN_DECLARED_VALUE = 50  # A:dt:declared_value|min@v1
    MAX_DECLARED_VALUE = 83000  # A:dt:declared_value|max@v1

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a quote request according to the governed specification."""
        # Step 1: validate (DT-V)
        validation_error = self._validate_request(request)
        if validation_error is not None:
            # invalid_request|behaviour: immediate rejection, nothing else runs
            return {
                "status": "rejected: invalid_request",
            }

        # Extract validated fields
        shipper_id = str(request["shipper_id"])
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])
        _ = declared_value  # declared_value is validated but not used in pricing logic yet

        # Step 2: store draft
        try:
            stored = self.quote_store.store_draft(request)
        except StoreUnavailableError:
            # QuoteAPI|on_store_failure: nothing else runs
            return {
                "status": "error: store_unavailable",
            }

        quote_id = stored.get("quote_id")

        # Step 3: screen
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # QuoteAPI|on_screening_outage: price anyway, hold_unscreened, not notified, hold: true
            price = self.tariff_engine.price(weight_kg, distance_km)
            try:
                updated = self.quote_store.update_quote(
                    quote_id,
                    {
                        "status": "held_unscreened",
                        "price": price,
                        "hold": True,
                    },
                )
            except StoreUnavailableError:
                # Spec does not override store failure handling later in flow; be conservative
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

        # Step 4: decide based on risk_index (DT-S)
        if risk_index <= self.ACCEPT_MAX:
            decision = "accept"
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            decision = "review"
        else:  # risk_index >= REFUSE_MIN
            decision = "refuse"

        # Step 5: price depending on decision (DT-S priced column)
        price: Optional[float] = None
        if decision == "accept":
            price = self.tariff_engine.price(weight_kg, distance_km)
        # For review and refuse, pricing must NOT run

        # Prepare storage updates and notifications according to DT-S
        final_status: str
        hold_flag: Optional[bool] = None
        notify_action: Optional[str] = None

        if decision == "accept":
            final_status = "quoted"
            notify_action = "quote_document"
        elif decision == "review":
            final_status = "review_hold"
        else:  # refuse
            final_status = "refused_screening"
            notify_action = "refusal_notice"

        # Step 6: update stored quote status (and price if any)
        update_fields: Dict[str, Any] = {"status": final_status}
        if price is not None:
            update_fields["price"] = price

        try:
            updated = self.quote_store.update_quote(quote_id, update_fields)
        except StoreUnavailableError:
            # No explicit rule for update failure; align with on_store_failure to avoid partial processing
            return {
                "status": "error: store_unavailable",
            }

        # Step 7: notify (fire-and-forget) where applicable
        if notify_action == "quote_document":
            try:
                self.notification_service.send_quote_document(updated)
            except Exception:
                # fire-and-forget: do not alter response or stored state
                pass
        elif notify_action == "refusal_notice":
            try:
                self.notification_service.send_refusal_notice(updated)
            except Exception:
                # fire-and-forget: do not alter response or stored state
                pass

        # Build response according to response field presence rules
        response: Dict[str, Any] = {
            "status": final_status,
        }

        # quote_id whenever a draft was stored (and we didn't fail store)
        if quote_id is not None:
            response["quote_id"] = quote_id

        # price present exactly on priced rows: accept and screening outage case only
        if price is not None:
            response["price"] = price

        # hold: true exactly on held_unscreened (already handled in outage path)
        # In this screening-success branch, held_unscreened never occurs.

        return response


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point required by the harness.

    Instantiates real collaborator placeholders which can be monkey-patched
    or stubbed in tests by class and method name.
    """
    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)


# Internal helpers

def _is_number(value: Any) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _in_range(value: Any, minimum: float, maximum: float) -> bool:
    if not _is_number(value):
        return False
    v = float(value)
    return minimum <= v <= maximum


# Attach validation as methods on QuoteAPI after its definition

def _validate_request(self: QuoteAPI, request: Dict[str, Any]) -> Optional[str]:
    # shipper_id present and non-empty
    shipper_id = request.get("shipper_id")
    if shipper_id is None or str(shipper_id) == "":
        return "missing_or_empty_shipper_id"

    # weight_kg range check
    if not _in_range(request.get("weight_kg"), self.MIN_WEIGHT, self.MAX_WEIGHT):
        return "invalid_weight_kg"

    # distance_km range check
    if not _in_range(request.get("distance_km"), self.MIN_DISTANCE, self.MAX_DISTANCE):
        return "invalid_distance_km"

    # declared_value range check
    if not _in_range(
        request.get("declared_value"), self.MIN_DECLARED_VALUE, self.MAX_DECLARED_VALUE
    ):
        return "invalid_declared_value"

    return None


setattr(QuoteAPI, "_validate_request", _validate_request)
