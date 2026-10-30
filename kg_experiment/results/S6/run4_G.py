from dataclasses import dataclass
from typing import Any, Dict


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable."""


class ScreeningUnavailableError(Exception):
    """Raised when the screening service is unavailable."""


class QuoteStore:
    """Persistence for quotes.

    The real implementation is provided elsewhere; this stub defines the
    interface for testing and stubbing.
    """

    def store_draft(self, request: Dict[str, Any]) -> str:
        """Store a draft quote and return its quote_id.

        May raise StoreUnavailableError on storage failure.
        """
        raise NotImplementedError

    def update_quote(self, quote_id: str, updates: Dict[str, Any]) -> None:
        """Update an existing quote.

        May raise StoreUnavailableError on storage failure.
        """
        raise NotImplementedError


class TariffEngine:
    """Pricing engine implementing DT-P."""

    # Constants taken from approved tariff assertions
    BASE_WEIGHT_COEFF = 0.87  # from P1 formula
    BASE_DISTANCE_COEFF = 1.13  # from P1 formula
    HEAVY_THRESHOLD = 1244  # from A:dt:P2|threshold@v2
    HEAVY_SURCHARGE = 341.00  # from A:dt:P2|surcharge@v2
    LONG_HAUL_THRESHOLD = 4912  # from A:dt:P3|threshold@v1
    LONG_HAUL_FACTOR = 1.19  # from A:dt:P3|factor@v1

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the price according to DT-P.

        Implements:
        - P1: base = 0.87 * weight_kg + 1.13 * distance_km
        - P2: if weight_kg > 1244, add 341.00 flat
        - P3: if distance_km >= 4912, multiply running total by 1.19,
               applied after P2
        - P4: price = round(result, 2)
        """
        base = self.BASE_WEIGHT_COEFF * weight_kg + self.BASE_DISTANCE_COEFF * distance_km

        # P2 heavy surcharge
        if weight_kg > self.HEAVY_THRESHOLD:
            base += self.HEAVY_SURCHARGE

        # P3 long-haul multiplier (applied after P2)
        if distance_km >= self.LONG_HAUL_THRESHOLD:
            base *= self.LONG_HAUL_FACTOR

        # P4 rounding
        price = round(base, 2)
        return price


class ScreeningService:
    """External screening service to obtain shipper risk index."""

    def screen(self, shipper_id: str) -> int:
        """Return the risk index for the given shipper.

        May raise ScreeningUnavailableError if the service is unavailable.
        """
        raise NotImplementedError


class NotificationService:
    """Notification service for quote documents and refusal notices."""

    def send_quote_document(self, quote_id: str) -> None:
        """Send a quote document (fire-and-forget).

        Failures must not alter stored quote or API response.
        """
        raise NotImplementedError

    def send_refusal_notice(self, quote_id: str) -> None:
        """Send a refusal notice (fire-and-forget).

        Failures must not alter stored quote or API response.
        """
        raise NotImplementedError


@dataclass
class QuoteAPI:
    """Implements the CargoQuote flow according to the governed spec."""

    store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notifier: NotificationService

    # Validation bounds from decision tables / OpenAPI
    MIN_WEIGHT = 3
    MAX_WEIGHT = 19400
    MIN_DISTANCE = 25
    MAX_DISTANCE = 7150
    MIN_DECLARED_VALUE = 50
    MAX_DECLARED_VALUE = 83000

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a quote request according to the governed flow.

        Flow order (spec flow|order): validate > store > screen > decide > price > notify > respond.
        """
        # 1. validate
        if not self._is_valid_request(request):
            # invalid_request behaviour: reject immediately, no side effects
            return {
                "status": "rejected: invalid_request",
            }

        # 2. store (draft)
        try:
            quote_id = self.store.store_draft({
                "shipper_id": request["shipper_id"],
                "weight_kg": request["weight_kg"],
                "distance_km": request["distance_km"],
                "declared_value": request["declared_value"],
                "status": "draft",
            })
        except StoreUnavailableError:
            # On storage failure: status error: store_unavailable; nothing else runs
            return {
                "status": "error: store_unavailable",
            }

        # 3. screen
        try:
            risk_index = self.screening_service.screen(request["shipper_id"])
            screening_outage = False
        except ScreeningUnavailableError:
            # Screening outage path, treated specially later
            risk_index = None
            screening_outage = True

        response: Dict[str, Any] = {
            "quote_id": quote_id,
        }

        # 4. decide, 5. price, 6. notify
        if screening_outage:
            # On screening outage: price anyway, status held_unscreened, not notified, hold: true
            price = self.tariff_engine.price(request["weight_kg"], request["distance_km"])
            try:
                self.store.update_quote(quote_id, {"status": "held_unscreened", "price": price})
            except StoreUnavailableError:
                # Spec does not override on-store-failure behaviour here;
                # store failures after draft persist are not explicitly governed,
                # but we must not contradict earlier rule that store failure
                # stops the flow. We surface the error without further actions.
                return {
                    "status": "error: store_unavailable",
                }

            response["status"] = "held_unscreened"
            response["price"] = price
            response["hold"] = True
            # Notification is explicitly suppressed on held_unscreened
            # (no calls to notifier here).
            return response

        # Normal screening path using risk_index
        assert risk_index is not None

        if risk_index <= 41:
            # accept row: priced, notified with quote document, status quoted
            price = self.tariff_engine.price(request["weight_kg"], request["distance_km"])
            try:
                self.store.update_quote(quote_id, {"status": "quoted", "price": price})
            except StoreUnavailableError:
                return {
                    "status": "error: store_unavailable",
                }

            response["status"] = "quoted"
            response["price"] = price

            # Notification is fire-and-forget; failures must not change response
            try:
                self.notifier.send_quote_document(quote_id)
            except Exception:
                # Per specification, ignore notification failures
                pass

            return response

        if 42 <= risk_index <= 66:
            # review row: no pricing, no notification, status review_hold
            try:
                self.store.update_quote(quote_id, {"status": "review_hold"})
            except StoreUnavailableError:
                return {
                    "status": "error: store_unavailable",
                }

            response["status"] = "review_hold"
            return response

        # risk_index >= 67: refuse row, no pricing, refusal notice sent
        try:
            self.store.update_quote(quote_id, {"status": "refused_screening"})
        except StoreUnavailableError:
            return {
                "status": "error: store_unavailable",
            }

        response["status"] = "refused_screening"

        # Fire-and-forget refusal notice; ignore failures
        try:
            self.notifier.send_refusal_notice(quote_id)
        except Exception:
            pass

        return response

    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Validate request fields according to decision tables and OpenAPI."""
        # shipper_id present and non-empty
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or not shipper_id:
            return False

        # numeric fields must be within defined ranges
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


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point using default service instances.

    In production, the collaborators would be real implementations; for tests,
    the QuoteAPI class and collaborators can be instantiated and patched
    directly.
    """
    api = QuoteAPI(
        store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notifier=NotificationService(),
    )
    return api.handle(request)
