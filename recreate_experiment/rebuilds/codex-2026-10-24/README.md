# Independent jef-data recreation

Recreates the specified `jef` 0.6.0 package, ten-command `jef-data` CLI,
`deploy/daily.sh`, and import-only `jdl_adapter.py` from the pinned handover
and kit. Includes an input-quality assessment for every supplied artefact.

## Current result

| Validation | Result |
|---|---|
| Supplied acceptance cases with missing shell externals replaced by explicitly labelled test doubles | **257 passed, 0 failed, 0 skipped** |
| Additional independent checks (including 80 generated fixed-point/effective arithmetic examples) | **11 passed** |
| Unchanged supplied suite with production deployment directory | **246 passed, 11 setup failures**, all caused by the missing external scripts |
| Independent DMN checks | 63 rules across 13 tables; unique matches over declared finite domains and sampled nonnegative integer thresholds |
| Package | Installs; wheel builds; resources byte-identical; four exact runtime pins verified |
| Packaged-universe dry run | Nine legs planned, exit 0 |

**The exact handover completion gate is not yet satisfied.** The permitted
inputs omit `events.sh` and `dashboard.sh`, which are described as supplied
externals that must not be recreated. The suite copies those files; it does
not supply them. Put the owner's supplied originals beside `deploy/daily.sh`
to run the unqualified integration check. This recreation deliberately does
not manufacture production versions. Test doubles under `tests/externals/`
exist only to exercise the chain's orchestration through the supplied
recording stubs; they are not replacements for production use.

## Independence and provenance

Behavioural inputs: only `recreate_experiment/kit/` and
`recreate_experiment/handover/` at commit
`88f656a39f47fe92a31e887e26888775658aa19b`.
All 221 input files were checked against their pinned Git blob hashes.
Repository tree/branch metadata was inspected for placement and publishing.
No prior recreation source, reference implementation, hidden tests, or prior
experiment outcomes were read, imported, or used. No external behavioural
research was performed. Network access was used to retrieve permitted files,
install pinned dependencies/test tools, and publish the work.

The first diagnostic test run caught an extra newline introduced by local
file materialization. All local input bytes were corrected to the pinned Git
blobs before final verification; no source-kit edits were made. Raw initial
logs are retained and labelled diagnostic, not final evidence.

Authoring model: `gpt-6.1-sol-wm`; actual reasoning-effort setting unverified.
Environment used: CPython 3.12.14, Linux, Bash/GNU timeout. No subagents.
The recommended model/effort is documented in `EVALUATION-METHOD.md`, but
recommendation is not evidence of the active effort setting.

## Install and validate

From the repository root, create a dedicated environment (do not install a
prior recreation's identically named package in it):

```bash
python3.12 -m venv /tmp/jef-recreation-venv
source /tmp/jef-recreation-venv/bin/activate
pip install -e recreate_experiment/rebuilds/codex-2026-10-24
pip install -r recreate_experiment/rebuilds/codex-2026-10-24/requirements-test.txt
```

Run the available offline validation, explicitly substituting the missing
shell externals:

```bash
python recreate_experiment/rebuilds/codex-2026-10-24/run_validation.py --with-test-doubles --independent
python recreate_experiment/rebuilds/codex-2026-10-24/tests/check_decisions.py
```

Once the original external scripts have been supplied:

```bash
python recreate_experiment/rebuilds/codex-2026-10-24/run_validation.py
```

The runner uses the unchanged sibling kit and never imports prior builds.
Its test-double option stages only this recreation's chain and the labelled
doubles in a temporary directory. Omit the option for the production-external
gate. The runner does not silently skip missing inputs.

The packaged default universe contains CSV paths outside the allowed input
set; those snapshots must be supplied at deployment. Offline planning works:

```bash
jef-data sync --universe recreate_experiment/kit/contracts/universe.toml --store /tmp/jef-smoke --dry-run
```

## Module layout

- `src/jef/data/universe.py`: strict parsing, validation order and selection.
- `collectors.py`: provider clients, HTTP/replay/recording transports, quotas,
  retries, hygiene and pagination.
- `store.py`: actions files, locked atomic year writes, adjustment, append,
  reconcile, overwrite, import and export.
- `sync.py`: fetch windows, actions gates, leg isolation and summaries.
- `health.py`: declared-class evidence, source checks and venue pairs.
- `contract.py`: seam validation and relative differential reports.
- `parser.py`, `cli.py`: declared parser and command dispatch.
- `deploy/daily.sh`: chain guards, stages, TERM handling and publish gate.

`build_parser.py` materializes parser declarations from the allowed contract
at build-authoring time; the installed package has no runtime dependency on
the kit or generated evaluation records.

## Quality and evidence records

- `EVALUATION-METHOD.md`: protocol recorded before implementation.
- `INPUT-QUALITY.md`: per-artefact scores/comments and set-level assessment.
- `input-quality.json`: preserved baseline scores, final scores, confidence,
  hashes, contributions, findings and trace links for all 221 inputs.
- `ASSUMPTIONS.md`: **12** explicit decisions/gaps and their implementation
  consequences; gaps are never silently resolved.
- `requirement-trace.json`: all **163** requirements linked to module files
  and tagged scenario declarations. Static trace is not measured code coverage.
- `validation/`: full test logs/JUnit records, environment, packaging,
  decision checks, dry-run output, and a runtime-source hash manifest.

`review_inputs.py` created the baseline before implementation;
`finalize_review.py` joins evidence into the readable/JSON final assessment.
They are review tooling, not runtime dependencies. Archived baseline scores
remain in the JSON. Artefact usefulness is an observed role in this one
build, not a proven causal percentage improvement. Unknown semantic truth or
individual contribution remains explicitly unscored.

Five consequential interpretation decisions:

1. Store seconds in `timestamp`, while keeping millisecond UTC `datetime`.
2. Use declared class for sync basis/actions even when `.CC` suggests otherwise;
   the hand-run `load` declaration has its own namespace refusal.
3. Inject the run clock into windows/gates, while actions stamps use real UTC.
4. Preserve volume raw-ized with the earlier split knowledge outside refreshed
   tails; later adjustment must re-derive from those stored raw cells.
5. Preserve unguarded pandas failures for absent exports/differentials, and
   qualify chain results when the specified externals are unavailable.

## Limits

No live provider, real AWS bucket, Python 3.11, or original-external
integration was exercised. Additional tests use fake clocks/transports and
controlled temporary stores. The excluded optional harness tools and its
invariants were not run; independently derived checks are not claimed to be
those gates. SVGs were structurally consumed but not visually reviewed, and
full handover regeneration was not executed. The valid packaged
classification file is parsed; an arbitrary alternate-file validator is not
exposed. There is no line/branch coverage claim, full independent market-data
truth verification, or controlled artefact ablation study.

Reproducing the intentional quirks is conformance; passing synthetic examples
is not proof of universal semantic correctness. Remaining input gaps and
score qualifications are retained rather than concealed by a green run with
test substitutes.
