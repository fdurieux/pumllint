"""EOD acquisition, local-store, adjustment and health subsystem.

The package root is deliberately small: it exposes only the seven-column
contract check. Store, sync, collector and health APIs live in their own
submodules; the store-loading seam on the consumer side is
`jef.binning.loading`, which stays storage-agnostic.
"""

from jef_data_rc.contract import ContractError, ContractReport, validate, validate_or_raise

__all__ = ["ContractError", "ContractReport", "validate", "validate_or_raise"]
