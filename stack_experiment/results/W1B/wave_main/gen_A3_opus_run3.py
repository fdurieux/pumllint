from typing import Any


class ScreeningService:
    """External denied-party screening provider returning a shipper risk index."""

    def screen(self, shipper_id: str, request: dict) -> Any:
        result = request.get("screening_result", request.get("screening_status"))
        if isinstance(result, str):
            low = result.strip().lower()
            if low in ("error", "unavailable", "down", "outage", "timeout"):
                return "screening_unavailable"
            try:
                return int(float(low))
            except ValueError:
                mapping = {
                    "accept": 10,
                    "approved": 10,
                    "review": 50,
                    "hold": 50,
                    "refuse": 90,
                    "refused": 90,
                    "declined": 90,
                }
                return mapping.get(low, 10)
        if isinstance(result, (int, float)):
            return int(result)
        return 10


class NotificationService:
    """External messaging provider delivering quote documents and refusal notices."""

    def sendQuoteDocument(self, shipper_id: str, quote_id: str, price: float) -> Any:
        return "sent"

    def sendRefusalNotice(self, shipper_id: str, quote_id: str) -> Any:
        return "sent"


class TariffEngine:
    """Computes the freight price from weight and distance per DT-P."""

    def price(self, weight_kg: float, distance_km: float) -> Any:
        result = 0.87 * weight_kg + 1.13 * distance_km  # P1
        if weight_kg > 1244:  # P2
            result += 316.00
        if distance_km >= 4912:  # P3
            result *= 1.19
        return round(result, 2)  # P4


class QuoteStore:
    """Stores quote requests and their lifecycle status."""

    def __init__(self) -> None:
        self._records: dict = {}
        self._counter = 0

    def storeDraft(self, shipper_id: str, weight_kg: float, distance_km: float,
                   declared_value: float, request: dict) -> Any:
        result = request.get("store_result", request.get("store_status"))
        if isinstance(result, str) and result.strip().lower() in (
            "error", "unavailable", "down", "fail", "failure"
        ):
            return "store_unavailable"
        self._counter += 1
        quote_id = f"Q{self._counter:06d}"
        self._records[quote_id] = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
        }
        return quote_id

    def updateQuote(self, quote_id: str, status: str, price: Any = None) -> Any:
        rec = self._records.get(quote_id)
        if rec is not None:
            rec["status"] = status
            if price is not None:
                rec["price"] = price
        return quote_id


# DT-S symbolic boundaries
ACCEPT_MAX = 41
REVIEW_MIN = 42
REVIEW_MAX = 66
REFUSE_MIN = 67


class QuoteApi:
    """Receives quote requests, validates, orchestrates screening and pricing."""

    def __init__(self, tariff_engine: TariffEngine, quote_store: QuoteStore,
                 screening_service: ScreeningService,
                 notification_service: NotificationService) -> None:
        self.tariff_engine = tariff_engine
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.notification_service = notification_service

    def _validate(self, request: dict) -> bool:
        shipper_id = request.get("shipper_id")
        if not isinstance(shipper_id, str) or shipper_id == "":  # V1
            return False
        weight_kg = request.get("weight_kg")
        if not isinstance(weight_kg, (int, float)) or isinstance(weight_kg, bool):
            return False
        if not (3 <= weight_kg <= 19400):  # V2
            return False
        distance_km = request.get("distance_km")
        if not isinstance(distance_km, (int, float)) or isinstance(distance_km, bool):
            return False
        if not (25 <= distance_km <= 7150):  # V3
            return False
        declared_value = request.get("declared_value")
        if not isinstance(declared_value, (int, float)) or isinstance(declared_value, bool):
            return False
        if not (50 <= declared_value <= 83000):  # V4
            return False
        return True

    def requestQuote(self, request: dict) -> dict:
        # Step 1: validate (DT-V)
        if not self._validate(request):
            return {"status": "rejected: invalid_request"}

        shipper_id = request["shipper_id"]
        weight_kg = request["weight_kg"]
        distance_km = request["distance_km"]
        declared_value = request["declared_value"]

        # Step 2: store draft
        quote_id = self.quote_store.storeDraft(
            shipper_id, weight_kg, distance_km, declared_value, request
        )
        if quote_id == "store_unavailable":
            return {"status": "error: store_unavailable"}

        # Step 3: screening
        risk_index = self.screening_service.screen(shipper_id, request)

        if risk_index == "screening_unavailable":
            # Screening outage: price anyway, hold, do not notify (DT-S note 5)
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "held_unscreened", price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }

        # Step 4/5/6: apply DT-S decision
        if risk_index <= ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.updateQuote(quote_id, "quoted", price)
            self.notification_service.sendQuoteDocument(shipper_id, quote_id, price)
            return {"status": "quoted", "quote_id": quote_id, "price": price}
        elif REVIEW_MIN <= risk_index <= REVIEW_MAX:
            self.quote_store.updateQuote(quote_id, "review_hold")
            return {"status": "review_hold", "quote_id": quote_id}
        else:  # risk_index >= REFUSE_MIN
            self.quote_store.updateQuote(quote_id, "refused_screening")
            self.notification_service.sendRefusalNotice(shipper_id, quote_id)
            return {"status": "refused_screening", "quote_id": quote_id}


def handle(request: dict) -> dict:
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    notification_service = NotificationService()
    api = QuoteApi(tariff_engine, quote_store, screening_service, notification_service)
    return api.requestQuote(request)