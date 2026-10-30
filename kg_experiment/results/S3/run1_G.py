from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the QuoteStore cannot persist or update a quote."""


class ScreeningUnavailableError(Exception):
    """Raised when the ScreeningService cannot provide a risk index."""


class QuoteStore:
    """Persistence boundary for quotes.

    Methods are expected to raise StoreUnavailableError on storage failures.
    The concrete implementation is provided elsewhere and may be stubbed in tests.
    """

    def store_draft(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Store a new draft quote and return a representation including quote_id.

        May raise StoreUnavailableError.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, **fields: Any) -> Dict[str, Any]:
        """Update an existing quote and return the updated representation.

        May raise StoreUnavailableError.
        """

        raise NotImplementedError


class TariffEngine:
    """Pricing boundary implementing DT-P.

    The concrete implementation is provided elsewhere and may be stubbed in tests.
    """

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Return a price computed according to P1–P4.

        This module does not reapply pricing logic; it trusts this result.
        """

        raise NotImplementedError


class ScreeningService:
    """Screening boundary used to obtain a shipper risk index."""

    def screen(self, shipper_id: str) -> Dict[str, Any]:
        """Return a screening result including a numeric risk_index.

        May raise ScreeningUnavailableError when screening is unavailable.
        """

        raise NotImplementedError


class NotificationService:
    """Notification boundary for quote documents and refusal notices.

    Notification is fire-and-forget: failures must not affect stored state
    or the API response. Callers must swallow any exceptions from these
    methods.
    """

    def send_quote_document(self, quote: Dict[str, Any]) -> None:
        raise NotImplementedError

    def send_refusal_notice(self, quote: Dict[str, Any]) -> None:
        raise NotImplementedError


# Validation constants (approved ranges)
WEIGHT_MIN = 3.0  # [A:dt:weight_kg|min@v1]
WEIGHT_MAX = 19400.0  # [A:dt:weight_kg|max@v1]
DISTANCE_MIN = 25.0  # [A:dt:distance_km|min@v1]
DISTANCE_MAX = 7150.0  # [A:dt:distance_km|max@v1]
DECLARED_VALUE_MIN = 50.0  # [A:dt:declared_value|min@v1]
DECLARED_VALUE_MAX = 83000.0  # [A:dt:declared_value|max@v1]


# Screening decision thresholds (ASSUMPTIONS based on proposed knowledge)
# ASSUMPTION A:seq:S-accept|max@v1
ACCEPT_MAX: float = 41.0

# ASSUMPTION A:seq:S-review|min@v1 and A:seq:S-review|max@v1
REVIEW_MIN: float = 42.0
REVIEW_MAX: float = 66.0

# ASSUMPTION A:seq:S-refuse|min@v1
REFUSE_MIN: float = 67.0


STATUS_QUOTED = "quoted"  # [A:dt:S-accept|status@v1]
STATUS_REVIEW_HOLD = "review_hold"  # [A:dt:S-review|status@v1]
STATUS_REFUSED_SCREENING = "refused_screening"  # [A:dt:S-refuse|status@v1]
STATUS_HELD_UNSCREENED = "held_unscreened"  # [A:dt:QuoteAPI|on_screening_outage@v1]
STATUS_REJECTED_INVALID = "rejected: invalid_request"  # [A:dt:invalid_request|behaviour@v1]
STATUS_ERROR_STORE_UNAVAILABLE = "error: store_unavailable"  # [A:spec:QuoteAPI|on_store_failure@v1]


@dataclass
class QuoteAPI:
    """Implements the CargoQuote instant freight quotation flow."""

    store: QuoteStore
    tariff: TariffEngine
    screening: ScreeningService
    notification: NotificationService

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:  # noqa: D401
        """Handle a CargoQuote request according to the governed specification."""

        # 1. validate [A:spec:flow|order@v1]
        if not self._is_valid_request(request):
            # [A:dt:invalid_request|behaviour@v1]
            return {"status": STATUS_REJECTED_INVALID}

        shipper_id = str(request.get("shipper_id"))
        weight_kg = float(request.get("weight_kg"))
        distance_km = float(request.get("distance_km"))

        # 2. store (draft) [A:spec:flow|order@v1]
        try:
            stored = self.store.store_draft({
                "shipper_id": shipper_id,
                "weight_kg": weight_kg,
                "distance_km": distance_km,
                "declared_value": float(request.get("declared_value")),
                "status": "draft",
            })
        except StoreUnavailableError:
            # [A:spec:QuoteAPI|on_store_failure@v1]
            return {"status": STATUS_ERROR_STORE_UNAVAILABLE}

        quote_id = self._extract_quote_id(stored)

        # 3. screen [A:spec:flow|order@v1]
        try:
            screening_result = self.screening.screen(shipper_id)
            risk_index = float(screening_result.get("risk_index"))
            screening_available = True
        except ScreeningUnavailableError:
            # Screening outage path [A:spec:QuoteAPI|on_screening_outage@v1]
            screening_available = False
            risk_index = None

        # Screening outage branch: price, hold_unscreened, no notify.
        if not screening_available:
            price = self.tariff.price(weight_kg, distance_km)
            try:
                updated = self.store.update_quote(quote_id, status=STATUS_HELD_UNSCREENED, price=price)
            except StoreUnavailableError:
                # Specification only defines store failure behaviour for initial store;
                # on update failure we still return held_unscreened with price and hold.
                updated = stored
                updated["status"] = STATUS_HELD_UNSCREENED
                updated["price"] = price

            response: Dict[str, Any] = {
                "status": STATUS_HELD_UNSCREENED,
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }
            return response

        # 4. decide [A:spec:flow|order@v1]
        assert risk_index is not None
        if risk_index <= ACCEPT_MAX:
            decision = "accept"
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            decision = "review"
        elif risk_index >= REFUSE_MIN:
            decision = "refuse"
        else:
            # Risk index landed in a gap; conservatively hold for review.
            decision = "review"

        # 5–6. price, notify, and update store according to decision
        if decision == "accept":
            # price [A:dt:S-accept|priced@v1]
            price = self.tariff.price(weight_kg, distance_km)
            try:
                updated = self.store.update_quote(quote_id, status=STATUS_QUOTED, price=price)
            except StoreUnavailableError:
                # As with screening-outage update failure, leave stored state unspecified
                # but honour the accept decision in the response.
                updated = stored
                updated["status"] = STATUS_QUOTED
                updated["price"] = price

            # notify (fire-and-forget) [A:dt:S-accept|notified@v1, A:dt:QuoteAPI|on_notification_failure@v1]
            try:
                self.notification.send_quote_document(updated)
            except Exception:
                pass

            response = {
                "status": STATUS_QUOTED,
                "quote_id": quote_id,
                "price": price,
            }
            return response

        if decision == "review":
            # No pricing, no notification [A:dt:S-review|priced@v1, A:dt:S-review|notified@v1]
            try:
                self.store.update_quote(quote_id, status=STATUS_REVIEW_HOLD)
            except StoreUnavailableError:
                # On update failure we still return review_hold to the caller.
                pass

            response = {
                "status": STATUS_REVIEW_HOLD,
                "quote_id": quote_id,
            }
            return response

        # decision == "refuse"
        # No pricing, refusal is notified, status refused_screening.
        try:
            updated = self.store.update_quote(quote_id, status=STATUS_REFUSED_SCREENING)
        except StoreUnavailableError:
            updated = stored
            updated["status"] = STATUS_REFUSED_SCREENING

        # notify refusal (fire-and-forget) [A:dt:S-refuse|notified#1@v1, A:dt:QuoteAPI|on_notification_failure@v1]
        try:
            self.notification.send_refusal_notice(updated)
        except Exception:
            pass

        response = {
            "status": STATUS_REFUSED_SCREENING,
            "quote_id": quote_id,
        }
        return response

    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Validate request fields against the approved ranges."""

        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or not shipper_id:
            return False

        try:
            weight = float(request.get("weight_kg"))
            distance = float(request.get("distance_km"))
            declared_value = float(request.get("declared_value"))
        except (TypeError, ValueError):
            return False

        if not (WEIGHT_MIN <= weight <= WEIGHT_MAX):
            return False
        if not (DISTANCE_MIN <= distance <= DISTANCE_MAX):
            return False
        if not (DECLARED_VALUE_MIN <= declared_value <= DECLARED_VALUE_MAX):
            return False

        return True

    def _extract_quote_id(self, stored: Dict[str, Any]) -> str:
        """Extract quote_id from the stored quote representation.

        This assumes the presence of a 'quote_id' field as per the API
        contract for responses whenever a draft was stored.
        """

        quote_id = stored.get("quote_id")
        if not isinstance(quote_id, str) or not quote_id:
            raise ValueError("Stored quote did not provide a valid quote_id")
        return quote_id


# Module-level handle function expected by the harness.

def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    store = QuoteStore()
    tariff = TariffEngine()
    screening = ScreeningService()
    notification = NotificationService()
    api = QuoteAPI(store=store, tariff=tariff, screening=screening, notification=notification)
    return api.handle(request)
