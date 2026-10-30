from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised when the Quote Store is unavailable for storing or updating quotes."""


class ScreeningUnavailableError(Exception):
    """Raised when the Screening Service is unavailable or cannot return a risk index."""


class QuoteStore:
    """Persistence collaborator for quote drafts and updates.

    In this experiment, the concrete storage is not implemented; tests are
    expected to stub or monkeypatch these methods.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a new draft quote and return its quote_id.

        May raise StoreUnavailableError on storage failure.
        """
        raise NotImplementedError

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> None:
        """Update an existing quote's status and optional price.

        May raise StoreUnavailableError on storage failure.
        """
        raise NotImplementedError


class TariffEngine:
    """Pricing engine implementing DT-P and REQ-08."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        # DT-P P1: base = 0.87 * weight_kg + 1.13 * distance_km
        base = 0.87 * weight_kg + 1.13 * distance_km
        # DT-P P2: heavy surcharge if weight_kg > 1244, add 316.00
        if weight_kg > 1244:
            base += 316.00
        # DT-P P3 / REQ-08: long-haul multiplier if distance_km >= 4912, multiply by 1.19
        if distance_km >= 4912:
            base *= 1.19
        # DT-P P4: round to 2 decimal places
        return round(base, 2)


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id: str) -> int:
        """Return an integer risk index for the given shipper.

        May raise ScreeningUnavailableError on outage.
        """
        raise NotImplementedError


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send a quote document to the shipper.

        Delivery failures must not affect the outcome or response; any
        exceptions from an implementation should be swallowed by callers.
        """
        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice to the shipper.

        Delivery failures must not affect the outcome or response; any
        exceptions from an implementation should be swallowed by callers.
        """
        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # ---- Public entrypoint used by handle() ----
    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a quote request according to the CargoQuote specification.

        This function implements the orchestration described in spec.md and
        decision_table.md, respecting DT-V, DT-S, and DT-P.
        """
        # 1. Validate the request (DT-V). Invalid → reject, stop.
        valid = self._validate_request(request)
        if not valid:
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
            # REQ-05 / DT-S note 3: storage failure → error, nothing else runs
            return {"status": "error: store_unavailable"}

        # 3. Request the shipper's risk index from the Screening Service.
        # Behaviour on ScreeningUnavailableError is explicitly unspecified (REQ-06);
        # per assumptions, we let it propagate.
        risk_index_raw = self.screening_service.screen(shipper_id)
        # Coerce to int per assumption
        risk_index = int(risk_index_raw)

        # 4. Apply the screening decision (DT-S) to the risk index. Update stored quote.
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

        # For all DT-S rows, we first update the stored quote status (without price yet).
        # Any StoreUnavailableError here is treated as unexpected and propagated per assumptions.
        if status == "quoted":
            # For quoted, we will store price after computing it, so initial update is deferred
            pass
        else:
            # review_hold or refused_screening without price
            self.quote_store.update_quote(quote_id=quote_id, status=status, price=None)

        response: Dict[str, Any] = {"status": status, "quote_id": quote_id}

        # 5. Price the quote (DT-P) — only on the rows DT-S marks priced (accept row).
        if priced:
            price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)
            # Update stored quote with final status and price
            self.quote_store.update_quote(quote_id=quote_id, status=status, price=price)
            response["price"] = price

        # 6. Notify the shipper — only on the rows DT-S marks notified; fire-and-forget.
        if notified == "quote_document":
            try:
                # quote document sent on accept row
                self.notification_service.send_quote_document(
                    shipper_id=shipper_id,
                    quote_id=quote_id,
                    price=response["price"],
                )
            except Exception:
                # Fire-and-forget: swallow any exception; outcome/response unchanged.
                pass
        elif notified == "refusal_notice":
            try:
                self.notification_service.send_refusal_notice(
                    shipper_id=shipper_id,
                    quote_id=quote_id,
                )
            except Exception:
                # Fire-and-forget: swallow any exception; outcome/response unchanged.
                pass

        # 7. Return the response.
        return response

    # ---- Internal helpers ----

    def _validate_request(self, request: Dict[str, Any]) -> bool:
        """Validate request fields against DT-V.

        Returns True if valid, False otherwise.
        """
        required_fields = ["shipper_id", "weight_kg", "distance_km", "declared_value"]
        for field in required_fields:
            if field not in request:
                return False

        shipper_id = request["shipper_id"]
        if not isinstance(shipper_id, str) or shipper_id == "":
            return False

        # Numeric bounds with strict type checking (int or float)
        numeric_fields = ["weight_kg", "distance_km", "declared_value"]
        for field in numeric_fields:
            value = request[field]
            if not isinstance(value, (int, float)):
                return False

        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        if not (3 <= weight_kg <= 19400):
            return False
        if not (25 <= distance_km <= 7150):
            return False
        if not (50 <= declared_value <= 83000):
            return False

        return True


# Module-level handle for the harness

def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    """Module-level handle function delegating to QuoteAPI.

    This constructs default collaborator instances that tests can replace
    via monkeypatching classes and methods by name.
    """
    api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return api.handle(request)
