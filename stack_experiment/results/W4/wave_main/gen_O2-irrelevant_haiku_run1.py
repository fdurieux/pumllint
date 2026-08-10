import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

# Constants from DT-S (screening decision boundaries)
ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67

# Validation bounds from DT-V
WEIGHT_MIN = 3
WEIGHT_MAX = 19400
DISTANCE_MIN = 25
DISTANCE_MAX = 7150
DECLARED_VALUE_MIN = 50
DECLARED_VALUE_MAX = 83000


class QuoteStore:
    """PostgreSQL 16 quote store — stores quote requests and lifecycle status."""

    def __init__(self):
        self.quotes = {}

    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, declared_value: float) -> str:
        """Store a draft quote; return quote_id."""
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id

    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> str:
        """Update quote status and optionally price; return quote_id."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        return quote_id


class TariffEngine:
    """Tariff engine — computes freight price from weight and distance per DT-P."""

    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute price per DT-P (P1–P4). Return price as float."""
        # P1: base = 0.87 * weight_kg + 1.13 * distance_km
        base = Decimal(str(0.87 * weight_kg + 1.13 * distance_km))

        # P2: heavy surcharge if weight_kg > 1244, add 316.00 flat
        if weight_kg > 1244:
            base += Decimal("316.00")

        # P3: long-haul multiplier if distance_km >= 4912, multiply by 1.19
        # (applied AFTER P2)
        if distance_km >= 4912:
            base = base * Decimal("1.19")

        # P4: round to 2 decimal places
        price = base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return float(price)


class ScreeningService:
    """External denied-party screening provider — returns risk index."""

    def screen(self, shipper_id: str) -> int:
        """Request shipper risk index. Return risk index (higher is worse)."""
        # This is an external system; the request dict supplies the result via screening_result key
        raise NotImplementedError("Screening service called but result not provided in request")


class NotificationService:
    """External messaging provider — delivers quote documents and refusal notices."""

    def send_quote_document(self, shipper_id: str, quote_id: str, price: float) -> str:
        """Send quote document to shipper; fire-and-forget. Return confirmation."""
        # External system; request dict supplies outcome via notification_status key
        raise NotImplementedError("Notification service called but result not provided in request")

    def send_refusal_notice(self, shipper_id: str, quote_id: str) -> str:
        """Send refusal notice to shipper; fire-and-forget. Return confirmation."""
        # External system; request dict supplies outcome via notification_status key
        raise NotImplementedError("Notification service called but result not provided in request")


class QuoteAPI:
    """Quote API orchestrates validation, screening, pricing, storage and notification."""

    def __init__(self, quote_store: QuoteStore, tariff_engine: TariffEngine,
                 screening_service: ScreeningService, notification_service: NotificationService):
        self.quote_store = quote_store
        self.tariff_engine = tariff_engine
        self.screening_service = screening_service
        self.notification_service = notification_service

    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float,
                      declared_value: float, screening_result: Optional[int] = None,
                      screening_status: Optional[str] = None, notification_status: Optional[str] = None) -> dict:
        """
        Request a freight quote. Orchestrate validation, storage, screening, pricing, notification.
        Return response dict with status and optional fields (quote_id, price, hold).
        """
        # Step 1: Validate request per DT-V
        validation_error = self._validate_request(shipper_id, weight_kg, distance_km, declared_value)
        if validation_error:
            return {"status": validation_error}

        # Step 2: Store draft
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km, declared_value)
        except Exception:
            return {"status": "error: store_unavailable"}

        # Step 3: Request screening
        risk_index = None
        screening_unavailable = False
        if screening_status == "unavailable":
            screening_unavailable = True
        elif screening_result is not None:
            risk_index = screening_result
        else:
            # Normal case: call screening service (but in tests it's mocked via screening_result)
            try:
                risk_index = self.screening_service.screen(shipper_id)
            except Exception:
                screening_unavailable = True

        # Step 4: Apply screening decision (DT-S) or handle outage
        if screening_unavailable:
            # Screening outage: price anyway, store as held_unscreened, do not notify
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Normal screening path: apply DT-S decision
        if risk_index <= ACCEPT_MAX:
            # Accept: price and notify
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, "quoted", price)
            # Notify (fire-and-forget)
            try:
                self.notification_service.send_quote_document(shipper_id, quote_id, price)
            except Exception:
                # Notification failure never changes response (DT-S note 4)
                pass
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            # Review: hold without pricing or notification
            self.quote_store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        else:  # risk_index >= REFUSE_MIN
            # Refuse: notify but do not price
            self.quote_store.update_quote(quote_id, "refused_screening")
            # Notify (fire-and-forget)
            try:
                self.notification_service.send_refusal_notice(shipper_id, quote_id)
            except Exception:
                # Notification failure never changes response
                pass
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }

    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float,
                          declared_value: float) -> Optional[str]:
        """Validate per DT-V. Return error string if invalid, None if valid."""
        # V1: shipper_id present and non-empty
        if not shipper_id:
            return "rejected: invalid_request"
        # V2: weight_kg in range
        if not isinstance(weight_kg, (int, float)) or weight_kg < WEIGHT_MIN or weight_kg > WEIGHT_MAX:
            return "rejected: invalid_request"
        # V3: distance_km in range
        if not isinstance(distance_km, (int, float)) or distance_km < DISTANCE_MIN or distance_km > DISTANCE_MAX:
            return "rejected: invalid_request"
        # V4: declared_value in range
        if not isinstance(declared_value, (int, float)) or declared_value < DECLARED_VALUE_MIN or declared_value > DECLARED_VALUE_MAX:
            return "rejected: invalid_request"
        return None


def handle(request: dict) -> dict:
    """
    Run one end-to-end quotation flow. Request carries scenario input:
    entity ids and amounts, existence flags, and external system outcomes.
    Return dict with status key naming the outcome.
    """
    # Extract request fields
    shipper_id = request.get("shipper_id", "")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")

    # Extract external system outcomes from request (test injection)
    screening_result = request.get("screening_result")
    screening_status = request.get("screening_status")
    notification_status = request.get("notification_status")

    # Instantiate system components
    quote_store = QuoteStore()
    tariff_engine = TariffEngine()
    screening_service = ScreeningService()
    notification_service = NotificationService()

    quote_api = QuoteAPI(quote_store, tariff_engine, screening_service, notification_service)

    # Run the quotation flow
    response = quote_api.request_quote(
        shipper_id=shipper_id,
        weight_kg=weight_kg,
        distance_km=distance_km,
        declared_value=declared_value,
        screening_result=screening_result,
        screening_status=screening_status,
        notification_status=notification_status,
    )

    return response