from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the QuoteStore is unavailable or cannot persist data."""


class ScreeningUnavailableError(Exception):
    """Raised when the ScreeningService cannot perform screening (outage)."""


@dataclass
class QuoteStore:
    """Collaborator responsible for persisting quotes.

    The concrete implementation is provided by the environment/test harness.
    """

    def store_draft(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Store a draft quote.

        On success, returns a mapping that includes at least a 'quote_id' key.
        On storage failure, must raise StoreUnavailableError.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, **fields: Any) -> None:
        """Update fields of an existing quote.

        On storage failure, must raise StoreUnavailableError.
        """

        raise NotImplementedError


@dataclass
class TariffEngine:
    """Collaborator implementing the pricing rules DT-P."""

    # Pricing constants from DT-P
    BASE_WEIGHT_FACTOR: float = 0.87  # [A:dt:P1|formula@v1]
    BASE_DISTANCE_FACTOR: float = 1.13  # [A:dt:P1|formula@v1]
    HEAVY_SURCHARGE_THRESHOLD: float = 1244.0  # [A:dt:P2|threshold@v1]
    HEAVY_SURCHARGE_AMOUNT: float = 316.00  # [A:dt:P2|surcharge@v1]
    LONG_HAUL_THRESHOLD: float = 4912.0  # [A:dt:P3|threshold@v1]
    LONG_HAUL_FACTOR: float = 1.19  # [A:dt:P3|factor@v1]
    ROUNDING_PLACES: int = 2  # [A:dt:P4|rounding@v1]

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the freight price according to DT-P."""

        # Base price [A:dt:P1|formula@v1]
        result = (
            self.BASE_WEIGHT_FACTOR * weight_kg
            + self.BASE_DISTANCE_FACTOR * distance_km
        )

        # Heavy surcharge [A:dt:P2|threshold@v1] [A:dt:P2|surcharge@v1]
        if weight_kg > self.HEAVY_SURCHARGE_THRESHOLD:
            result += self.HEAVY_SURCHARGE_AMOUNT

        # Long-haul multiplier applied after P2 [A:dt:P3|threshold@v1] [A:dt:P3|factor@v1] [A:dt:P3|order@v1]
        if distance_km >= self.LONG_HAUL_THRESHOLD:
            result *= self.LONG_HAUL_FACTOR

        # Rounding [A:dt:P4|rounding@v1]
        price = round(result, self.ROUNDING_PLACES)
        return price


@dataclass
class ScreeningService:
    """Collaborator responsible for computing shipper risk index."""

    def screen(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Screen the shipper and return at least {'risk_index': number}.

        On outage/unavailability, must raise ScreeningUnavailableError.
        """

        raise NotImplementedError


@dataclass
class NotificationService:
    """Collaborator responsible for sending notifications.

    Notifications are fire-and-forget: failures do not affect stored state or
    the API response. [A:dt:QuoteAPI|on_notification_failure@v1]
    """

    def send_quote_document(self, quote: Dict[str, Any]) -> None:
        """Send the quote document for an accepted quote (DT-S accept row)."""

        raise NotImplementedError

    def send_refusal_notice(self, quote: Dict[str, Any]) -> None:
        """Send a refusal notice for a refused quote (DT-S refuse row)."""

        raise NotImplementedError


class QuoteAPI:
    """Implements the CargoQuote instant freight quotation flow."""

    # Validation bounds
    WEIGHT_MIN: float = 3.0  # [A:dt:weight_kg|min@v1]
    WEIGHT_MAX: float = 19400.0  # [A:dt:weight_kg|max@v1]
    DISTANCE_MIN: float = 25.0  # [A:dt:distance_km|min@v1]
    DISTANCE_MAX: float = 7150.0  # [A:dt:distance_km|max@v1]
    DECLARED_VALUE_MIN: float = 50.0  # [A:dt:declared_value|min@v1]
    DECLARED_VALUE_MAX: float = 83000.0  # [A:dt:declared_value|max@v1]

    # Risk band thresholds – ASSUMPTIONS based on proposed/ambiguous knowledge
    # ASSUMPTION A:seq:S-accept|max@v1, A:dt:S-accept|max@v1
    ACCEPT_MAX: float = 41.0
    # ASSUMPTION A:seq:S-review|min@v1, A:dt:S-review|min@v1
    REVIEW_MIN: float = 42.0
    # ASSUMPTION A:seq:S-review|max@v1, A:dt:S-review|max@v1
    REVIEW_MAX: float = 66.0
    # ASSUMPTION A:seq:S-refuse|min@v1, A:dt:S-refuse|min@v1
    REFUSE_MIN: float = 67.0

    STATUS_QUOTED: str = "quoted"  # [A:dt:S-accept|status@v1]
    STATUS_REVIEW_HOLD: str = "review_hold"  # [A:dt:S-review|status@v1]
    STATUS_REFUSED_SCREENING: str = "refused_screening"  # [A:dt:S-refuse|status@v1]
    STATUS_HELD_UNSCREENED: str = "held_unscreened"  # [A:dt:QuoteAPI|on_screening_outage@v1]
    STATUS_REJECTED_INVALID: str = "rejected: invalid_request"  # [A:dt:invalid_request|behaviour@v1]
    STATUS_ERROR_STORE_UNAVAILABLE: str = "error: store_unavailable"  # [A:spec:QuoteAPI|on_store_failure@v1]

    def __init__(self) -> None:
        self.store = QuoteStore()
        self.tariff = TariffEngine()
        self.screening = ScreeningService()
        self.notification = NotificationService()

    # Core entry point for tests
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a quote request according to the governed specification.

        request: dict with keys shipper_id, weight_kg, distance_km, declared_value.
        Returns a dict with at least a 'status' key, and optionally 'quote_id',
        'price', and 'hold' as per the policy.
        """

        # 1. validate [A:spec:flow|order@v1]
        if not self._is_valid_request(request):
            # Invalid request behaviour [A:dt:invalid_request|behaviour@v1]
            return {"status": self.STATUS_REJECTED_INVALID}

        # Extract validated fields
        shipper_id = request["shipper_id"]
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # Prepare draft payload for storage
        draft_payload: Dict[str, Any] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
        }

        # 2. store draft [A:spec:flow|order@v1]
        try:
            stored = self.store.store_draft(draft_payload)
        except StoreUnavailableError:
            # On storage failure nothing else runs [A:spec:QuoteAPI|on_store_failure@v1]
            return {"status": self.STATUS_ERROR_STORE_UNAVAILABLE}

        quote_id = stored.get("quote_id") if isinstance(stored, dict) else None

        # 3. screen [A:spec:flow|order@v1]
        try:
            screening_result = self.screening.screen(request)
            risk_index = float(screening_result.get("risk_index"))
        except ScreeningUnavailableError:
            # Screening outage path [A:spec:QuoteAPI|on_screening_outage@v1]
            price = self.tariff.price(weight_kg, distance_km)

            # Update stored quote to held_unscreened; spec does not define store
            # failure here, so we let StoreUnavailableError propagate.
            self.store.update_quote(
                quote_id,
                status=self.STATUS_HELD_UNSCREENED,
                price=price,
                hold=True,
            )

            response: Dict[str, Any] = {
                "status": self.STATUS_HELD_UNSCREENED,
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }
            return response

        # 4. decide based on risk_index (DT-S)
        # Pricing, notification, and status mapping are determined by which
        # band risk_index falls into.
        if risk_index <= self.ACCEPT_MAX:
            # Accept branch: quote issued [A:dt:S-accept|priced@v1]
            price = self.tariff.price(weight_kg, distance_km)

            # Update stored quote to quoted [A:dt:S-accept|status@v1]
            self.store.update_quote(
                quote_id,
                status=self.STATUS_QUOTED,
                price=price,
            )

            # Notify (fire-and-forget) [A:dt:S-accept|notified@v1] [A:dt:QuoteAPI|on_notification_failure@v1]
            try:
                self.notification.send_quote_document(
                    {
                        "quote_id": quote_id,
                        "status": self.STATUS_QUOTED,
                        "price": price,
                        "shipper_id": shipper_id,
                    }
                )
            except Exception:
                # Fire-and-forget: never affect stored quote or response
                # [A:dt:QuoteAPI|on_notification_failure@v1]
                pass

            response = {
                "status": self.STATUS_QUOTED,
                "quote_id": quote_id,
                "price": price,
            }
            return response

        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review branch: held for manual review, no pricing, no notification
            # [A:dt:S-review|priced@v1] [A:dt:S-review|notified@v1]
            self.store.update_quote(
                quote_id,
                status=self.STATUS_REVIEW_HOLD,
            )

            response = {
                "status": self.STATUS_REVIEW_HOLD,
                "quote_id": quote_id,
            }
            return response

        if risk_index >= self.REFUSE_MIN:
            # Refuse branch: refused, no pricing, refusal notice sent
            # [A:dt:S-refuse|priced@v1] [A:dt:S-refuse|status@v1]
            self.store.update_quote(
                quote_id,
                status=self.STATUS_REFUSED_SCREENING,
            )

            # Notify refusal (fire-and-forget) [A:dt:S-refuse|notified#1@v1]
            try:
                self.notification.send_refusal_notice(
                    {
                        "quote_id": quote_id,
                        "status": self.STATUS_REFUSED_SCREENING,
                        "shipper_id": shipper_id,
                    }
                )
            except Exception:
                # Fire-and-forget: ignore failures [A:dt:QuoteAPI|on_notification_failure@v1]
                pass

            response = {
                "status": self.STATUS_REFUSED_SCREENING,
                "quote_id": quote_id,
            }
            return response

        # If risk_index falls into a gap between bands due to threshold
        # assumptions, we conservatively treat it as review_hold so that it is
        # neither priced nor automatically refused. This behaviour is not
        # specified in the repository and is thus intentionally conservative.
        # ASSUMPTION related to ambiguous bands A:dt:S-accept|max@v1, A:dt:S-review|min@v1, A:dt:S-review|max@v1, A:dt:S-refuse|min@v1
        self.store.update_quote(
            quote_id,
            status=self.STATUS_REVIEW_HOLD,
        )
        response = {
            "status": self.STATUS_REVIEW_HOLD,
            "quote_id": quote_id,
        }
        return response

    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Validate request fields against the approved constraints."""

        # shipper_id present and non-empty [A:dt:shipper_id|present@v1]
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or not shipper_id.strip():
            return False

        # Numeric ranges for weight, distance, declared_value
        try:
            weight_kg = float(request.get("weight_kg"))
            distance_km = float(request.get("distance_km"))
            declared_value = float(request.get("declared_value"))
        except (TypeError, ValueError):
            return False

        if not (self.WEIGHT_MIN <= weight_kg <= self.WEIGHT_MAX):
            return False
        if not (self.DISTANCE_MIN <= distance_km <= self.DISTANCE_MAX):
            return False
        if not (self.DECLARED_VALUE_MIN <= declared_value <= self.DECLARED_VALUE_MAX):
            return False

        return True


# Module-level handle function expected by the harness
_api_instance: Optional[QuoteAPI] = None


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    global _api_instance
    if _api_instance is None:
        _api_instance = QuoteAPI()
    return _api_instance.handle(request)
