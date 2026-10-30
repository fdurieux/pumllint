"""Required keys per task class (pre-registration §6), frozen."""

CODEGEN_KEYS = [
    # DT-V
    "shipper_id|present", "weight_kg|min", "weight_kg|max", "distance_km|min", "distance_km|max",
    "declared_value|min", "declared_value|max", "invalid_request|behaviour",
    # DT-S rows
    "S-accept|max", "S-accept|priced", "S-accept|notified", "S-accept|status",
    "S-review|min", "S-review|max", "S-review|priced", "S-review|notified", "S-review|status",
    "S-refuse|min", "S-refuse|priced", "S-refuse|notified", "S-refuse|status",
    # notes 3-5 as behaviours
    "QuoteAPI|on_store_failure", "QuoteAPI|on_notification_failure", "QuoteAPI|on_screening_outage",
    # DT-P
    "P1|formula", "P2|threshold", "P2|surcharge", "P3|threshold", "P3|factor", "P3|order", "P4|rounding",
    # flow and response
    "flow|order", "response|statuses", "response|price_presence", "response|hold_presence",
    "response|quote_id_presence",
]

TASKS = {
    "codegen": {
        "keys": CODEGEN_KEYS,
        "block_levels": {"absent", "declared_gap", "disputed", "invalidated"},
        "max_unverified_share": 0.25,
    },
}
