from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable for draft storage or updates."""


class ScreeningUnavailableError(Exception):
    """Raised when the screening service is unavailable (screening outage)."""


class QuoteStore:
    """Persistence layer for quotes.

    In this kata-style implementation, the methods are stubs meant to be
    replaced or monkey-patched by tests. The behavior described here is
    the logical contract used by QuoteAPI.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        May raise StoreUnavailableError if initial storage fails.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote's status and optionally its price.

        For this exercise, behavior on failures is unspecified by the spec;
        tests can stub this method. Implementations MAY raise
        StoreUnavailableError, which this module does not specially handle.
        """

        raise NotImplementedError


class TariffEngine:
    """Tariff calculation according to DT-P."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute the freight price per DT-P.

        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: heavy surcharge: if weight_kg > 1244, add 316.00 (flat)
        P3: long-haul multiplier: if distance_km >= 4912, multiply running
            total by 1.19 (after P2)
        P4: price = round(result, 2)
        """

        base = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            base += 316.00
        if distance_km >= 4912:
            base *= 1.19
        return round(base, 2)


class ScreeningService:
    """External screening provider wrapper."""

    def screen(self, shipper_id: str) -> int:
        """Return the risk index for the given shipper.

        May raise ScreeningUnavailableError to signal an outage.
        """

        raise NotImplementedError


class NotificationService:
    """External notification provider wrapper."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send a quote document to the shipper.

        Any exceptions represent delivery or provider failures and MUST NOT
        affect the API response (fire-and-forget semantics)."""

        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice to the shipper.

        Any exceptions represent delivery or provider failures and MUST NOT
        affect the API response (fire-and-forget semantics)."""

        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # ---- Public entry point ----

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a quote request per the CargoQuote specification.

        The request dict must contain shipper_id, weight_kg, distance_km,
        declared_value. Response always contains a status, and may contain
        quote_id, price, and hold as defined by the spec.
        """

        # 1. Validate request (DT-V). Invalid → reject, stop.
        if not self._is_valid_request(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # 2. Store the draft quote with status `draft`.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            # Storage failure → error: store_unavailable, nothing else runs.
            return {"status": "error: store_unavailable"}

        # From here on, we must include quote_id in all non-rejection responses.

        # 3. Request risk index from Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage → price anyway, status held_unscreened, no notify,
            # response carries price and hold: true.
            price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)
            # Spec says: stored with status held_unscreened.
            self.quote_store.update_quote(quote_id=quote_id, status="held_unscreened", price=price)
            return {"status": "held_unscreened", "quote_id": quote_id, "price": price, "hold": True}

        # 4. Apply screening decision (DT-S) to the risk index.
        if risk_index <= 41:
            # Accept row: quoted, priced, notified.
            price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)
            self.quote_store.update_quote(quote_id=quote_id, status="quoted", price=price)
            # Notify fire-and-forget; swallow any exceptions.
            try:
                self.notification_service.send_quote_document(shipper_id=shipper_id, quote_id=quote_id, price=price)
            except Exception:
                pass
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        if 42 <= risk_index <= 66:
            # Review row: review_hold, no price, no notification.
            self.quote_store.update_quote(quote_id=quote_id, status="review_hold", price=None)
            return {"status": "review_hold", "quote_id": quote_id}

        # risk_index >= 67: refused row.
        self.quote_store.update_quote(quote_id=quote_id, status="refused_screening", price=None)
        # Notify fire-and-forget; swallow any exceptions.
        try:
            self.notification_service.send_refusal_notice(shipper_id=shipper_id, quote_id=quote_id)
        except Exception:
            pass
        return {"status": "refused_screening", "quote_id": quote_id}

    # ---- Internal helpers ----

    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Check DT-V validation rules.

        A request is valid iff:
        - shipper_id present and non-empty string
        - weight_kg is a number with 3 <= weight_kg <= 19400
        - distance_km is a number with 25 <= distance_km <= 7150
        - declared_value is a number with 50 <= declared_value <= 83000
        """

        # V1: shipper_id present and non-empty
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False

        # Helper to check numeric bounds for int/float only.
        def in_numeric_range(key: str, lo: float, hi: float) -> bool:
            if key not in request:
                return False
            value = request[key]
            if not isinstance(value, (int, float)):
                return False
            return lo <= float(value) <= hi

        # V2: weight_kg
        if not in_numeric_range("weight_kg", 3, 19400):
            return False

        # V3: distance_km
        if not in_numeric_range("distance_km", 25, 7150):
            return False

        # V4: declared_value
        if not in_numeric_range("declared_value", 50, 83000):
            return False

        return True


# Module-level handle function required by the harness.

def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level facade delegating to QuoteAPI with default collaborators.

    Tests are expected to monkey-patch or subclass the collaborator
    classes (QuoteStore, TariffEngine, ScreeningService, NotificationService)
    as needed.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
