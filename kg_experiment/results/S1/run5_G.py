from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable."""


class ScreeningUnavailableError(Exception):
    """Raised when the screening service is unavailable."""


class QuoteStore:
    """Collaborator responsible for persisting quotes.

    The real implementation is provided elsewhere; this is a stub-able API.
    """

    def store_draft(self, payload: Dict[str, Any]) -> str:
        """Store a new draft quote and return its quote_id.

        May raise StoreUnavailableError when storage fails.
        """
        raise NotImplementedError

    def update_quote(self, quote_id: str, updates: Dict[str, Any]) -> None:
        """Update an existing quote with the given fields.

        May raise StoreUnavailableError when storage fails.
        """
        raise NotImplementedError


class TariffEngine:
    """Collaborator responsible for computing the freight price (DT-P)."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # Implement DT-P locally based on approved pricing table.
        # base = 0.87 * weight_kg + 1.13 * distance_km  [A:dt:P1|formula@v1]
        result = 0.87 * weight_kg + 1.13 * distance_km

        # heavy surcharge: if weight_kg > 1244, add 316.00 (flat) [A:dt:P2|threshold@v1, A:dt:P2|surcharge@v1]
        if weight_kg > 1244:
            result += 316.00

        # long-haul multiplier: if distance_km >= 4912, multiply running total by 1.19 after P2 [A:dt:P3|threshold@v1, A:dt:P3|factor@v1, A:dt:P3|order@v1]
        if distance_km >= 4912:
            result *= 1.19

        # price = round(result, 2) [A:dt:P4|rounding@v1]
        price = round(result, 2)
        return price


class ScreeningService:
    """Collaborator responsible for returning a shipper risk index (DT-S input)."""

    def screen(self, shipper_id: str) -> int:
        """Return the risk index for the given shipper.

        May raise ScreeningUnavailableError if the service is unavailable.
        """
        raise NotImplementedError


class NotificationService:
    """Collaborator responsible for sending documents and notices.

    Notification is fire-and-forget: failures must not alter stored quote
    or response. [A:dt:QuoteAPI|on_notification_failure@v1]
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

    # Constants for validation bounds
    MIN_WEIGHT = 3.0  # [A:dt:weight_kg|min@v1]
    MAX_WEIGHT = 19400.0  # [A:dt:weight_kg|max@v1]
    MIN_DISTANCE = 25.0  # [A:dt:distance_km|min@v1]
    MAX_DISTANCE = 7150.0  # [A:dt:distance_km|max@v1]
    MIN_DECLARED_VALUE = 50.0  # [A:dt:declared_value|min@v1]
    MAX_DECLARED_VALUE = 83000.0  # [A:dt:declared_value|max@v1]

    # Screening decision thresholds
    ACCEPT_MAX = 41  # risk_index <= 41 => accept [A:dt:S-accept|max@v1]
    REVIEW_MIN = 42  # [A:dt:S-review|min@v1]
    REVIEW_MAX = 66  # [A:dt:S-review|max@v1]
    REFUSE_MIN = 67  # risk_index >= 67 => refuse [A:dt:S-refuse|min@v1]

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a quote request according to the governed contract.

        Implements: validate > store > screen > decide > price > notify > respond.
        [A:spec:flow|order@v1]
        """

        # 1. validate
        if not self._is_valid_request(request):
            # Invalid request behaviour [A:dt:invalid_request|behaviour@v1]
            return {"status": "rejected: invalid_request"}

        shipper_id = str(request["shipper_id"])
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # 2. store draft
        draft_payload = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
        }

        try:
            quote_id = self.quote_store.store_draft(draft_payload)
        except StoreUnavailableError:
            # On storage failure nothing else runs; status error: store_unavailable
            # [A:spec:QuoteAPI|on_store_failure@v1]
            return {"status": "error: store_unavailable"}

        # 3. screen
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_outage = False
        except ScreeningUnavailableError:
            # Screening outage path [A:spec:QuoteAPI|on_screening_outage@v1]
            risk_index = None
            screening_outage = True

        response: Dict[str, Any] = {"quote_id": quote_id}

        # 4. decide + 5. price + 6. notify
        if screening_outage:
            # Screening outage behaviour: price anyway; store as held_unscreened;
            # do not notify; hold: true in response.
            price = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {
                        "status": "held_unscreened",
                        "price": price,
                        "hold": True,
                    },
                )
            except StoreUnavailableError:
                # Contract does not override DT-S note 3 for later updates; on
                # store failure nothing else runs. We cannot roll back, but we
                # still must not notify further; response matches latest intent.
                return {
                    "status": "error: store_unavailable",
                    "quote_id": quote_id,
                }

            response["status"] = "held_unscreened"
            response["price"] = price
            response["hold"] = True
            # No notification [A:spec:QuoteAPI|on_screening_outage@v1]
            return response

        # Normal screening path: we have a concrete risk_index
        assert risk_index is not None

        if risk_index <= self.ACCEPT_MAX:
            # Accept row: quote issued, priced, notified with quote document,
            # status quoted. [A:dt:S-accept|status@v1]
            price = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {
                        "status": "quoted",
                        "price": price,
                    },
                )
            except StoreUnavailableError:
                return {
                    "status": "error: store_unavailable",
                    "quote_id": quote_id,
                }

            # Notification is fire-and-forget; ignore failures.
            try:
                self.notification_service.send_quote_document(quote_id)
            except Exception:
                # Do not alter stored quote or response.
                # [A:dt:QuoteAPI|on_notification_failure@v1]
                pass

            response["status"] = "quoted"
            response["price"] = price
            return response

        if self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # Review row: held for manual review, no pricing, no notification,
            # status review_hold. [A:dt:S-review|status@v1]
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {
                        "status": "review_hold",
                    },
                )
            except StoreUnavailableError:
                return {
                    "status": "error: store_unavailable",
                    "quote_id": quote_id,
                }

            response["status"] = "review_hold"
            return response

        # risk_index >= REFUSE_MIN branch (refuse)
        if risk_index >= self.REFUSE_MIN:
            # Refuse row: refused, no pricing, notified with refusal notice,
            # status refused_screening. [A:dt:S-refuse|status@v1]
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {
                        "status": "refused_screening",
                    },
                )
            except StoreUnavailableError:
                return {
                    "status": "error: store_unavailable",
                    "quote_id": quote_id,
                }

            # Send refusal notice, fire-and-forget.
            try:
                self.notification_service.send_refusal_notice(quote_id)
            except Exception:
                # Do not alter stored quote or response.
                pass

            response["status"] = "refused_screening"
            return response

        # The DMN/DT-S table is exhaustive for risk_index; this branch should
        # not be reachable under the governed rules. However, to remain total,
        # fall back to review_hold semantics without pricing or notification.
        try:
            self.quote_store.update_quote(
                quote_id,
                {
                    "status": "review_hold",
                },
            )
        except StoreUnavailableError:
            return {
                "status": "error: store_unavailable",
                "quote_id": quote_id,
            }

        response["status"] = "review_hold"
        return response

    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Validate presence and ranges according to contract tables."""

        # shipper_id present and non-empty [A:dt:shipper_id|present@v1]
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or not shipper_id:
            return False

        # weight_kg range [A:dt:weight_kg|min@v1, A:dt:weight_kg|max@v1]
        try:
            weight = float(request.get("weight_kg"))
        except (TypeError, ValueError):
            return False
        if not (self.MIN_WEIGHT <= weight <= self.MAX_WEIGHT):
            return False

        # distance_km range [A:dt:distance_km|min@v1, A:dt:distance_km|max@v1]
        try:
            distance = float(request.get("distance_km"))
        except (TypeError, ValueError):
            return False
        if not (self.MIN_DISTANCE <= distance <= self.MAX_DISTANCE):
            return False

        # declared_value range [A:dt:declared_value|min@v1, A:dt:declared_value|max@v1]
        try:
            declared = float(request.get("declared_value"))
        except (TypeError, ValueError):
            return False
        if not (self.MIN_DECLARED_VALUE <= declared <= self.MAX_DECLARED_VALUE):
            return False

        return True


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point delegating to QuoteAPI.

    Collaborators are instantiated with default stub implementations that
    can be replaced in tests by monkeypatching the classes/methods.
    """

    quote_store = QuoteStore()
    tariff_engine = TariffEngine()
    screening_service = ScreeningService()
    notification_service = NotificationService()

    api = QuoteAPI(
        quote_store=quote_store,
        tariff_engine=tariff_engine,
        screening_service=screening_service,
        notification_service=notification_service,
    )

    return api.handle(request)
