import uuid
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP


class QuoteStore:
    """PostgreSQL 16 quote store."""
    
    def __init__(self):
        self.quotes = {}
    
    def store_draft(self, shipper_id: str, weight_kg: float, distance_km: float, 
                   declared_value: float) -> str:
        """Store a draft quote and return its ID."""
        quote_id = str(uuid.uuid4())
        self.quotes[quote_id] = {
            'shipper_id': shipper_id,
            'weight_kg': weight_kg,
            'distance_km': distance_km,
            'declared_value': declared_value,
            'status': 'draft',
            'price': None
        }
        return quote_id
    
    def update_quote(self, quote_id: str, status: str, price: Optional[float] = None) -> dict:
        """Update a stored quote with status and optional price."""
        if quote_id not in self.quotes:
            raise ValueError(f"Quote {quote_id} not found")
        self.quotes[quote_id]['status'] = status
        if price is not None:
            self.quotes[quote_id]['price'] = price
        return self.quotes[quote_id]


class ScreeningService:
    """External denied-party screening provider."""
    
    def screen(self, shipper_id: str, screening_result: Optional[int] = None, 
              screening_status: Optional[str] = None) -> int:
        """Request shipper risk index. Return value is always a single integer."""
        if screening_status == "unavailable":
            raise Exception("Screening service unavailable")
        if screening_result is not None:
            return screening_result
        return 0


class TariffEngine:
    """Tariff computation engine."""
    
    def price(self, weight_kg: float, distance_km: float) -> float:
        """Compute freight price per DT-P."""
        base = Decimal(str(0.87 * weight_kg + 1.13 * distance_km))
        
        if weight_kg > 1244:
            base += Decimal('316.00')
        
        if distance_km >= 4912:
            base *= Decimal('1.19')
        
        result = float(base.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        return result


class NotificationService:
    """External messaging provider."""
    
    def send_quote_document(self, shipper_id: str, quote_id: str, price: float,
                           notification_status: Optional[str] = None) -> str:
        """Send quote document (fire-and-forget). Always returns a single value."""
        if notification_status == "error":
            return "failed"
        return "sent"
    
    def send_refusal_notice(self, shipper_id: str, quote_id: str,
                           notification_status: Optional[str] = None) -> str:
        """Send refusal notice (fire-and-forget). Always returns a single value."""
        if notification_status == "error":
            return "failed"
        return "sent"


class QuoteAPI:
    """Quote API orchestrator."""
    
    ACCEPT_MAX = 41
    REVIEW_MIN = 42
    REVIEW_MAX = 66
    REFUSE_MIN = 67
    
    def __init__(self, quote_store: QuoteStore, screening_service: ScreeningService,
                 tariff_engine: TariffEngine, notification_service: NotificationService):
        self.quote_store = quote_store
        self.screening_service = screening_service
        self.tariff_engine = tariff_engine
        self.notification_service = notification_service
    
    def _validate_request(self, shipper_id: str, weight_kg: float, 
                         distance_km: float, declared_value: float) -> bool:
        """Validate request per DT-V."""
        if not shipper_id or not isinstance(shipper_id, str) or len(shipper_id) == 0:
            return False
        if not isinstance(weight_kg, (int, float)) or weight_kg < 3 or weight_kg > 19400:
            return False
        if not isinstance(distance_km, (int, float)) or distance_km < 25 or distance_km > 7150:
            return False
        if not isinstance(declared_value, (int, float)) or declared_value < 50 or declared_value > 83000:
            return False
        return True
    
    def request_quote(self, shipper_id: str, weight_kg: float, distance_km: float,
                     declared_value: float, screening_result: Optional[int] = None,
                     screening_status: Optional[str] = None,
                     notification_status: Optional[str] = None) -> dict:
        """Handle quote request per the flow specification."""
        
        if not self._validate_request(shipper_id, weight_kg, distance_km, declared_value):
            return {'status': 'rejected: invalid_request'}
        
        try:
            quote_id = self.quote_store.store_draft(shipper_id, weight_kg, distance_km,
                                                     declared_value)
        except Exception:
            return {'status': 'error: store_unavailable'}
        
        screening_unavailable = False
        try:
            risk_index = self.screening_service.screen(shipper_id, screening_result,
                                                       screening_status)
        except Exception:
            screening_unavailable = True
        
        if screening_unavailable:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, 'held_unscreened', price)
            return {
                'status': 'held_unscreened',
                'quote_id': quote_id,
                'price': price,
                'hold': True
            }
        
        if risk_index <= self.ACCEPT_MAX:
            price = self.tariff_engine.price(weight_kg, distance_km)
            self.quote_store.update_quote(quote_id, 'quoted', price)
            self.notification_service.send_quote_document(shipper_id, quote_id, price,
                                                         notification_status)
            return {
                'status': 'quoted',
                'quote_id': quote_id,
                'price': price
            }
        elif self.REVIEW_MIN <= risk_index <= self.REVIEW_MAX:
            self.quote_store.update_quote(quote_id, 'review_hold')
            return {
                'status': 'review_hold',
                'quote_id': quote_id
            }
        elif risk_index >= self.REFUSE_MIN:
            self.quote_store.update_quote(quote_id, 'refused_screening')
            self.notification_service.send_refusal_notice(shipper_id, quote_id,
                                                         notification_status)
            return {
                'status': 'refused_screening',
                'quote_id': quote_id
            }


def handle(request: dict) -> dict:
    """
    Run one end-to-end quotation flow.
    
    request keys:
    - shipper_id: string
    - weight_kg: number
    - distance_km: number
    - declared_value: number
    - screening_result: optional int (risk index)
    - screening_status: optional str ("unavailable" triggers exception)
    - notification_status: optional str ("error" simulates failure)
    - store_status: optional str ("unavailable" simulates store failure)
    
    Returns: dict with 'status' and optional 'quote_id', 'price', 'hold'.
    """
    quote_store = QuoteStore()
    screening_service = ScreeningService()
    tariff_engine = TariffEngine()
    notification_service = NotificationService()
    quote_api = QuoteAPI(quote_store, screening_service, tariff_engine, 
                        notification_service)
    
    shipper_id = request.get('shipper_id', '')
    weight_kg = request.get('weight_kg')
    distance_km = request.get('distance_km')
    declared_value = request.get('declared_value')
    screening_result = request.get('screening_result')
    screening_status = request.get('screening_status')
    notification_status = request.get('notification_status')
    store_status = request.get('store_status')
    
    if store_status == 'unavailable':
        return {'status': 'error: store_unavailable'}
    
    return quote_api.request_quote(
        shipper_id=shipper_id,
        weight_kg=weight_kg,
        distance_km=distance_km,
        declared_value=declared_value,
        screening_result=screening_result,
        screening_status=screening_status,
        notification_status=notification_status
    )