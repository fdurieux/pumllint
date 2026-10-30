from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the QuoteStore cannot persist data."""
    pass


class ScreeningUnavailableError(Exception):
    """Raised when the ScreeningService is unavailable."""
    pass


class QuoteStore:
    """Persistence for quotes.

    Real implementations are expected to raise StoreUnavailableError on
    storage failures, as per the governed contract.
    """

    def store_draft(self, request: Dict[str, Any]) -> str:
        """Store a new draft quote and return its quote_id.

        May raise StoreUnavailableError to signal storage failure.
        """
        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote's status and, optionally, its price.

        May raise StoreUnavailableError to signal storage failure.
        """
        raise NotImplementedError


class TariffEngine:
    """Pricing engine implementing DT-P (P1–P4)."""

    # Pricing constants from governed knowledge
    BASE_WEIGHT_COEFF = 0.87  # A:dt:P1|formula@v1
    BASE_DISTANCE_COEFF = 1.13  # A:dt:P1|formula@v1
    HEAVY_SURCHARGE_THRESHOLD = 1244  # A:dt:P2|threshold@v2
    HEAVY_SURCHARGE_AMOUNT = 341.00  # A:dt:P2|surcharge@v2
    LONG_HAUL_THRESHOLD = 4912  # A:dt:P3|threshold@v1
    LONG_HAUL_FACTOR = 1.19  # A:dt:P3|factor@v1

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the price according to DT-P.

        Implements:
        - P1 base = 0.87 * weight_kg + 1.13 * distance_km
        - P2 heavy surcharge: if weight_kg > 1244, add 341.00 (flat)
        - P3 long-haul multiplier: if distance_km >= 4912, multiply the
          running total by 1.19, applied after P2
        - P4 rounding: price = round(result, 2)
        """
        # P1: base
        result = (
            self.BASE_WEIGHT_COEFF * weight_kg
            + self.BASE_DISTANCE_COEFF * distance_km
        )

        # P2: heavy surcharge
        if weight_kg > self.HEAVY_SURCHARGE_THRESHOLD:
            result += self.HEAVY_SURCHARGE_AMOUNT

        # P3: long-haul multiplier (applied after P2)
        if distance_km >= self.LONG_HAUL_THRESHOLD:
            result *= self.LONG_HAUL_FACTOR

        # P4: rounding to 2 decimal places
        price = round(result, 2)
        return price


class ScreeningService:
    """Service for obtaining shipper risk index."""

    def screen(self, shipper_id: str) -> int:
        """Return the risk index for the given shipper.

        May raise ScreeningUnavailableError on outage.
        """
        raise NotImplementedError


class NotificationService:
    """Service for sending quote-related notifications.

    Notification is fire-and-forget: failures must not affect stored
    state or API response semantics.
    """

    def send_quote_document(self, quote_id: str) -> None:
        raise NotImplementedError

    def send_refusal_notice(self, quote_id: str) -> None:
        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # Validation bounds from governed knowledge
    MIN_WEIGHT = 3
    MAX_WEIGHT = 19400
    MIN_DISTANCE = 25
    MAX_DISTANCE = 7150
    MIN_DECLARED_VALUE = 50
    MAX_DECLARED_VALUE = 83000

    # Screening thresholds
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a quote request according to the governed contract."""
        # 1. validate
        if not self._is_valid_request(request):
            # invalid_request behaviour: reject immediately; nothing else runs
            # A:dt:invalid_request|behaviour@v1
            return {"status": "rejected: invalid_request"}

        # 2. store draft
        try:
            quote_id = self.quote_store.store_draft(request)
        except StoreUnavailableError:
            # On storage failure: no screening, no pricing, no notification
            # A:dt:QuoteAPI|on_store_failure@v1
            return {"status": "error: store_unavailable"}

        # 3. screen
        try:
            risk_index = self.screening_service.screen(request["shipper_id"])
        except ScreeningUnavailableError:
            # Screening outage path: price anyway, status held_unscreened, not notified
            # A:spec:QuoteAPI|on_screening_outage@v1
            price = self.tariff_engine.price(request["weight_kg"], request["distance_km"])
            try:
                self.quote_store.update_quote(quote_id, "held_unscreened", price=price)
            except StoreUnavailableError:
                # Contract only specifies store failure handling on initial store.
                # Here we conservatively surface store_unavailable as well.
                return {"status": "error: store_unavailable", "quote_id": quote_id}

            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4. decide based on risk_index
        if risk_index <= self.ACCEPT_MAX:
            decision = "accept"
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            decision = "review"
        else:
            # risk_index >= REFUSE_MIN
            decision = "refuse"

        # 5. price (only for priced rows)
        price: Optional[float] = None
        if decision == "accept":
            price = self.tariff_engine.price(request["weight_kg"], request["distance_km"])

        # 6. update store and notify according to decision table DT-S
        if decision == "accept":
            # Priced, notified quote, status quoted
            try:
                self.quote_store.update_quote(quote_id, "quoted", price=price)
            except StoreUnavailableError:
                return {"status": "error: store_unavailable", "quote_id": quote_id}

            try:
                self.notification_service.send_quote_document(quote_id)
            except Exception:
                # Notification is fire-and-forget; ignore any failure
                # A:dt:QuoteAPI|on_notification_failure@v1
                pass

            response = {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }
        elif decision == "review":
            # No pricing, no notification, status review_hold
            try:
                self.quote_store.update_quote(quote_id, "review_hold")
            except StoreUnavailableError:
                return {"status": "error: store_unavailable", "quote_id": quote_id}

            response = {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        else:  # decision == "refuse"
            # No pricing, refusal notice, status refused_screening
            try:
                self.quote_store.update_quote(quote_id, "refused_screening")
            except StoreUnavailableError:
                return {"status": "error: store_unavailable", "quote_id": quote_id}

            try:
                self.notification_service.send_refusal_notice(quote_id)
            except Exception:
                # Fire-and-forget semantics; ignore failures
                pass

            response = {
                "status": "refused_screening",
                "quote_id": quote_id,
            }

        # 7. respond (response already constructed with correct fields)
        return response

    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Validate request fields against DT-V constraints."""
        # shipper_id present and non-empty
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or not shipper_id:
            return False

        # weight_kg bounds
        weight = request.get("weight_kg")
        if not isinstance(weight, (int, float)):
            return False
        if not (self.MIN_WEIGHT <= weight <= self.MAX_WEIGHT):
            return False

        # distance_km bounds
        distance = request.get("distance_km")
        if not isinstance(distance, (int, float)):
            return False
        if not (self.MIN_DISTANCE <= distance <= self.MAX_DISTANCE):
            return False

        # declared_value bounds
        declared = request.get("declared_value")
        if not isinstance(declared, (int, float)):
            return False
        if not (self.MIN_DECLARED_VALUE <= declared <= self.MAX_DECLARED_VALUE):
            return False

        return True


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point delegating to QuoteAPI.

    In production, the collaborator instances would be real implementations;
    in tests, they can be monkeypatched or the QuoteAPI reconstructed
    directly with stubs.
    """
    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
