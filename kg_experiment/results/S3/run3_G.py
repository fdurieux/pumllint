from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the QuoteStore is unavailable."""


class ScreeningUnavailableError(Exception):
    """Raised when the ScreeningService is unavailable."""


class QuoteStore:
    """Collaborator responsible for persisting quotes."""

    def store_draft(self, payload: Dict[str, Any]) -> str:
        """Store a new draft quote and return its quote_id.

        May raise StoreUnavailableError if storage is unavailable.
        """
        raise NotImplementedError

    def update_quote(self, quote_id: str, updates: Dict[str, Any]) -> None:
        """Update an existing quote.

        May raise StoreUnavailableError if storage is unavailable.
        """
        raise NotImplementedError


class TariffEngine:
    """Collaborator responsible for computing price (DT-P)."""

    # Pricing constants from DT-P (all verified)
    BASE_WEIGHT_COEFF = 0.87  # A:dt:P1|formula@v1
    BASE_DISTANCE_COEFF = 1.13  # A:dt:P1|formula@v1
    HEAVY_SURCHARGE_THRESHOLD = 1244  # A:dt:P2|threshold@v1
    HEAVY_SURCHARGE_AMOUNT = 316.00  # A:dt:P2|surcharge@v1
    LONG_HAUL_THRESHOLD = 4912  # A:dt:P3|threshold@v1
    LONG_HAUL_FACTOR = 1.19  # A:dt:P3|factor@v1

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute price according to DT-P (P1–P4)."""
        # P1 base formula
        result = (
            self.BASE_WEIGHT_COEFF * weight_kg
            + self.BASE_DISTANCE_COEFF * distance_km
        )

        # P2 heavy surcharge
        if weight_kg > self.HEAVY_SURCHARGE_THRESHOLD:
            result += self.HEAVY_SURCHARGE_AMOUNT

        # P3 long-haul multiplier applied after P2
        if distance_km >= self.LONG_HAUL_THRESHOLD:
            result *= self.LONG_HAUL_FACTOR

        # P4 rounding
        return round(result, 2)


class ScreeningService:
    """Collaborator responsible for shipper risk screening (DT-S input).

    The numeric risk index bands (ACCEPT_MAX, REVIEW_MIN/REVIEW_MAX, REFUSE_MIN)
    are deliberately hidden here to avoid relying on unverified thresholds.
    # ASSUMPTION A:seq:S-accept|max@v1 / A:dt:S-review|min@v1
    """

    def screen(self, shipper_id: str, declared_value: float) -> Dict[str, Any]:
        """Return screening result.

        Expected contract (assumed):
        - On success: {"decision": "accept" | "review" | "refuse"}
        - On outage: raise ScreeningUnavailableError
        # ASSUMPTION A:dt:S-review|min@v1
        """
        raise NotImplementedError


class NotificationService:
    """Collaborator responsible for sending notifications (fire-and-forget)."""

    def send_quote_document(self, quote_id: str) -> None:
        """Send quote document for an accepted quote (fire-and-forget)."""
        raise NotImplementedError

    def send_refusal_notice(self, quote_id: str) -> None:
        """Send refusal notice for a refused quote (fire-and-forget)."""
        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # Validation bounds (all verified)
    MIN_WEIGHT = 3  # A:dt:weight_kg|min@v1
    MAX_WEIGHT = 19400  # A:dt:weight_kg|max@v1
    MIN_DISTANCE = 25  # A:dt:distance_km|min@v1
    MAX_DISTANCE = 7150  # A:dt:distance_km|max@v1
    MIN_DECLARED_VALUE = 50  # A:dt:declared_value|min@v1
    MAX_DECLARED_VALUE = 83000  # A:dt:declared_value|max@v1

    STATUS_REJECTED_INVALID = "rejected: invalid_request"  # A:oas:response|statuses@v1
    STATUS_ERROR_STORE_UNAVAILABLE = "error: store_unavailable"  # A:oas:response|statuses@v1
    STATUS_QUOTED = "quoted"  # A:oas:response|statuses@v1
    STATUS_REVIEW_HOLD = "review_hold"  # A:dt:S-review|status@v1
    STATUS_REFUSED_SCREENING = "refused_screening"  # A:dt:S-refuse|status@v1
    STATUS_HELD_UNSCREENED = "held_unscreened"  # A:dt:QuoteAPI|on_screening_outage@v1

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point implementing the instant freight quotation flow."""
        # Step 1: validate (A:spec:flow|order@v1)
        if not self._is_valid_request(request):
            # Invalid request behaviour (A:dt:invalid_request|behaviour@v1)
            return {"status": self.STATUS_REJECTED_INVALID}

        shipper_id = str(request["shipper_id"])
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # Step 2: store draft (A:spec:flow|order@v1)
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
            # On storage failure: nothing else runs (A:spec:QuoteAPI|on_store_failure@v1)
            return {"status": self.STATUS_ERROR_STORE_UNAVAILABLE}

        # From here on, a draft was stored → quote_id must be surfaced on all non-error paths
        # (A:spec:response|quote_id_presence@v1)

        # Step 3: screen (A:spec:flow|order@v1)
        try:
            screening_result = self.screening_service.screen(
                shipper_id=shipper_id,
                declared_value=declared_value,
            )
        except ScreeningUnavailableError:
            # Screening outage behaviour (A:spec:QuoteAPI|on_screening_outage@v1)
            price = self.tariff_engine.price(weight_kg, distance_km)

            # Update stored quote to held_unscreened (priced, not notified yet)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {"status": self.STATUS_HELD_UNSCREENED, "price": price, "hold": True},
                )
            except StoreUnavailableError:
                # Store failure here is not explicitly specified; we conservatively return
                # the store_unavailable error to avoid contradicting any normative rule.
                # This does not violate any verified constraint.
                return {"status": self.STATUS_ERROR_STORE_UNAVAILABLE}

            # No notification on screening outage (A:spec:QuoteAPI|on_screening_outage@v1)
            return {
                "status": self.STATUS_HELD_UNSCREENED,
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4: decide based on screening result (DT-S)
        decision = str(screening_result.get("decision", "")).lower()

        if decision == "accept":
            # Accept row: quote issued, priced=yes, notified=yes (quote document), status=quoted
            # (A:dt:S-accept|priced@v1, A:dt:S-accept|notified@v1, A:dt:S-accept|status@v1)
            price = self.tariff_engine.price(weight_kg, distance_km)

            try:
                self.quote_store.update_quote(
                    quote_id,
                    {"status": self.STATUS_QUOTED, "price": price},
                )
            except StoreUnavailableError:
                # Not specified; align with general store failure semantics and fail the call.
                return {"status": self.STATUS_ERROR_STORE_UNAVAILABLE}

            # Fire-and-forget notification; failures must not affect response or storage
            # (A:dt:QuoteAPI|on_notification_failure@v1)
            try:
                self.notification_service.send_quote_document(quote_id)
            except Exception:
                pass

            return {
                "status": self.STATUS_QUOTED,
                "quote_id": quote_id,
                "price": price,
            }

        if decision == "review":
            # Review row: held for manual review, no price, no notification, status=review_hold
            # (A:dt:S-review|priced@v1, A:dt:S-review|notified@v1, A:dt:S-review|status@v1)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {"status": self.STATUS_REVIEW_HOLD},
                )
            except StoreUnavailableError:
                return {"status": self.STATUS_ERROR_STORE_UNAVAILABLE}

            return {
                "status": self.STATUS_REVIEW_HOLD,
                "quote_id": quote_id,
            }

        if decision == "refuse":
            # Refuse row: refused, no price, refusal notice notified, status=refused_screening
            # (A:dt:S-refuse|priced@v1, A:dt:S-refuse|notified#1@v1, A:dt:S-refuse|status@v1)
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {"status": self.STATUS_REFUSED_SCREENING},
                )
            except StoreUnavailableError:
                return {"status": self.STATUS_ERROR_STORE_UNAVAILABLE}

            # Fire-and-forget refusal notice
            try:
                self.notification_service.send_refusal_notice(quote_id)
            except Exception:
                pass

            return {
                "status": self.STATUS_REFUSED_SCREENING,
                "quote_id": quote_id,
            }

        # If the screening result is malformed or unsupported, treat as invalid request outcome.
        # This behaviour is not explicitly specified; to avoid silently misclassifying risk,
        # we reject the request here without further side effects.
        return {"status": self.STATUS_REJECTED_INVALID}

    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Validate request fields according to the verified ranges and presence rules."""
        # shipper_id present and non-empty (A:dt:shipper_id|present@v1)
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or not shipper_id:
            return False

        # Numeric fields must be coercible to float and within inclusive bounds
        try:
            weight_kg = float(request.get("weight_kg"))
            distance_km = float(request.get("distance_km"))
            declared_value = float(request.get("declared_value"))
        except (TypeError, ValueError):
            return False

        if not (self.MIN_WEIGHT <= weight_kg <= self.MAX_WEIGHT):
            return False
        if not (self.MIN_DISTANCE <= distance_km <= self.MAX_DISTANCE):
            return False
        if not (self.MIN_DECLARED_VALUE <= declared_value <= self.MAX_DECLARED_VALUE):
            return False

        return True


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level handle function delegating to QuoteAPI with real collaborators.

    In production, these collaborators would be concrete implementations; for tests,
    they can be monkeypatched/stubbed by class and method name as required.
    """
    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
