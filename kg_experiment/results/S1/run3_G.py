from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable."""
    pass


class ScreeningUnavailableError(Exception):
    """Raised when the screening service is unavailable."""
    pass


class QuoteStore:
    """Collaborator responsible for persisting quotes.

    Implementations must raise StoreUnavailableError on storage failure.
    """

    def store_draft(self, payload: Dict[str, Any]) -> str:
        """Store a new draft quote and return its quote_id.

        May raise StoreUnavailableError.
        """
        raise NotImplementedError

    def update_quote(self, quote_id: str, updates: Dict[str, Any]) -> None:
        """Update an existing quote.

        May raise StoreUnavailableError.
        """
        raise NotImplementedError


class TariffEngine:
    """Collaborator responsible for computing the freight price (DT-P)."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the price according to DT-P (P1..P4)."""
        # Implement DT-P using approved pricing rules.
        # base = 0.87 * weight_kg + 1.13 * distance_km  [A:dt:P1|formula@v1]
        result = 0.87 * weight_kg + 1.13 * distance_km

        # Heavy surcharge: if weight_kg > 1244, add 316.00 flat  [A:dt:P2|threshold@v1][A:dt:P2|surcharge@v1]
        if weight_kg > 1244:
            result += 316.00

        # Long-haul multiplier: if distance_km >= 4912, multiply by 1.19 after P2  [A:dt:P3|threshold@v1][A:dt:P3|factor@v1][A:dt:P3|order@v1]
        if distance_km >= 4912:
            result *= 1.19

        # price = round(result, 2)  [A:dt:P4|rounding@v1]
        return round(result, 2)


class ScreeningService:
    """Collaborator responsible for returning a shipper's risk index."""

    def screen(self, shipper_id: str) -> int:
        """Return the risk_index for the given shipper.

        May raise ScreeningUnavailableError on outage.
        """
        raise NotImplementedError


class NotificationService:
    """Collaborator responsible for sending notifications.

    Notification is fire-and-forget: failures must not affect stored
    quote or API response.  [A:dt:QuoteAPI|on_notification_failure@v1]
    """

    def send_quote_document(self, quote_id: str) -> None:
        """Send the quote document associated with the quote_id."""
        raise NotImplementedError

    def send_refusal_notice(self, quote_id: str) -> None:
        """Send the refusal notice associated with the quote_id."""
        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a quote request according to the governed spec.

        Flow order: validate > store > screen > decide > price > notify > respond
        [A:spec:flow|order@v1]
        """

        # 1. validate  [A:dt:shipper_id|present@v1][A:dt:weight_kg|min@v1][A:dt:weight_kg|max@v1]
        #              [A:dt:distance_km|min@v1][A:dt:distance_km|max@v1]
        #              [A:dt:declared_value|min@v1][A:dt:declared_value|max@v1]
        shipper_id = request.get("shipper_id")
        weight_kg = request.get("weight_kg")
        distance_km = request.get("distance_km")
        declared_value = request.get("declared_value")

        if not isinstance(shipper_id, str) or not shipper_id:
            # Invalid request behaviour  [A:dt:invalid_request|behaviour@v1]
            return {"status": "rejected: invalid_request"}

        # Basic numeric type checks; spec constrains ranges.
        if not isinstance(weight_kg, (int, float)):
            return {"status": "rejected: invalid_request"}
        if not isinstance(distance_km, (int, float)):
            return {"status": "rejected: invalid_request"}
        if not isinstance(declared_value, (int, float)):
            return {"status": "rejected: invalid_request"}

        # Range validation.
        if not (3 <= float(weight_kg) <= 19400):  # [A:dt:weight_kg|min@v1][A:dt:weight_kg|max@v1]
            return {"status": "rejected: invalid_request"}
        if not (25 <= float(distance_km) <= 7150):  # [A:dt:distance_km|min@v1][A:dt:distance_km|max@v1]
            return {"status": "rejected: invalid_request"}
        if not (50 <= float(declared_value) <= 83000):  # [A:dt:declared_value|min@v1][A:dt:declared_value|max@v1]
            return {"status": "rejected: invalid_request"}

        weight_kg = float(weight_kg)
        distance_km = float(distance_km)
        declared_value = float(declared_value)

        # 2. store draft in Quote Store with status 'draft'  [A:spec:QuoteAPI|on_store_failure@v1]
        try:
            draft_payload = {
                "shipper_id": shipper_id,
                "weight_kg": weight_kg,
                "distance_km": distance_km,
                "declared_value": declared_value,
                "status": "draft",
            }
            quote_id = self.quote_store.store_draft(draft_payload)
        except StoreUnavailableError:
            # On storage failure: error: store_unavailable; do nothing else
            # [A:spec:QuoteAPI|on_store_failure@v1]
            return {"status": "error: store_unavailable"}

        # Prepare response; quote_id whenever a draft was stored
        # [A:spec:response|quote_id_presence@v1]
        response: Dict[str, Any] = {"quote_id": quote_id}

        # 3. screen - request risk index from Screening Service  [A:spec:QuoteAPI|on_screening_outage@v1]
        try:
            risk_index = self.screening_service.screen(shipper_id)
            screening_outage = False
        except ScreeningUnavailableError:
            risk_index = None
            screening_outage = True

        # 4. decide (screening decision) and branch  [DT-S]
        if screening_outage:
            # Screening outage path  [A:spec:QuoteAPI|on_screening_outage@v1]
            # 5. price anyway (DT-P)
            price_value = self.tariff_engine.price(weight_kg, distance_km)

            # Update stored quote to held_unscreened  [A:spec:QuoteAPI|on_screening_outage@v1]
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {
                        "status": "held_unscreened",
                        "price": price_value,
                    },
                )
            except StoreUnavailableError:
                # Spec only defines store failure on initial storeDraft; no
                # alternative behaviour for update failures is provided.
                # We let the exception propagate, surfacing an implementation-time
                # error rather than inventing behaviour.
                raise

            # Do not notify on screening outage  [A:spec:QuoteAPI|on_screening_outage@v1]

            # 7. respond with price and hold: true  [A:spec:QuoteAPI|on_screening_outage@v1]
            response["status"] = "held_unscreened"
            response["price"] = price_value  # priced row  [A:spec:response|price_presence@v1]
            response["hold"] = True  # held_unscreened only  [A:spec:response|hold_presence@v1]
            return response

        # No screening outage: we have a risk_index; apply DT-S.
        assert risk_index is not None

        if risk_index <= 41:  # accept band  [A:dt:S-accept|max@v1]
            # accept row: quote issued, priced, notified, status quoted
            # 5. price
            price_value = self.tariff_engine.price(weight_kg, distance_km)

            # Update stored quote to quoted with price.
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {
                        "status": "quoted",  # [A:dt:S-accept|status@v1]
                        "price": price_value,
                    },
                )
            except StoreUnavailableError:
                # No explicit behaviour specified for update failure; do not invent.
                raise

            # 6. notify with quote document (fire-and-forget)
            try:
                self.notification_service.send_quote_document(quote_id)
            except Exception:
                # Fire-and-forget: failures never change stored quote or response
                # [A:dt:QuoteAPI|on_notification_failure@v1]
                pass

            # 7. respond: priced row, status quoted, include price
            response["status"] = "quoted"
            response["price"] = price_value  # priced row  [A:spec:response|price_presence@v1]
            return response

        if 42 <= risk_index <= 66:  # review band  [A:dt:S-review|min@v1][A:dt:S-review|max@v1]
            # review row: held for manual review, no price, no notification, status review_hold
            try:
                self.quote_store.update_quote(
                    quote_id,
                    {
                        "status": "review_hold",  # [A:dt:S-review|status@v1]
                    },
                )
            except StoreUnavailableError:
                # No explicit behaviour specified for update failure; do not invent.
                raise

            response["status"] = "review_hold"
            # No price field on unpriced rows  [A:spec:response|price_presence@v1]
            return response

        # risk_index >= 67: refuse band  [A:dt:S-refuse|min@v1]
        try:
            self.quote_store.update_quote(
                quote_id,
                {
                    "status": "refused_screening",  # [A:dt:S-refuse|status@v1]
                },
            )
        except StoreUnavailableError:
            # No explicit behaviour specified for update failure; do not invent.
            raise

        # Send refusal notice (fire-and-forget) [A:dt:S-refuse|notified@v1]
        try:
            self.notification_service.send_refusal_notice(quote_id)
        except Exception:
            # Fire-and-forget: failures never change stored quote or response
            # [A:dt:QuoteAPI|on_notification_failure@v1]
            pass

        # Respond with refused_screening status, unpriced row. [A:oas:response|statuses@v1][A:spec:response|price_presence@v1]
        response["status"] = "refused_screening"
        return response


# Module-level handle, as required by the harness.

def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level entry point wiring real collaborators.

    In production, QuoteStore, TariffEngine, ScreeningService, and
    NotificationService would be concrete implementations. Here we
    instantiate the base classes, expecting a test harness to monkeypatch
    their methods as needed.
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
