# Assumptions and specification issues

Input baseline: `88f656a39f47fe92a31e887e26888775658aa19b`.
Findings and their score impacts live in `INPUT-QUALITY.md` and `input-quality.json`.

1. **A-01 / F-001 — Inventory authority.** Use the actual 163 requirement records, rather than the kit README's stale count of 162.
2. **A-02 / F-002 — Excluded verification tools.** DONE checks reference harness tools outside the permitted inputs. Do not access them. Independently derived checks do not count as execution of those exact gates.
3. **A-03 / F-003 — Missing chain externals.** The supplied suite copies sibling externals, contrary to the handover's statement that it stubs them. Leave production externals absent; any independently constructed test doubles must live under tests and their use must be labelled in results. This cannot establish equivalence with the missing original externals.
4. **A-04 / F-004 — Refusal identity.** Distinguish the two X-10 rows by requirement and condition; do not change required runtime messages.
5. **A-05 / F-005 — Future actions stamps.** Follow JDL-091's comparison: on or after today means fresh. The DMN model's input domain lacks a future-stamp value.
6. **A-06 / F-007 — Default snapshots.** Ship packaged universe bytes unchanged. Its experiment CSV paths remain external prerequisites; do not retrieve excluded files to supply them.
7. **A-07 / F-008 — Transport shape.** Use the prose tuple `(status, text)` seam rather than the UML's response-object notation.
8. **A-08 — Empty provider response.** A zero-bar collector call creates no market-data files or lock unless re-adjustment of an existing raw series is required. An empty CSV overwrite takes the lock and prunes existing years.
9. **A-09 — Duplicate incoming timestamps.** Store keeps first timestamps on overwrite and append. Provider collectors already deduplicate. Direct low-level duplicate reconcile input is outside the documented provider flow.
10. **A-10 — Numeric status knob range.** Apart from the specified sync tail minimum, preserve parser-accepted numeric values without inventing range refusals; behaviour of negative windows is ordinary slicing, and is not claimed semantically useful.
11. **A-11 — Evaluation uncertainty.** Baseline quality scores are provisional ordinal judgements. Fixture bytes are structurally inspected; independent truth of all synthetic expected cells and external vendor facts is not asserted. Derived artefacts contribute comprehension, not independent behavioural evidence.
12. **A-12 / F-009 — Chain logger representation.** Keep metadata Python `-c` arguments on one physical line, with escaped internal newlines, because the supplied recording stub does not escape multiline arguments. This avoids a false call-list difference without changing metadata behaviour.
