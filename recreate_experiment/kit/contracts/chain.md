# The daily chain: `deploy/daily.sh`

A bash script that drives the program once a day on the venue. Requirements:
JDL-146 … JDL-158. The two scripts it sources, `events.sh`
and `dashboard.sh`, are **given externals**: they are copied verbatim beside
the rebuilt `daily.sh` and are not part of what you rebuild. This contract
fixes only how `daily.sh` uses them. Revision 2026-10-24: the two files are
shipped in `contracts/externals/` (until then the kit named them and did
not carry them, found by the fourth rebuild); the chain scenarios copy them
from beside the script named by `JDL_CHAIN`, so put them there. One
constraint the scenarios' call logger imposes, met by the original: an
argument handed to a stubbed command is logged on one line, so a
`python3 -c` program is written on one physical line.

## 1. Invocation and environment

| variable | read by | meaning / default |
|---|---|---|
| `JEF_S3_BUCKET` | daily.sh, externals | required (inner run); the venue bucket name |
| `JEF_ASSETS` | daily.sh | space-separated asset names; default `AAPL BTC TLT NVDA TSLA IBM` |
| `JEF_IMAGE_DIGEST` | daily.sh | image provenance; computed when empty/unset (§2) |
| `ECS_CONTAINER_METADATA_URI_V4` | daily.sh | metadata endpoint base (default empty) |
| `JEF_TASK_VCPU`, `JEF_TASK_MEMORY_GB` | daily.sh (set-if-unset), externals' children | cost inputs |
| `JEF_RUN_STAMP` | daily.sh, events.sh | default `$(date -u +%Y-%m-%dT%H%M%SZ)` |
| `JEF_APP_DIR` | daily.sh | working directory for the run; default `/app` |
| `JEF_EVENT_DIR` | events.sh, dashboard.sh | default `/tmp/jef-events` |
| `JEF_DASH_DIR` | dashboard.sh | default `/tmp/jef-dashboard` |
| `EODHD_API_KEY` | the `jef-data` children | passed through untouched |

Shell variables set by daily.sh and read by the externals: `RUN_DATE`
(`$(date -u +%F)`), `STORE` (`data`), `STAGE`, `STAGE_T0`. Derived paths:
`OUT=out/${RUN_DATE}`, `DIAG=${OUT}/.diagnostics` (relative to JEF_APP_DIR).

The script runs under `set -euo pipefail`. External commands it calls
directly: `curl`, `python3` (metadata parsing only), `date`, `timeout`, `aws`,
`jef-data`, `jef-binning`, `tee`, `find`, `mkdir`, `dirname`. (The externals
additionally call `python3 -m jef.events`, `python3 -m jef.dashboard`,
`python3 -` and `aws`.)

## 2. Prologue (runs in every invocation, before the exec guard)

1. If `JEF_IMAGE_DIGEST` is empty/unset:
   * `_meta=$(curl -s "${ECS_CONTAINER_METADATA_URI_V4:-}/task" 2>/dev/null || true)`
   * digest = `Containers[0].ImageDigest` or else `Containers[0].ImageID` or
     else `unknown` from that JSON (any failure → `unknown`), parsed with
     `python3 -c`.
   * size = `Limits.CPU` and `Limits.Memory / 1024` (Python float division,
     e.g. 1024 → `1.0`); when parsing succeeds, `JEF_TASK_VCPU` and
     `JEF_TASK_MEMORY_GB` are set only if unset, and both are exported.
2. `export JEF_IMAGE_DIGEST`.
3. `JEF_RUN_STAMP` set if unset/empty (`date -u +%Y-%m-%dT%H%M%SZ`), exported.

## 3. Guards

4. **Exec guard**: `$# > 0` and `$1 != --inner` → `exec "$@"` (nothing else
   runs; no traps; exit code = the command's).
5. **Hard cap**: `$1 != --inner` → `exec timeout --signal=TERM --kill-after=60 3600 "$0" --inner`.
6. Inner run: `JEF_S3_BUCKET` empty/unset → bash's `${VAR:?msg}` failure
   (`…: JEF_S3_BUCKET: JEF_S3_BUCKET must name the venue bucket` on stderr),
   exit 1.

## 4. The inner run

7. `ASSETS` ← JEF_ASSETS (default list) split on whitespace; `RUN_DATE`,
   `STORE`, `OUT`.
8. Source `$(dirname "$0")/events.sh`, then `$(dirname "$0")/dashboard.sh`.
9. `cd "${JEF_APP_DIR:-/app}"`; print `== jef daily ${RUN_DATE} assets: ${ASSETS[*]}`;
   `mkdir -p "${DIAG}"`.
10. `trap '…' TERM` — `jef_emit "${STAGE:-unknown}" 143 "${STAGE_T0:-0}" "$(date +%s)"; jef_put "${STAGE:-unknown}"; exit 143`.
11. `trap 'jef_publish_dashboard' EXIT` (returns 0; the exit status is kept).
12. `aws s3 sync "s3://${JEF_S3_BUCKET}/store/" "data/" --only-show-errors`.
13. `FILTERS` = `--asset A` for each asset, in order.

### Stages (each: capture rc, emit, put, stop on non-zero)

| stage | command | emit extra args | put |
|---|---|---|---|
| `sync` | `jef-data sync ${FILTERS[@]} --store data --summary-json ${DIAG}/sync.json` | `--attach ${DIAG}/sync.json` when that file is non-empty | `jef_put sync` |
| `status` | `jef-data status ${FILTERS[@]} --store data --json \| tee ${DIAG}/status.json` (rc of the pipeline under pipefail) | `--attach ${DIAG}/status.json` when non-empty | `jef_put status` |
| `binning` | per asset A: `jef-binning --asset A --store data --counter-start latest --counter-end latest --output-dir ${OUT}/A` | per asset: `--asset A`, then when a manifest `M` = first `run_manifest*.json` directly in `${OUT}/A` exists: `--manifest M --manifest-root ${OUT} --manifest-prefix runs/${RUN_DATE}` (and before the emit `jef_manifest_keys M ${DIAG}/binning-A.json`), then `--attach ${DIAG}/binning-A.json` when non-empty | `jef_put binning` once after the loop |

Each stage sets `STAGE=<name>` and `STAGE_T0=$(date +%s)` first; each emit is
`jef_emit <stage> <rc> <t0> "$(date +%s)" [extra]` (binning: t0 per asset).
The binning loop stops at the first asset with a non-zero rc (that asset is
still emitted); the remaining assets do not run.

### Publish (green only)

14. `aws s3 sync "data/" "s3://${JEF_S3_BUCKET}/store/" --only-show-errors`
15. `aws s3 sync "${OUT}/" "s3://${JEF_S3_BUCKET}/runs/${RUN_DATE}/" --only-show-errors`
16. `echo "${JEF_IMAGE_DIGEST}" | aws s3 cp - "s3://${JEF_S3_BUCKET}/runs/${RUN_DATE}/image_digest.txt" --only-show-errors`
17. print `== green (${JEF_IMAGE_DIGEST})`; exit 0 (then the EXIT trap).

## 5. The externals' interface (given; do not rebuild)

| function | used as | what it does (for orientation only) |
|---|---|---|
| `jef_emit STAGE RC T0 T1 [args…]` | after each stage / per binning asset / in the TERM trap | runs `python3 -m jef.events emit --stage STAGE --rc RC --t0 T0 --t1 T1 --run-date ${RUN_DATE} --out ${JEF_EVENT_DIR}/${JEF_RUN_STAMP}-STAGE.jsonl [args…]`; always returns 0 |
| `jef_put STAGE` | after each stage | when the stage's `.jsonl` is non-empty: `aws s3 cp <file> s3://${JEF_S3_BUCKET}/events/v1/<file name> --only-show-errors`, else prints a WARN; returns 0 |
| `jef_attach_if_present PATH` | in `$(…)` unquoted, as emit args | prints `--attach` and PATH on two lines when PATH is non-empty |
| `jef_manifest_keys M OUT` | binning, when a manifest exists | writes join keys from M to OUT (or nothing, with a WARN); returns 0 |
| `jef_publish_dashboard` | EXIT trap | when `data/market_data` exists: syncs the ledger down, runs `python3 -m jef.dashboard publish …`, uploads the page; else prints `WARN: no store at data/market_data, dashboard publish skipped`; returns 0 |

## 6. Outcomes

| situation | exit code | uploads |
|---|---|---|
| override arguments | the command's | none |
| bucket missing | 1 | none |
| store restore fails | aws's rc | dashboard (EXIT trap) |
| sync rc ≠ 0 | sync's rc | sync ledger object, dashboard |
| status rc ≠ 0 (alerts) | status's rc | sync + status ledger objects, dashboard |
| binning rc ≠ 0 | that asset's rc | ledger objects of all three stages, dashboard |
| all green | 0 | ledger objects, store, runs, image digest, dashboard |
| TERM during a stage | 143 | that stage's ledger object, dashboard |
