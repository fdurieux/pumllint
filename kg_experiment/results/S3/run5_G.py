from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the QuoteStore is unavailable for storage operations."""


class ScreeningUnavailableError(Exception):
    """Raised when the ScreeningService is unavailable or times out."""


# Risk band constants are intentionally left symbolic.
# They must be configured by governance to resolve the ambiguous
# S-accept|max, S-review|min/max, S-refuse|min semantics.
# ASSUMPTION A:dt:S-accept|max@v1, A:dt:S-review|min@v1, A:dt:S-refuse|min@v1
ACCEPT_MAX: float = 40.0  # placeholder, to be decided by governed config
REVIEW_MIN: float = 40.0  # placeholder, inclusive lower bound of review band
REVIEW_MAX: float = 66.0  # placeholder, inclusive upper bound of review band
REFUSE_MIN: float = 66.0  # placeholder, inclusive lower bound of refuse band


# Pricing constants from DT-P
HEAVY_SURCHARGE_THRESHOLD: float = 1244.0  # A:dt:P2|threshold@v1
HEAVY_SURCHARGE_AMOUNT: float = 316.00     # A:dt:P2|surcharge@v1
LONG_HAUL_THRESHOLD: float = 4912.0        # A:dt:P3|threshold@v1
LONG_HAUL_FACTOR: float = 1.19             # A:dt:P3|factor@v1


@dataclass
class QuoteDraft:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: str
    price: Optional[float] = None
    hold: Optional[bool] = None


class QuoteStore:
    """Collaborator responsible for persisting quotes."""

    def store_draft(self, draft: QuoteDraft) -> QuoteDraft:
        """Persist a new draft quote.

        May raise StoreUnavailableError on storage failure.
        """

        # Default stub: echo back with same quote_id; real impl is external.
        return draft

    def update_quote(self, quote: QuoteDraft) -> QuoteDraft:
        """Update an existing quote's status/fields.

        May raise StoreUnavailableError on storage failure.
        """

        # Default stub: echo back; real impl is external.
        return quote


class TariffEngine:
    """Collaborator responsible for pricing logic (DT-P)."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # DT-P P1: base formula
        base = 0.87 * weight_kg + 1.13 * distance_km  # A:dt:P1|formula@v1

        # DT-P P2: heavy surcharge
        if weight_kg > HEAVY_SURCHARGE_THRESHOLD:  # A:dt:P2|threshold@v1
            base += HEAVY_SURCHARGE_AMOUNT        # A:dt:P2|surcharge@v1

        # DT-P P3: long-haul multiplier applied after P2
        if distance_km >= LONG_HAUL_THRESHOLD:    # A:dt:P3|threshold@v1, A:dt:P3|order@v1
            base *= LONG_HAUL_FACTOR             # A:dt:P3|factor@v1

        # DT-P P4: rounding
        price = round(base, 2)                   # A:dt:P4|rounding@v1
        return price


class ScreeningService:
    """Collaborator responsible for returning a risk index for a shipper."""

    def screen(self, shipper_id: str, declared_value: float) -> float:
        """Return a numeric risk index for the given shipper.

        May raise ScreeningUnavailableError on outage.
        Concrete scale and calibration are governed externally.
        """

        # Default stub: always low risk; real implementation is external.
        return 0.0


class NotificationService:
    """Collaborator responsible for sending notifications (fire-and-forget)."""

    def send_quote_document(self, quote: QuoteDraft) -> None:
        """Send a quote document for an accepted quote (fire-and-forget)."""
        # Failures must not affect stored quote or response
        # (A:dt:QuoteAPI|on_notification_failure@v1).
        return None

    def send_refusal_notice(self, quote: QuoteDraft) -> None:
        """Send a refusal notice for a refused quote (fire-and-forget)."""
        # Failures must not affect stored quote or response
        # (A:dt:QuoteAPI|on_notification_failure@v1).
        return None


class QuoteAPI:
    """Implements the CargoQuote instant freight quotation flow."""

    def __init__(self) -> None:
        self.store = QuoteStore()
        self.tariff = TariffEngine()
        self.screening = ScreeningService()
        self.notifier = NotificationService()

    # --- Validation helpers -------------------------------------------------

    def _is_valid_request(self, req: Dict[str, Any]) -> bool:
        # shipper_id present and non-empty
        shipper_id = req.get("shipper_id")
        if not isinstance(shipper_id, str) or len(shipper_id) == 0:
            return False  # A:dt:shipper_id|present@v1

        # Numeric bounds for weight_kg, distance_km, declared_value
        try:
            weight = float(req.get("weight_kg"))
            distance = float(req.get("distance_km"))
            declared = float(req.get("declared_value"))
        except (TypeError, ValueError):
            return False

        if not (3 <= weight <= 19400):  # A:dt:weight_kg|min@v1, A:dt:weight_kg|max@v1
            return False
        if not (25 <= distance <= 7150):  # A:dt:distance_km|min@v1, A:dt:distance_km|max@v1
            return False
        if not (50 <= declared <= 83000):  # A:dt:declared_value|min@v1, A:dt:declared_value|max@v1
            return False

        return True

    # --- Main flow ----------------------------------------------------------

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # Step 1: validate (A:spec:flow|order@v1)
        if not self._is_valid_request(request):
            # A:dt:invalid_request|behaviour@v1
            return {
                "status": "rejected: invalid_request",
            }

        shipper_id = str(request["shipper_id"])
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # Step 2: store draft (status=draft)
        draft = QuoteDraft(
            quote_id=self._generate_quote_id(),
            shipper_id=shipper_id,
            weight_kg=weight_kg,
            distance_km=distance_km,
            declared_value=declared_value,
            status="draft",
        )

        try:
            stored = self.store.store_draft(draft)
        except StoreUnavailableError:
            # On storage failure nothing else runs
            # A:spec:QuoteAPI|on_store_failure@v1
            return {
                "status": "error: store_unavailable",
            }

        # Step 3: screen
        try:
            risk_index = self.screening.screen(shipper_id, declared_value)
            screening_outage = False
        except ScreeningUnavailableError:
            # Screening outage path handled after pricing as held_unscreened
            # A:spec:QuoteAPI|on_screening_outage@v1
            risk_index = None
            screening_outage = True

        # Step 4: decide & subsequent actions
        if screening_outage:
            # Screening outage branch: price, store as held_unscreened, no notify, hold: true
            price_amount = self.tariff.price(weight_kg, distance_km)

            stored.status = "held_unscreened"  # A:dt:QuoteAPI|on_screening_outage@v1
            stored.price = price_amount
            stored.hold = True

            try:
                updated = self.store.update_quote(stored)
            except StoreUnavailableError:
                # Spec does not explicitly override store-failure semantics here;
                # follow same rule: status=error: store_unavailable
                # A:spec:QuoteAPI|on_store_failure@v1
                return {
                    "status": "error: store_unavailable",
                }

            response = {
                "status": "held_unscreened",
                "quote_id": updated.quote_id,
                "price": price_amount,
                "hold": True,
            }
            return response

        # Normal screening result: use risk_index to branch accept/review/refuse.
        assert risk_index is not None

        if risk_index <= ACCEPT_MAX:
            # Accept path (low risk)
            price_amount = self.tariff.price(weight_kg, distance_km)

            stored.status = "quoted"  # A:dt:S-accept|status@v1
            stored.price = price_amount
            stored.hold = None

            try:
                updated = self.store.update_quote(stored)
            except StoreUnavailableError:
                # Follow general store-failure rule
                # A:spec:QuoteAPI|on_store_failure@v1
                return {
                    "status": "error: store_unavailable",
                }

            # Notify (fire-and-forget)
            try:
                self.notifier.send_quote_document(updated)  # A:dt:S-accept|notified@v1
            except Exception:
                # Fire-and-forget: must not change response or store
                # A:dt:QuoteAPI|on_notification_failure@v1
                pass

            return {
                "status": "quoted",
                "quote_id": updated.quote_id,
                "price": price_amount,
            }

        if REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # Review path (medium risk): no pricing, no notification
            stored.status = "review_hold"  # A:dt:S-review|status@v1
            stored.price = None
            stored.hold = None

            try:
                updated = self.store.update_quote(stored)
            except StoreUnavailableError:
                # Follow general store-failure rule
                # A:spec:QuoteAPI|on_store_failure@v1
                return {
                    "status": "error: store_unavailable",
                }

            return {
                "status": "review_hold",
                "quote_id": updated.quote_id,
            }

        # Else: refuse path (high risk). We treat any remaining risk_index as refused.
        stored.status = "refused_screening"  # A:dt:S-refuse|status@v1
        stored.price = None
        stored.hold = None

        try:
            updated = self.store.update_quote(stored)
        except StoreUnavailableError:
            # Follow general store-failure rule
            # A:spec:QuoteAPI|on_store_failure@v1
            return {
                "status": "error: store_unavailable",
            }

        # Notify refusal (fire-and-forget)
        try:
            self.notifier.send_refusal_notice(updated)  # A:dt:S-refuse|notified@v1
        except Exception:
            # Fire-and-forget: must not change response or store
            # A:dt:QuoteAPI|on_notification_failure@v1
            pass

        return {
            "status": "refused_screening",
            "quote_id": updated.quote_id,
        }

    def _generate_quote_id(self) -> str:
        """Generate a quote id. In production this would be more robust.

        For this implementation we keep it simple and deterministic enough
        that tests can override QuoteStore.store_draft if they need
        specific IDs.
        """

        # In absence of repository guidance, use a simple monotonic counter
        # scoped to the process. This is internal and not normatively
        # specified by the contract.
        if not hasattr(self, "_id_seq"):
            self._id_seq = 0
        self._id_seq += 1
        return f"Q{self._id_seq}"


_quote_api_instance: Optional[QuoteAPI] = None


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point expected by the harness."""
    global _quote_api_instance
    if _quote_api_instance is None:
        _quote_api_instance = QuoteAPI()
    return _quote_api_instance.handle(request)
