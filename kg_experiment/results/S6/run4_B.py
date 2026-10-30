from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the Quote Store is unavailable for draft storage or updates."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service is unavailable (screening outage)."""


class QuoteStore:
    """Persistence layer for quotes.

    Methods are expected to raise StoreUnavailableError when the underlying
    storage is unavailable. Concrete implementations are provided elsewhere
    and may be stubbed in tests by class and method name.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        May raise StoreUnavailableError on failure.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote's status and optionally its price.

        May raise StoreUnavailableError on failure.
        """

        raise NotImplementedError


class TariffEngine:
    """Pricing engine implementing DT-P rules."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute price according to DT-P.

        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: heavy surcharge: if weight_kg > 1244, add 341.00 (flat)
        P3: long-haul multiplier: if distance_km >= 4912, multiply running total by 1.19
        P4: price = round(result, 2)
        """

        # P1
        result = 0.87 * weight_kg + 1.13 * distance_km
        # P2
        if weight_kg > 1244:
            result += 341.00
        # P3
        if distance_km >= 4912:
            result *= 1.19
        # P4
        price = round(result, 2)
        return price


class ScreeningService:
    """External screening provider interface."""

    def screen(self, shipper_id: str) -> int:
        """Return an integer risk index for the given shipper.

        May raise ScreeningUnavailableError on outage.
        """

        raise NotImplementedError


class NotificationService:
    """External notification provider interface."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send a quote document to the shipper.

        Any exceptions are treated as delivery failures and must not
        affect the outcome of handle().
        """

        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice to the shipper.

        Any exceptions are treated as delivery failures and must not
        affect the outcome of handle().
        """

        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # Validation bounds from DT-V
    MIN_WEIGHT = 3
    MAX_WEIGHT = 19400
    MIN_DISTANCE = 25
    MAX_DISTANCE = 7150
    MIN_DECLARED_VALUE = 50
    MAX_DECLARED_VALUE = 83000

    # Screening thresholds from DT-S
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def _validate(self, request: Dict[str, Any]) -> bool:
        """Validate the incoming request according to DT-V.

        Returns True iff valid; False otherwise.
        """

        # shipper_id: present and non-empty string
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False

        # Numeric fields: ensure they are numbers and within bounds
        try:
            weight = float(request.get("weight_kg"))
            distance = float(request.get("distance_km"))
            declared_value = float(request.get("declared_value"))
        except (TypeError, ValueError):
            return False

        if not (self.MIN_WEIGHT <= weight <= self.MAX_WEIGHT):
            return False
        if not (self.MIN_DISTANCE <= distance <= self.MAX_DISTANCE):
            return False
        if not (self.MIN_DECLARED_VALUE <= declared_value <= self.MAX_DECLARED_VALUE):
            return False

        return True

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Main orchestration entry point implementing the CargoQuote flow.

        Follows the flow and semantics defined in spec.md and decision_table.md.
        """

        # 1. Validate request per DT-V
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        # At this point, numeric conversions should succeed due to validation
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])  # stored but unused in pricing

        # 2. Store draft quote with status 'draft'
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            # On storage failure, nothing else runs
            return {"status": "error: store_unavailable"}

        # 3. Request risk index from Screening Service
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_outage = False
        except ScreeningUnavailableError:
            screening_outage = True
            risk_index = None  # unused in this branch

        # Handle screening outage path
        if screening_outage:
            # Price anyway per DT-P
            price = self.tariff_engine.price(weight_kg, distance_km)
            # Update stored quote to held_unscreened with price
            self.quote_store.update_quote(quote_id, status="held_unscreened", price=price)
            # No notification; response carries price and hold: true
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4. Apply DT-S to risk_index and handle each branch
        # Accept row: priced, notified, status quoted
        if risk_index <= self.ACCEPT_MAX:
            # 5. Price per DT-P
            price = self.tariff_engine.price(weight_kg, distance_km)
            # Update stored quote
            self.quote_store.update_quote(quote_id, status="quoted", price=price)

            # 6. Notify shipper with quote document (fire-and-forget)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                # Delivery failure must not affect outcome or response
                pass

            # 7. Return response
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }

        # Review row: no price, no notification
        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, status="review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }

        # Refuse row: no price, refusal notice, status refused_screening
        if risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, status="refused_screening")

            # Notify shipper with refusal notice (fire-and-forget)
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                # Delivery failure must not affect outcome or response
                pass

            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }

        # The decision table DT-S is exhaustive over integer risk_index values,
        # but for defensive programming, if none of the above matched, treat as
        # review_hold (safest: no price, no notification).
        self.quote_store.update_quote(quote_id, status="review_hold")
        return {
            "status": "review_hold",
            "quote_id": quote_id,
        }


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point used by the test harness.

    Instantiates concrete collaborator classes; in tests, these classes
    can be monkeypatched/stubbed by name.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
