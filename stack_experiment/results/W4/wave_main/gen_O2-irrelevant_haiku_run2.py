import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str, screening_result: Optional[int] = None, 
               screening_status: Optional[str] = None) -> int:
        """
        Request shipper risk index from screening service.
        
        In test/mock mode, accepts screening_result or screening_status to simulate
        outcomes. In production, would call the real external service.
        
        Returns: risk_index (higher is worse)
        Raises: ScreeningUnavailableError if service is down
        """
        if screening_status == "unavailable":
            raise ScreeningUnavailableError("Screening service unavailable")
        if screening_result is not None:
            return screening_result
        # Default: low-risk shipper
        return 10


class ScreeningUnavailableError(Exception):
    pass


class TariffEngine:
    """Computes freight price from weight and distance per published tariff."""
    
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """
        Compute freight price (DT-P).
        
        P1: base = 0.87 * weight_kg + 1.13 * distance_km
        P2: if weight_kg > 1244, add 316.00 (flat)
        P3: if distance_km >= 4912, multiply by 1.19 (applied after P2)
        P4: round to 2 decimal places
        
        Returns: price amount (float)
        """
        base = Decimal(str(0.87 * weight_kg)) + Decimal(str(1.13 * distance_km))
        
        # P2: heavy surcharge
        if weight_kg > 1244:
            base += Decimal("316.00")
        
        # P3: long-haul multiplier (applied after P2)
        if distance_km >= 4912:
            base *= Decimal("1.19")
        
        # P4: round to 2 decimal places
        result = float(base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        return result


class QuoteStore:
    """PostgreSQL-backed quote record store."""
    
    def __init__(self):
        # In-memory store for testing; in production this is PostgreSQL
        self.quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float,
                    declared_value: float, store_status: Optional[str] = None) -> str:
        """
        Store a draft quote and return quote_id.
        
        Raises: StoreUnavailableError if storage fails
        """
        if store_status == "unavailable":
            raise StoreUnavailableError("Quote store unavailable")
        
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            "quote_id": quote_id,
            "shipper_id": shipper_id,
            "weight_kg": weight_kg,
            "distance_km": distance_km,
            "declared_value": declared_value,
            "status": "draft",
            "price": None,
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        """Update quote status and optionally price."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self.quotes[quote_id]["status"] = status
        if price is not None:
            self.quotes[quote_id]["price"] = price
        return self.quotes[quote_id]


class StoreUnavailableError(Exception):
    pass


class NotificationService:
    """External messaging provider for quote documents and refusal notices."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float,
                           notification_status: Optional[str] = None) -> str:
        """
        Fire-and-forget delivery of quote document.
        Delivery failure never changes the response.
        
        Returns: confirmation string
        Raises: (never; failures are silent per spec note 4)
        """
        if notification_status == "error":
            # Silent failure: never raises, never changes response
            return "delivery_attempted"
        return "delivered"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str,
                           notification_status: Optional[str] = None) -> str:
        """
        Fire-and-forget delivery of refusal notice.
        
        Returns: confirmation string
        """
        if notification_status == "error":
            # Silent failure: never raises, never changes response
            return "delivery_attempted"
        return "delivered"


class QuoteAPI:
    """Main orchestration service: validates, screens, prices, stores and notifies."""
    
    # DT-S risk thresholds
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def __init__(self, screening_service: ScreeningService, tariff_engine: TariffEngine,
                 quote_store: QuoteStore, notification_service: NotificationService):
        self.screening = screening_service
        self.tariff = tariff_engine
        self.store = quote_store
        self.notifier = notification_service
    
    def _validate_request(self, shipper_id: str, weight_kg: float, distance_km: float,
                         declared_value: float) -> bool:
        """
        Validate request per DT-V.
        
        V1: shipper_id present and non-empty
        V2: weight_kg in [3, 19400]
        V3: distance_km in [25, 7150]
        V4: declared_value in [50, 83000]
        
        Returns: True if valid, False otherwise
        """
        # V1
        if not shipper_id or not isinstance(shipper_id, str):
            return False
        # V2
        if not isinstance(weight_kg, (int, float)) or not (3 <= weight_kg <= 19400):
            return False
        # V3
        if not isinstance(distance_km, (int, float)) or not (25 <= distance_km <= 7150):
            return False
        # V4
        if not isinstance(declared_value, (int, float)) or not (50 <= declared_value <= 83000):
            return False
        return True
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float,
                     declared_value: float, screening_result: Optional[int] = None,
                     screening_status: Optional[str] = None,
                     store_status: Optional[str] = None,
                     notification_status: Optional[str] = None) -> dict:
        """
        Process a quote request end-to-end.
        
        Args:
            shipper_id, weight_kg, distance_km, declared_value: request fields
            screening_result: mock risk index (overrides screening call)
            screening_status: mock screening availability ("unavailable", etc.)
            store_status: mock store availability ("unavailable", etc.)
            notification_status: mock notification delivery ("error", etc.)
        
        Returns: response dict with status and optional quote_id, price, hold
        """
        
        # Step 1: Validate request (DT-V)
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {"status": "rejected: invalid_request"}
        
        # Step 2: Store draft quote
        try:
            quote_id = self.store.store_draft(shipper_id, weight_kg, distance_km,
                                             declared_value, store_status=store_status)
        except StoreUnavailableError:
            # On storage failure: stop, don't screen/price/notify (DT-S note 3)
            return {"status": "error: store_unavailable"}
        
        # Step 3: Request screening
        screening_unavailable = False
        risk_index = None
        try:
            risk_index = self.screening.screen(shipper_id, screening_result=screening_result,
                                               screening_status=screening_status)
        except ScreeningUnavailableError:
            screening_unavailable = True
        
        # Step 4 & 5 & 6 & 7: Apply screening decision (DT-S)
        
        if screening_unavailable:
            # DT-S note 5: screening outage does not fail quote
            # Price it, store as held_unscreened, don't notify
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "held_unscreened", price=price)
            return {
                "status": "held_unscreened",
                "quote_id": quote_id,
                "price": price,
                "hold": True,
            }
        
        # Screening succeeded: apply DT-S decision bands
        if risk_index <= self.ACCEPT_MAX:
            # DT-S row accept: price, store as quoted, notify with document
            price = self.tariff.price(weight_kg, distance_km)
            self.store.update_quote(quote_id, "quoted", price=price)
            self.notifier.send_quote_document(shipper_id, quote_id, price,
                                             notification_status=notification_status)
            return {
                "status": "quoted",
                "quote_id": quote_id,
                "price": price,
            }
        
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            # DT-S row review: don't price, store as review_hold, don't notify
            self.store.update_quote(quote_id, "review_hold")
            return {
                "status": "review_hold",
                "quote_id": quote_id,
            }
        
        elif risk_index >= self.REFUSE_MIN:
            # DT-S row refuse: don't price, store as refused_screening, notify refusal
            self.store.update_quote(quote_id, "refused_screening")
            self.notifier.send_refusal_notice(shipper_id, quote_id,
                                             notification_status=notification_status)
            return {
                "status": "refused_screening",
                "quote_id": quote_id,
            }


def handle(request: dict) -> dict:
    """
    End-to-end handler for a quote request.
    
    Expected request keys:
      - shipper_id, weight_kg, distance_km, declared_value: quote fields
      - screening_result (optional): risk index to return from screening
      - screening_status (optional): "unavailable" to simulate outage
      - store_status (optional): "unavailable" to simulate store failure
      - notification_status (optional): "error" to simulate notification failure
    
    Returns: response dict with status and optional quote_id, price, hold
    """
    
    # Extract request fields
    shipper_id = request.get("shipper_id")
    weight_kg = request.get("weight_kg")
    distance_km = request.get("distance_km")
    declared_value = request.get("declared_value")
    
    # Extract mock/test parameters
    screening_result = request.get("screening_result")
    screening_status = request.get("screening_status")
    store_status = request.get("store_status")
    notification_status = request.get("notification_status")
    
    # Instantiate collaborators
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    quote_store = QuoteStore()
    notification_service = NotificationService()
    
    # Instantiate orchestration service
    api = QuoteAPI(screening_service, tariff_engine, quote_store, notification_service)
    
    # Process request
    response = api.request_quote(
        shipper_id=shipper_id,
        weight_kg=weight_kg,
        distance_km=distance_km,
        declared_value=declared_value,
        screening_result=screening_result,
        screening_status=screening_status,
        store_status=store_status,
        notification_status=notification_status,
    )
    
    return response