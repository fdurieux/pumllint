"""Provider collectors: EODHD and Binance over a shared transport seam.

Importing this package does not import ``requests``; only constructing the
live ``HttpTransport`` does.
"""
from jef_data_rc.collectors.base import (
    SECRET_PARAMS,
    BaseCollector,
    CollectorError,
    DailyBudgetExhausted,
    HttpTransport,
    RateLimiter,
    RecordingTransport,
    ReplayTransport,
    TransportConnectionError,
    TransportResponse,
    public_params,
    request_key,
)

__all__ = [
    "SECRET_PARAMS",
    "BaseCollector",
    "CollectorError",
    "DailyBudgetExhausted",
    "HttpTransport",
    "RateLimiter",
    "RecordingTransport",
    "ReplayTransport",
    "TransportConnectionError",
    "TransportResponse",
    "public_params",
    "request_key",
]
