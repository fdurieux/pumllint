# Wave 2, layer 1 — property-based invariants through the harness adapter

Hypothesis generates provider responses (bar series with zero-volume rows and
dropped non-positive closes, split events with realistic ratios, dividends),
universe files and clocks; every property runs through the adapter named by
`JDL_ADAPTER`, so the same file checks the original and any rebuild.

    # intrinsic properties on one implementation
    JDL_ADAPTER=adapters.original PYTHONPATH=harness pytest harness/invariants -q
    # differential: the implementation under test against a reference
    JDL_ADAPTER=adapter_rc JDL_REF_ADAPTER=adapters.original PYTHONPATH=harness:<rc out> pytest harness/invariants -q

No float tolerance anywhere: identities are recomputed with the same operations
and differential checks are exact. Hypothesis is a lab-only dependency
(installed in the lab venvs, never in a kit's pins). `derandomize=True`, so a
run is reproducible; `max_examples` is 100 per property unless `JDL_EXAMPLES`
says otherwise.
