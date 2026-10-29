"""Provider collectors (EODHD, Binance) over a pluggable transport."""
from jef_data_rc.collectors.base import (BaseCollector, CollectorError, DailyBudgetExhausted,
                                         HttpTransport, RateLimiter, RecordingTransport,
                                         ReplayTransport, TransportConnectionError,
                                         TransportResponse)

VOLUME_BASIS = {"eodhd": "split_adjusted", "binance": "raw"}

__all__ = ["BaseCollector", "CollectorError", "DailyBudgetExhausted", "HttpTransport",
           "RateLimiter", "RecordingTransport", "ReplayTransport", "TransportConnectionError",
           "TransportResponse", "VOLUME_BASIS"]
