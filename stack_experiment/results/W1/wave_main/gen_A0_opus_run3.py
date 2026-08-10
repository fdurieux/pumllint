from typing import Any, Dict


class ScreeningProvider:
    """External denied-party screening provider (outside system boundary)."""

    def screen(self, shipper_id: str, override: Any = None) -> float:
        if override is not None:
            if isinstance(override, (int, float)):
                return float(override)
            word = str(override).lower()
            mapping = {
                "approved": 5.0,
                "active": 5.0,
                "clear": 5.0,
                "assessed": 45.0,
                "review": 45.0,
                "declined": 90.0,
                "denied": 90.0,
                "error": -1.0,
            }
            if word in mapping:
                return mapping[word]
            try:
                return float(word)
            except ValueError:
                return 5.0
        return 5.0


class TariffEngine:
    """Prices a consignment against the company tariff."""

    BASE_FEE = 25.0
    PER_KG = 0.85
    PER_KM = 0.12
    VALUE_RATE = 0.005

    def price(self, weight_kg: float, distance_km: float, declared_value: float) -> float:
        amount = (
            self.BASE_FEE
            + weight_kg * self.PER_KG
            + distance_km * self.PER_KM
            + declared_value * self.VALUE_RATE
        )
        return round(amount, 2)


class QuoteStore:
    """Persists quote requests and outcomes."""

    def __init__(self) -> None:
        self._records: Dict[str, Dict[str, Any]] = {}
        self._counter = 0

    def save(self, record: Dict[str, Any]) -> str:
        self._counter += 1
        confirmation = "QUO-{:06d}".format(self._counter)
        self._records[confirmation] = dict(record)
        return confirmation

    def update(self, confirmation: str, record: Dict[str, Any]) -> str:
        self._records[confirmation] = dict(record)
        return confirmation


class NotificationProvider:
    """External notification provider (outside system boundary)."""

    def notify(self, shipper_id: str, document: str) -> str:
        return "delivered"


class QuoteService:
    """Orchestrates the synchronous quotation flow."""

    HOLD_THRESHOLD = 30.0
    REFUSE_THRESHOLD = 70.0

    def __init__(
        self,
        screening: ScreeningProvider,
        tariff: TariffEngine,
        store: QuoteStore,
        notifier: NotificationProvider,
    ) -> None:
        self.screening = screening
        self.tariff = tariff
        self.store = store
        self.notifier = notifier

    def validate(self, request: Dict[str, Any]) -> None:
        shipper_id = request.get("shipper_id") or request.get("shipper")
        if not shipper_id:
            raise ValueError("missing_shipper")
        exists = request.get("shipper_exists", request.get("shipper_found", True))
        if not exists:
            raise ValueError("unknown_shipper")
        for field in ("weight_kg", "distance_km", "declared_value"):
            value = request.get(field)
            if value is None:
                raise ValueError("missing_" + field)
            try:
                number = float(value)
            except (TypeError, ValueError):
                raise ValueError("invalid_" + field)
            if number <= 0:
                raise ValueError("invalid_" + field)

    def quote(self, request: Dict[str, Any]) -> Dict[str, Any]:
        self.validate(request)

        shipper_id = request.get("shipper_id") or request.get("shipper")
        weight_kg = float(request["weight_kg"])
        distance_km = float(request["distance_km"])
        declared_value = float(request["declared_value"])

        record = {
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "state": "recorded",
        }
        confirmation = self.store.save(record)

        override = request.get("screening_result", request.get("screening_status"))
        risk_index = self.screening.screen(shipper_id, override)

        if risk_index < 0:
            record["state"] = "error"
            self.store.update(confirmation, record)
            raise RuntimeError("screening_unavailable")

        if risk_index >= self.REFUSE_THRESHOLD:
            record["state"] = "refused"
            record["risk_index"] = risk_index
            self.store.update(confirmation, record)
            self.notifier.notify(shipper_id, "refusal_notice:" + confirmation)
            return {
                "status": "rejected",
                "quote_id": confirmation,
                "risk_index": risk_index,
            }

        if risk_index >= self.HOLD_THRESHOLD:
            record["state"] = "manual_review"
            record["risk_index"] = risk_index
            self.store.update(confirmation, record)
            return {
                "status": "held",
                "quote_id": confirmation,
                "risk_index": risk_index,
            }

        price = self.tariff.price(weight_kg, distance_km, declared_value)
        record["state"] = "issued"
        record["risk_index"] = risk_index
        record["price"] = price
        self.store.update(confirmation, record)
        self.notifier.notify(shipper_id, "quote_document:" + confirmation)
        return {
            "status": "confirmed",
            "quote_id": confirmation,
            "price": price,
            "risk_index": risk_index,
        }


def handle(request: dict) -> dict:
    service = QuoteService(
        ScreeningProvider(),
        TariffEngine(),
        QuoteStore(),
        NotificationProvider(),
    )
    try:
        return service.quote(request)
    except (ValueError, RuntimeError) as exc:
        return {"status": "error: " + str(exc)}
    except Exception as exc:  # pragma: no cover
        return {"status": "error: " + str(exc)}