"""EOD acquisition, local-store, adjustment and health subsystem.

The package root is deliberately small: it exposes only the seven-column
contract check. Store, sync, collector and health APIs live in their own
submodules and are not imported here, so ``import jef_data_rc`` loads
neither pyarrow nor requests.
"""
from jef_data_rc.contract import (
    ContractError,
    ContractReport,
    validate,
    validate_or_raise,
)

__all__ = ["ContractError", "ContractReport", "validate", "validate_or_raise"]
