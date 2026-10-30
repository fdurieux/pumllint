from dataclasses import dataclass
from typing import Any, Dict


class StoreUnavailableError(Exception):
    """Raised when the quote store is unavailable for draft storage or updates."""


class ScreeningUnavailableError(Exception):
    """Raised when the screening service is unavailable (screening outage)."""


class QuoteStore:
    """Persistence adapter for quote records.

    The concrete implementation is out of scope; tests may stub these methods.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

        May raise StoreUnavailableError if storage is not available.
        """

        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: float | None = None) -> None:
        """Update an existing quote's status and optionally its price.

        May raise StoreUnavailableError on failure (behavior then is unspecified
        by the provided documents and thus not handled specially here).
        """

        raise NotImplementedError


class TariffEngine:
    """Tariff calculation implementing DT-P pricing rules."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # P1: base = 0.87 * weight_kg + 1.13 * distance_km
        base = 0.87 * weight_kg + 1.13 * distance_km
        # P2: heavy surcharge
        if weight_kg > 1244:
            base += 316.00
        # P3: long-haul multiplier after P2
        if distance_km >= 4912:
            base *= 1.19
        # P4: round to 2 decimals
        return round(base, 2)


class ScreeningService:
    """External denied-party screening provider."""

    def screen(self, shipper_id: str) -> int:
        """Return an integer risk index for the given shipper.

        May raise ScreeningUnavailableError on outage.
        """

        raise NotImplementedError


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send a quote document to the shipper.

        Delivery failures are modeled as exceptions but must not affect
        the outcome of handle(); such exceptions are caught and ignored.
        """

        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice to the shipper.

        Delivery failures are modeled as exceptions but must not affect
        the outcome of handle(); such exceptions are caught and ignored.
        """

        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # Public entry point used by module-level handle()
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Validate request (DT-V). Invalid -> reject, stop.
        valid, parsed_or_error = self._validate(request)
        if not valid:
            # parsed_or_error carries error marker; spec only needs status field.
            return {"status": "rejected: invalid_request"}

        shipper_id = parsed_or_error["shipper_id"]
        weight_kg = parsed_or_error["weight_kg"]
        distance_km = parsed_or_error["distance_km"]
        declared_value = parsed_or_error["declared_value"]

        # 2. Store draft quote with status draft.
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

        # From here on, a draft was stored; responses must include quote_id.
        # 3. Request risk index from Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Screening outage: price anyway, update to held_unscreened,
            # no notification, response includes price and hold: true.
            price = self.tariff_engine.price(weight_kg, distance_km)
            # Update quote status with computed price. Any StoreUnavailableError
            # here is not specified by the documents and is allowed to propagate.
            self.quote_store.update_quote(quote_id, status="held_unscreened", price=price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # 4. Apply screening decision DT-S to risk_index.
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

        # 5. Price the quote only if priced.
        price_value: float | None = None
        if priced:
            price_value = self.tariff_engine.price(weight_kg, distance_km)
            response["price"] = price_value

        # 4 + 5 (continued). Update stored quote to resulting status, with price if any.
        self.quote_store.update_quote(quote_id, status=status, price=price_value)

        # 6. Notify the shipper where DT-S says so; fire-and-forget.
        if notified == "quote_document" and price_value is not None:
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price_value)
            except Exception:
                # Fire-and-forget: ignore delivery failure.
                pass
        elif notified == "refusal_notice":
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                # Fire-and-forget: ignore delivery failure.
                pass
        # review path: no notification

        # 7. Return the response.
        return response

    def _validate(self, request: Dict[str, Any]) -> tuple[bool, Dict[str, Any]]:
        """Validate incoming request against DT-V.

        Returns (True, parsed_fields) on success, (False, {}) on failure.
        """

        required_fields = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for field in required_fields:
            if field not in request:
                return False, {}

        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id.strip() == "":
            return False, {}

        # Helper to coerce numeric and check bounds
        def _num_in_range(key: str, minimum: float, maximum: float) -> float | None:
            value = request.get(key)
            try:
                num = float(value)
            except (TypeError, ValueError):
                return None
            if num < minimum or num > maximum:
                return None
            return num

        weight_kg = _num_in_range("weight_kg", 3, 19400)
        if weight_kg is None:
            return False, {}

        distance_km = _num_in_range("distance_km", 25, 7150)
        if distance_km is None:
            return False, {}

        declared_value = _num_in_range("declared_value", 50, 83000)
        if declared_value is None:
            return False, {}

        return (
            True,
            {
                "shipper_id": shipper_id,
                "weight_kg": weight_kg,
                "distance_km": distance_km,
                "declared_value": declared_value,
            },
        )


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level handle function delegating to QuoteAPI.

    Collaborator instances are created here so a test harness can stub
    them by class and method name.
    """

    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
