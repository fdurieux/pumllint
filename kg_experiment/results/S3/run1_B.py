from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable for draft storage or updates."""


class ScreeningUnavailableError(Exception):
    """Raised when the screening service is unavailable or times out."""


@dataclass
class QuoteStore:
    """Persistence adapter for quote drafts and updates.

    The real implementation would talk to a database; in this module we
    define only the interface so test harnesses can stub it.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a new draft quote and return its identifier.

        May raise StoreUnavailableError on storage failure.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, *, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote's status and optionally its price.

        May raise StoreUnavailableError on storage failure.
        """

        raise NotImplementedError


@dataclass
class TariffEngine:
    """Tariff calculation per DT-P (pricing decision table)."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the freight price according to DT-P.

        DT-P steps:
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: heavy surcharge: if weight_kg > 1244, add 316.00 (flat)
        P3: long-haul multiplier: if distance_km >= 4912, multiply running total by 1.19
        P4: price = round(result, 2)
        """

        # P1
        base = 0.87 * weight_kg + 1.13 * distance_km

        # P2
        if weight_kg > 1244:
            base += 316.00

        # P3
        if distance_km >= 4912:
            base *= 1.19

        # P4
        price = round(base, 2)
        return price


@dataclass
class ScreeningService:
    """External denied-party screening provider returning a risk index."""

    def screen(self, shipper_id: str) -> int:
        """Return the integer risk index for the given shipper.

        May raise ScreeningUnavailableError when the service is unavailable.
        """

        raise NotImplementedError


@dataclass
class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send a quote document to the shipper.

        Any delivery failure must not change the outcome or response; in this
        implementation, exceptions are caught by the caller and ignored.
        """

        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice to the shipper.

        Any delivery failure must not change the outcome or response; in this
        implementation, exceptions are caught by the caller and ignored.
        """

        raise NotImplementedError


class QuoteAPI:
    """Quote orchestration service implementing the CargoQuote flow."""

    def __init__(self) -> None:
        self.quote_store = QuoteStore()
        self.tariff_engine = TariffEngine()
        self.screening_service = ScreeningService()
        self.notification_service = NotificationService()

    def _validate(self, request: Dict[str, Any]) -> bool:
        """Validate request per DT-V.

        Returns True if valid, False otherwise.
        """

        # V1: shipper_id present and non-empty string
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False

        # Helper to validate numeric field
        def _get_number(key: str) -> Optional[float]:
            if key not in request:
                return None
            value = request.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
            # Any non-numeric is invalid
            return None

        weight = _get_number("weight_kg")
        distance = _get_number("distance_km")
        declared = _get_number("declared_value")

        if weight is None or distance is None or declared is None:
            return False

        # V2: 3 <= weight_kg <= 19400
        if not (3 <= weight <= 19400):
            return False

        # V3: 25 <= distance_km <= 7150
        if not (25 <= distance <= 7150):
            return False

        # V4: 50 <= declared_value <= 83000
        if not (50 <= declared <= 83000):
            return False

        return True

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a quote request.

        Orchestrates validation, draft storage, screening, pricing,
        notification, and response construction exactly as specified.
        """

        response: Dict[str, Any] = {}

        # 1. Validate the request (DT-V). Invalid → reject, stop.
        if not self._validate(request):
            response["status"] = "rejected: invalid_request"
            return response

        shipper_id = request["shipper_id"]
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # 2. Store the draft quote in the Quote Store with status `draft`.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            # If storage fails: return `error: store_unavailable`; do not call
            # screening; do not price; do not notify.
            return {"status": "error: store_unavailable"}

        # At this point, a draft exists.
        # 3. Request the shipper's risk index from the Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage path per spec:
            # price anyway, update stored quote to `held_unscreened`, do not
            # notify, and return the price with hold: true.
            price = self.tariff_engine.price(weight_kg, distance_km)

            # Update quote with held_unscreened and price. Any StoreUnavailableError
            # here is allowed to propagate, as behavior is unspecified in docs.
            self.quote_store.update_quote(
                quote_id,
                status="held_unscreened",
                price=price,
            )

            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4. Apply the screening decision (DT-S) to the risk index.
        # Concrete band mapping is assumed (see assumptions section).
        if risk_index <= 39:
            # Accept band → quoted
            status = "quoted"
            priced = True
            notified = True
            notify_kind = "quote_document"
        elif 40 <= risk_index <= 65:
            # Review band → review_hold
            status = "review_hold"
            priced = False
            notified = False
            notify_kind = None
        else:
            # Refuse band → refused_screening
            status = "refused_screening"
            priced = False
            notified = True
            notify_kind = "refusal_notice"

        price: Optional[float] = None

        # 5. Price the quote (DT-P) — only on the rows DT-S marks priced.
        if priced:
            price = self.tariff_engine.price(weight_kg, distance_km)

        # Update the stored quote to the resulting status (and price if any).
        # StoreUnavailableError from update_quote is not caught here; behavior
        # is unspecified in the documents for this case.
        self.quote_store.update_quote(
            quote_id,
            status=status,
            price=price,
        )

        # 6. Notify the shipper — only on the rows DT-S marks notified;
        # fire-and-forget.
        if notified:
            try:
                if notify_kind == "quote_document" and price is not None:
                    self.notification_service.send_quote_document(
                        shipper_id, quote_id, price
                    )
                elif notify_kind == "refusal_notice":
                    self.notification_service.send_refusal_notice(
                        shipper_id, quote_id
                    )
            except Exception:
                # Fire-and-forget: delivery failure never changes stored quote
                # or response, so swallow all exceptions from NotificationService.
                pass

        # 7. Return the response.
        response["status"] = status
        response["quote_id"] = quote_id
        if price is not None:
            response["price"] = price
        if status == "held_unscreened":
            # This only occurs on screening outage path, which already returned
            # above. Kept for completeness if status set otherwise.
            response["hold"] = True

        return response


# Module-level handle function expected by the harness.
def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    api = QuoteAPI()
    return api.handle(request)
