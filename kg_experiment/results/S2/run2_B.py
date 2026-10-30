from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable for an operation."""


class ScreeningUnavailableError(Exception):
    """Raised when the screening service is unavailable or cannot return a risk index."""


class QuoteStore:
    """Persistence layer for quotes.

    The real implementation would interact with a database. Here we only
    define the interface expected by QuoteAPI so that test harnesses can
    stub or monkeypatch these methods.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a new draft quote and return its identifier.

        May raise StoreUnavailableError on failure.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote's status and optional price.

        May raise StoreUnavailableError on failure.
        """

        raise NotImplementedError


class TariffEngine:
    """Pricing engine implementing DT-P."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute price according to DT-P.

        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00
        P3: if distance_km >= 4912, multiply running total by 1.19
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
        """Return the integer risk index for the shipper.

        May raise ScreeningUnavailableError on outage.
        """

        raise NotImplementedError


class NotificationService:
    """External notification provider wrapper."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send the quote document (fire-and-forget semantics)."""

        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send the refusal notice (fire-and-forget semantics)."""

        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # Public entry point used by the top-level handle(request)
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a quote request according to CargoQuote specification.

        Implements validation (DT-V), draft storage, screening (DT-S),
        pricing (DT-P), notification, and error handling as specified.
        """

        # 1. Validate the request (DT-V). Invalid → reject, stop.
        if not self._is_valid_request(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = str(request["shipper_id"])
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
            # On storage failure: return error and do nothing else.
            return {"status": "error: store_unavailable"}

        # 3. Request the shipper's risk index from the Screening Service.
        # ScreeningUnavailableError is intentionally not caught here,
        # as behaviour is not specified (REQ-06 / OD-1).
        risk_index = self.screening_service.screen(shipper_id)

        # 4. Apply the screening decision (DT-S) to the risk index.
        if risk_index <= 41:
            status = "quoted"
            priced = True
            notified = "quote_document"
        elif 42 <= risk_index <= 66:
            status = "review_hold"
            priced = False
            notified = "none"
        else:  # risk_index >= 67
            status = "refused_screening"
            priced = False
            notified = "refusal_notice"

        response: Dict[str, Any] = {"status": status, "quote_id": quote_id}

        # 5. Price the quote (DT-P) — only on priced rows.
        price: Optional[float] = None
        if priced:
            price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)
            response["price"] = price

        # 4 (continued). Update the stored quote to the resulting status,
        # including price if present. Update failures are not specified,
        # so we allow StoreUnavailableError to propagate.
        self.quote_store.update_quote(quote_id=quote_id, status=status, price=price)

        # 6. Notify the shipper — only on the rows DT-S marks notified;
        # fire-and-forget: exceptions are swallowed.
        try:
            if notified == "quote_document" and price is not None:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            elif notified == "refusal_notice":
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
        except Exception:
            # Explicitly ignore any notification failures.
            pass

        # 7. Return the response.
        return response

    # Internal helpers
    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Validate request according to DT-V.

        Returns True if valid, False otherwise.
        """

        # Required keys
        required_keys = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for key in required_keys:
            if key not in request:
                return False

        shipper_id = request["shipper_id"]
        if not isinstance(shipper_id, str) or not shipper_id:
            return False

        # Numeric bounds with basic type coercion and validation
        try:
            weight_kg = float(request["weight_kg"])
            distance_km = float(request["distance_km"])
            declared_value = float(request["declared_value"])
        except (TypeError, ValueError):
            return False

        if not (3 <= weight_kg <= 19400):
            return False
        if not (25 <= distance_km <= 7150):
            return False
        if not (50 <= declared_value <= 83000):
            return False

        return True


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Top-level function expected by the harness.

    Instantiates real collaborators; in tests these classes/methods can
    be stubbed or monkeypatched by name.
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
