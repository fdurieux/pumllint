from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


class StoreUnavailableError(Exception):
    """Raised by QuoteStore when storage is unavailable."""


class ScreeningUnavailableError(Exception):
    """Raised by ScreeningService when screening is unavailable (outage)."""


class QuoteStore:
    """Persistence layer for quotes.

    In this implementation, methods are stubs to be overridden or mocked
    in a test harness.
    """

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote and return its quote_id.

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
        P3: if distance_km >= 4912, multiply running total by 1.19 (after P2)
        P4: price = round(result, 2)
        """

        base = 0.87 * weight_kg + 1.13 * distance_km
        if weight_kg > 1244:
            base += 316.00
        if distance_km >= 4912:
            base *= 1.19
        price = round(base, 2)
        return price


class ScreeningService:
    """External screening service returning a risk index for a shipper."""

    def screen(self, shipper_id: str) -> int:
        """Return the risk index for the given shipper.

        May raise ScreeningUnavailableError on outage.
        """

        raise NotImplementedError


class NotificationService:
    """External notification service for quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> None:
        """Send a quote document to the shipper.

        Fire-and-forget: any delivery failure should not change outcome/response.
        """

        raise NotImplementedError

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> None:
        """Send a refusal notice to the shipper.

        Fire-and-forget: any delivery failure should not change outcome/response.
        """

        raise NotImplementedError


@dataclass
class QuoteAPI:
    quote_store: QuoteStore
    tariff_engine: TariffEngine
    screening_service: ScreeningService
    notification_service: NotificationService

    # --- Public entry point ---

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a quote request according to the CargoQuote specification.

        The request dict must contain shipper_id, weight_kg, distance_km, declared_value.
        Returns a response dict with at least a status key.
        """

        # 1. Validate request (DT-V). Invalid -> reject, stop. (spec.md Flow order 1)
        if not self._is_valid_request(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        # 2. Store draft quote with status draft. On failure: error: store_unavailable, stop.
        try:
            quote_id = self.quote_store.store_draft(
                shipper_id=shipper_id,
                weight_kg=weight_kg,
                distance_km=distance_km,
                declared_value=declared_value,
            )
        except StoreUnavailableError:
            return {"status": "error: store_unavailable"}

        # 3. Request risk index from Screening Service.
        # Behaviour on screening outage is not specified (REQ-06); we propagate.
        risk_index = self.screening_service.screen(shipper_id)

        # 4. Apply DT-S to risk_index and update stored quote status.
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

        price: Optional[float] = None

        # 5. Price the quote (DT-P) — only if priced is True.
        if priced:
            price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)

        # Update quote with final status (and price if any).
        # StoreUnavailableError here is treated as unexpected and propagated.
        if price is not None:
            self.quote_store.update_quote(quote_id=quote_id, status=status, price=price)
        else:
            self.quote_store.update_quote(quote_id=quote_id, status=status)

        # 6. Notify the shipper — only on notified rows; fire-and-forget.
        if notified == "quote_document":
            if price is None:
                # Defensive: per DT-S, this should not happen, but avoid crashing notification.
                computed_price = self.tariff_engine.price(weight_kg=weight_kg, distance_km=distance_km)
            else:
                computed_price = price
            try:
                self.notification_service.send_quote_document(
                    shipper_id=shipper_id,
                    quote_id=quote_id,
                    price=computed_price,
                )
            except Exception:
                # Fire-and-forget semantics: ignore any delivery failure.
                pass
        elif notified == "refusal_notice":
            try:
                self.notification_service.send_refusal_notice(
                    shipper_id=shipper_id,
                    quote_id=quote_id,
                )
            except Exception:
                # Fire-and-forget semantics: ignore any delivery failure.
                pass

        # 7. Return the response.
        response: Dict[str, Any] = {"status": status, "quote_id": quote_id}
        if price is not None:
            response["price"] = price
        return response

    # --- Internal helpers ---

    def _is_valid_request(self, request: Dict[str, Any]) -> bool:
        """Validate the request against DT-V bounds.

        A request is valid iff all DT-V rules V1..V4 hold.
        """

        # V1: shipper_id present and non-empty string
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or not shipper_id:
            return False

        # Helper to check numeric field within bounds
        def _check_number(field: str, min_value: float, max_value: float) -> bool:
            if field not in request:
                return False
            value = request[field]
            if not isinstance(value, (int, float)):
                return False
            return min_value <= float(value) <= max_value

        # V2: weight_kg number, 3 <= weight_kg <= 19400
        if not _check_number("weight_kg", 3, 19400):
            return False

        # V3: distance_km number, 25 <= distance_km <= 7150
        if not _check_number("distance_km", 25, 7150):
            return False

        # V4: declared_value number, 50 <= declared_value <= 83000
        if not _check_number("declared_value", 50, 83000):
            return False

        return True


# Module-level handle function required by the harness.

def handle(request: Dict[str, Any]) -> Dict[str, Any]:
    quote_api = QuoteAPI(
        quote_store=QuoteStore(),
        tariff_engine=TariffEngine(),
        screening_service=ScreeningService(),
        notification_service=NotificationService(),
    )
    return quote_api.handle(request)
