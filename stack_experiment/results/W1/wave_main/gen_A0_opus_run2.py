from typing import Any, Dict


class DeniedPartyScreeningProvider:
    """External denied-party screening provider (outside system boundary)."""

    def screen(self, shipper_id: str, hints: Dict[str, Any]) -> Any:
        # Returns a single value: the shipper risk index (number) or a word.
        if "screening_result" in hints and hints["screening_result"] is not None:
            return hints["screening_result"]
        if "screening_status" in hints and hints["screening_status"] is not None:
            return hints["screening_status"]
        # Plausible default: low risk.
        return 10


class TariffEngine:
    """Prices a consignment against the company tariff."""

    BASE_FEE = 25.0
    RATE_PER_KG_KM = 0.0009
    VALUE_SURCHARGE = 0.004

    def price(self, weight: float, distance: float, declared_value: float) -> float:
        amount = (
            self.BASE_FEE
            + self.RATE_PER_KG_KM * weight * distance
            + self.VALUE_SURCHARGE * declared_value
        )
        return round(amount, 2)


class QuoteStore:
    """Persists quote requests and issued quotes."""

    def __init__(self):
        self._records = {}
        self._seq = 0

    def record(self, quote: Dict[str, Any]) -> str:
        # Returns a single confirmation reference.
        self._seq += 1
        ref = "Q-%05d" % self._seq
        self._records[ref] = dict(quote)
        return ref


class NotificationProvider:
    """External notification provider that delivers documents to shippers."""

    def notify(self, shipper_id: str, document: Dict[str, Any]) -> str:
        # Returns a single delivery confirmation.
        return "delivered:%s" % shipper_id


class ValidationError(Exception):
    pass


class QuoteService:
    """Orchestrates the synchronous quotation flow."""

    # Screening risk-index thresholds.
    ISSUE_MAX = 30
    REVIEW_MAX = 70

    def __init__(self, screening=None, tariff=None, store=None, notifier=None):
        self.screening = screening or DeniedPartyScreeningProvider()
        self.tariff = tariff or TariffEngine()
        self.store = store or QuoteStore()
        self.notifier = notifier or NotificationProvider()

    def _validate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        shipper_id = request.get("shipper_id")
        if not shipper_id:
            raise ValidationError("missing_shipper")

        exists = request.get("shipper_exists", request.get("shipper_found", True))
        if not exists:
            raise ValidationError("unknown_shipper")

        try:
            weight = float(request.get("weight", 0))
            distance = float(request.get("distance", 0))
            declared_value = float(request.get("declared_value", 0))
        except (TypeError, ValueError):
            raise ValidationError("invalid_amounts")

        if weight <= 0:
            raise ValidationError("invalid_weight")
        if distance <= 0:
            raise ValidationError("invalid_distance")
        if declared_value < 0:
            raise ValidationError("invalid_value")

        return {
            "shipper_id": shipper_id,
            "weight": weight,
            "distance": distance,
            "declared_value": declared_value,
        }

    def _classify(self, risk: Any) -> str:
        # Map screening outcome to a decision: issue / review / refuse.
        if isinstance(risk, str):
            word = risk.strip().lower()
            if word in ("approved", "clear", "clean", "active"):
                return "issue"
            if word in ("declined", "denied", "match", "blocked"):
                return "refuse"
            if word in ("assessed", "review", "hold", "manual"):
                return "review"
            if word == "error":
                raise RuntimeError("screening_error")
            try:
                risk = float(word)
            except ValueError:
                return "review"
        try:
            score = float(risk)
        except (TypeError, ValueError):
            return "review"
        if score < self.ISSUE_MAX:
            return "issue"
        if score < self.REVIEW_MAX:
            return "review"
        return "refuse"

    def quote(self, request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            data = self._validate(request)
        except ValidationError as exc:
            return {"status": "error: %s" % exc}

        # Record the incoming request.
        ref = self.store.record({"type": "request", **data})

        # Screen the shipper.
        try:
            risk = self.screening.screen(data["shipper_id"], request)
            decision = self._classify(risk)
        except RuntimeError as exc:
            return {"status": "error: %s" % exc, "reference": ref}

        if decision == "refuse":
            document = {
                "type": "refusal",
                "shipper_id": data["shipper_id"],
                "reference": ref,
            }
            self.store.record(document)
            self.notifier.notify(data["shipper_id"], document)
            return {
                "status": "rejected",
                "reference": ref,
                "reason": "screening_refused",
            }

        if decision == "review":
            self.store.record(
                {
                    "type": "held",
                    "shipper_id": data["shipper_id"],
                    "reference": ref,
                }
            )
            return {
                "status": "review",
                "reference": ref,
                "reason": "manual_review",
            }

        # Issue: price and deliver the quote document.
        price = self.tariff.price(
            data["weight"], data["distance"], data["declared_value"]
        )
        document = {
            "type": "quote",
            "shipper_id": data["shipper_id"],
            "reference": ref,
            "price": price,
        }
        confirmation = self.store.record(document)
        self.notifier.notify(data["shipper_id"], document)
        return {
            "status": "confirmed",
            "reference": confirmation,
            "price": price,
        }


def handle(request: dict) -> dict:
    service = QuoteService()
    return service.quote(request)