from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised by QuoteStore when storage is unavailable."""


class ScreeningUnavailableError(Exception):
    """Raised by ScreeningService when screening cannot be performed."""


@dataclass
class QuoteRecord:
    quote_id: str
    shipper_id: str
    weight_kg: float
    distance_km: float
    declared_value: float
    status: str
    price: Optional[float] = None


class QuoteStore:
    """Persistence boundary for quotes.

    Methods are specified to raise StoreUnavailableError on storage failures.
    """

    def store_draft(
        self,
        shipper_id: str,
        weight_kg: float,
        distance_km: float,
        declared_value: float,
    ) -> str:
        """Store a new draft quote and return its quote_id.

        May raise StoreUnavailableError if storage is unavailable.
        """

        # Minimal in-memory stub implementation; real systems will override.
        # Using id(self) is just to produce a deterministicish identifier.
        return f"q-{id(self)}"

    def update_quote(
        self,
        quote_id: str,
        status: str,
        price: Optional[float] = None,
    ) -> None:
        """Update an existing quote's status and optional price.

        May raise StoreUnavailableError if storage is unavailable.
        """

        # Stub: real implementations will persist the update.
        return None


class TariffEngine:
    """Computes the freight price per DT-P."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # P1: base
        base = 0.87 * weight_kg + 1.13 * distance_km
        # P2: heavy surcharge
        if weight_kg > 1244:
            base += 316.00
        # P3: long-haul multiplier
        if distance_km >= 4912:
            base *= 1.19
        # P4: round to 2 decimals
        return round(base, 2)


class ScreeningService:
    """External denied-party screening provider.

    screen may raise ScreeningUnavailableError on outage conditions.
    """

    def screen(self, shipper_id: str) -> int:
        """Return risk_index for the given shipper.

        May raise ScreeningUnavailableError if screening is unavailable.
        """

        # Stub: real implementation would call external service.
        return 0


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        # Fire-and-forget: errors should not affect response.
        return None

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        # Fire-and-forget: errors should not affect response.
        return None


class QuoteAPI:
    """Implements the CargoQuote quotation flow as per specification."""

    def __init__(
        self,
        quote_store: Optional[QuoteStore] = None,
        tariff_engine: Optional[TariffEngine] = None,
        screening_service: Optional[ScreeningService] = None,
        notification_service: Optional[NotificationService] = None,
    ) -> None:
        self.quote_store = quote_store or QuoteStore()
        self.tariff_engine = tariff_engine or TariffEngine()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    def _validate(self, request: Dict[str, Any]) -> bool:
        """Validate request per DT-V.

        Returns True if valid, False otherwise.
        """

        # V1: shipper_id present and non-empty
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or not shipper_id:
            return False

        # V2: weight_kg number, 3 <= weight_kg <= 19400
        if "weight_kg" not in request:
            return False
        weight = request["weight_kg"]
        if not isinstance(weight, (int, float)):
            return False
        if not (3 <= float(weight) <= 19400):
            return False

        # V3: distance_km number, 25 <= distance_km <= 7150
        if "distance_km" not in request:
            return False
        distance = request["distance_km"]
        if not isinstance(distance, (int, float)):
            return False
        if not (25 <= float(distance) <= 7150):
            return False

        # V4: declared_value number, 50 <= declared_value <= 83000
        if "declared_value" not in request:
            return False
        declared_value = request["declared_value"]
        if not isinstance(declared_value, (int, float)):
            return False
        if not (50 <= float(declared_value) <= 83000):
            return False

        return True

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point: orchestrates validation, storage, screening, pricing, and notification."""

        # 1. Validate the request (DT-V). Invalid -> reject, stop.
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

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
            # If storage fails: return error and stop (no screening, no price, no notification).
            return {"status": "error: store_unavailable"}

        # 3. Request the shipper's risk index from the Screening Service.
        try:
            risk_index = self.screening_service.screen(shipper_id)
        except ScreeningUnavailableError:
            # Assumed policy: treat outage as refusal to avoid quoting unscreened shippers.
            status = "refused_screening"
            try:
                self.quote_store.update_quote(quote_id, status=status, price=None)
            except StoreUnavailableError:
                # Specification is silent on update failures; allow exception to propagate.
                raise

            # Notify refusal, fire-and-forget: swallow any errors.
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass

            return {"status": status, "quote_id": quote_id}

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

        if priced:
            # 5. Price the quote (DT-P) — only on priced rows.
            price = self.tariff_engine.price(weight_kg, distance_km)
            try:
                self.quote_store.update_quote(quote_id, status=status, price=price)
            except StoreUnavailableError:
                # Behaviour not specified; propagate as an operational error.
                raise
            response["price"] = price
        else:
            # Update stored quote to the resulting status without a price.
            try:
                self.quote_store.update_quote(quote_id, status=status, price=None)
            except StoreUnavailableError:
                raise

        # 6. Notify the shipper — only on the rows DT-S marks notified; fire-and-forget.
        if notified == "quote_document":
            try:
                # price must be present in response when quoted & priced.
                self.notification_service.send_quote_document(
                    shipper_id, quote_id, response["price"]
                )
            except Exception:
                # Fire-and-forget: ignore failures.
                pass
        elif notified == "refusal_notice":
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                pass

        # 7. Return the response.
        return response


_quote_api_singleton = QuoteAPI()


def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level handle function delegating to QuoteAPI for the harness."""

    return _quote_api_singleton.handle(request)
