from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the Quote Store is unavailable for storing data."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service is unavailable (screening outage)."""


class QuoteStore:
    """Persistence layer for quotes.

    In production this would talk to a database. Here it is a stubbed
    collaborator; tests may override its methods or subclass it.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        Raises StoreUnavailableError on storage failure.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote's status and optionally its price.

        May raise StoreUnavailableError if the store becomes unavailable.
        Error semantics for this in the spec are not defined; callers may let it
        propagate.
        """

        raise NotImplementedError


class TariffEngine:
    """Tariff engine implementing DT-P pricing rules."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # P1: base = 0.87 * weight_kg + 1.13 * distance_km
        base = 0.87 * weight_kg + 1.13 * distance_km
        # P2: heavy surcharge if weight_kg > 1244, add 341.00
        if weight_kg > 1244:
            base += 341.00
        # P3: long-haul multiplier if distance_km >= 4912, multiply running total by 1.19
        if distance_km >= 4912:
            base *= 1.19
        # P4: round to 2 decimals
        price = round(base, 2)
        return price


class ScreeningService:
    """External screening provider stub."""

    def screen(self, shipper_id: str) -> int:
        """Return an integer risk index for the shipper.

        Raises ScreeningUnavailableError on screening outage.
        """

        raise NotImplementedError


class NotificationService:
    """External notification provider stub."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send a quote document to the shipper.

        Any exceptions are considered delivery failures and must not affect the
        outcome or response; callers should catch and ignore them.
        """

        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice to the shipper.

        Any exceptions are considered delivery failures and must not affect the
        outcome or response; callers should catch and ignore them.
        """

        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # ---- Public entrypoint ----

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a quote request according to the CargoQuote specification.

        request: dict with keys shipper_id, weight_kg, distance_km, declared_value.
        Returns a dict with at least a 'status' key, and possibly 'quote_id',
        'price', and 'hold' per the spec.
        """

        # Step 1: Validate request (DT-V). Invalid -> reject, stop.
        valid, validation_status = self._validate(request)
        if not valid:
            return {"status": validation_status}

        shipper_id = str(request["shipper_id"])
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # Step 2: Store draft quote with status draft.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            # storage failure -> error: store_unavailable, nothing else runs
            return {"status": "error: store_unavailable"}

        # Step 3: Request risk index from Screening Service.
        screening_outage = False
        risk_index: Optional[int]
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            screening_outage = True
            risk_index = None

        # Screening outage path: price anyway, update to held_unscreened, no notify.
        if screening_outage:
            price = self.tariff_engine.price(weight_kg, distance_km)
            # Update stored quote status and price. Store failure semantics
            # here are unspecified; let StoreUnavailableError propagate if raised.
            self.quote_store.update_quote(quote_id, status="held_unscreened", price=price)
            return {"status": "held_unscreened", "quote_id": quote_id, "price": price, "hold": True}

        assert risk_index is not None

        # Step 4: Apply screening decision (DT-S) to risk index.
        if risk_index <= 41:
            # accept row: priced, notified (quote document), status quoted
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, status="quoted", price=price)
            # fire-and-forget notification
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                # outcome and response unchanged
                pass
            return {"status": "quoted", "quote_id": quote_id, "price": price}

        if 42 <= risk_index <= 66:
            # review row: not priced, not notified, status review_hold
            self.quote_store.update_quote(quote_id, status="review_hold", price=None)
            return {"status": "review_hold", "quote_id": quote_id}

        # refuse row: risk_index >= 67
        self.quote_store.update_quote(quote_id, status="refused_screening", price=None)
        # fire-and-forget refusal notice
        try:
            self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            # outcome and response unchanged
            pass
        return {"status": "refused_screening", "quote_id": quote_id}

    # ---- Internal helpers ----

    def _validate(self, request: Dict[str, Any]) -> (bool, str):
        """Validate the request against DT-V.

        Returns (is_valid, status). On success, status is unused; on failure,
        status is "rejected: invalid_request".
        """

        # Check presence and non-empty shipper_id
        if "shipper_id" not in request:
            return False, "rejected: invalid_request"
        shipper_id = request["shipper_id"]
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False, "rejected: invalid_request"

        # Helper to get numeric field and check bounds
        def check_numeric(name: str, minimum: float, maximum: float) -> Optional[float]:
            if name not in request:
                return None
            value = request[name]
            try:
                num = float(value)
            except (TypeError, ValueError):
                return None
            if not (minimum <= num <= maximum):
                return None
            return num

        # V2: weight_kg bounds
        if check_numeric("weight_kg", 3, 19400) is None:
            return False, "rejected: invalid_request"

        # V3: distance_km bounds
        if check_numeric("distance_km", 25, 7150) is None:
            return False, "rejected: invalid_request"

        # V4: declared_value bounds
        if check_numeric("declared_value", 50, 83000) is None:
            return False, "rejected: invalid_request"

        return True, "ok"


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level handle function per instructions.

    Creates default collaborator instances; test harnesses may patch the
    classes or their methods by name.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
