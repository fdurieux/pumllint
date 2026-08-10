from __future__ import annotations


class Shipper:
    """A logistics customer requesting a price quote."""

    def __init__(self, shipper_id: str):
        self.shipper_id = shipper_id

    def request_quote(self, quote_api: "QuoteApi", request: dict) -> dict:
        return quote_api.submit_quote(request)


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def request_risk_index(self, shipper_id: str, request: dict) -> float:
        if "screening_result" in request or "screening_status" in request:
            raw = request.get("screening_result", request.get("screening_status"))
            if isinstance(raw, (int, float)):
                return float(raw)
            word = str(raw).lower()
            if word in ("approved", "clear", "active"):
                return 10.0
            if word in ("review", "assessed", "hold"):
                return 60.0
            if word in ("declined", "denied", "blocked"):
                return 90.0
            if word == "error":
                raise RuntimeError("screening_error")
        return 10.0


class TariffEngine:
    """Computes the freight price from weight and distance per tariff rules."""

    BASE_FEE = 25.0
    RATE_PER_KG = 0.5
    RATE_PER_KM = 0.8
    VALUE_SURCHARGE = 0.002

    def compute_price(self, weight: float, distance: float, declared_value: float) -> float:
        price = (
            self.BASE_FEE
            + weight * self.RATE_PER_KG
            + distance * self.RATE_PER_KM
            + declared_value * self.VALUE_SURCHARGE
        )
        return round(price, 2)


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self):
        self._records: dict = {}
        self._counter = 0

    def store_request(self, request: dict) -> str:
        self._counter += 1
        quote_id = f"Q-{self._counter:06d}"
        self._records[quote_id] = {"request": request, "status": "recorded"}
        return quote_id

    def update_status(self, quote_id: str, status: str) -> str:
        if quote_id in self._records:
            self._records[quote_id]["status"] = status
        return quote_id


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def send(self, shipper_id: str, document: dict) -> str:
        return f"delivered:{shipper_id}"


class QuoteApi:
    """Receives quote requests, validates them, orchestrates screening and
    pricing, and returns the quotation outcome."""

    ISSUE_THRESHOLD = 50.0
    REFUSE_THRESHOLD = 80.0

    def __init__(self, tariff_engine=None, quote_store=None,
                 screening_service=None, notification_service=None):
        self.tariff_engine = tariff_engine or TariffEngine()
        self.quote_store = quote_store or QuoteStore()
        self.screening_service = screening_service or ScreeningService()
        self.notification_service = notification_service or NotificationService()

    def _validate(self, request: dict) -> None:
        shipper_id = request.get("shipper_id")
        if not shipper_id:
            raise ValueError("missing_shipper")
        if request.get("shipper_exists") is False or request.get("shipper_found") is False:
            raise ValueError("unknown_shipper")
        for field in ("weight", "distance", "declared_value"):
            value = request.get(field)
            if value is None:
                raise ValueError(f"missing_{field}")
            if not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(f"invalid_{field}")

    def submit_quote(self, request: dict) -> dict:
        try:
            self._validate(request)
        except ValueError as exc:
            return {"status": f"error: {exc}"}

        shipper_id = request["shipper_id"]

        # Record the request
        quote_id = self.quote_store.store_request(request)

        # Screen the shipper
        try:
            risk_index = self.screening_service.request_risk_index(shipper_id, request)
        except Exception as exc:
            self.quote_store.update_status(quote_id, "screening_failed")
            return {"status": f"error: {exc}", "quote_id": quote_id}

        # Refused
        if risk_index >= self.REFUSE_THRESHOLD:
            self.quote_store.update_status(quote_id, "refused")
            self.notification_service.send(
                shipper_id, {"type": "refusal_notice", "quote_id": quote_id}
            )
            return {
                "status": "rejected",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }

        # Held for manual review
        if risk_index >= self.ISSUE_THRESHOLD:
            self.quote_store.update_status(quote_id, "manual_review")
            return {
                "status": "held",
                "quote_id": quote_id,
                "risk_index": risk_index,
            }

        # Issue immediately
        price = self.tariff_engine.compute_price(
            request["weight"], request["distance"], request["declared_value"]
        )
        self.quote_store.update_status(quote_id, "issued")
        self.notification_service.send(
            shipper_id,
            {"type": "quote_document", "quote_id": quote_id, "price": price},
        )
        return {
            "status": "confirmed",
            "quote_id": quote_id,
            "price": price,
            "risk_index": risk_index,
        }


def handle(request: dict) -> dict:
    api = QuoteApi()
    shipper = Shipper(request.get("shipper_id", ""))
    try:
        return shipper.request_quote(api, request)
    except Exception as exc:
        return {"status": f"error: {exc}"}