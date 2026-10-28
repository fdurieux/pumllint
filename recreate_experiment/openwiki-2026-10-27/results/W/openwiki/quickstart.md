---
type: quickstart
title: JEF Data Layer Quickstart
description: Task-routing guide for safely changing, operating, or verifying the JEF EOD data layer through its supported CLI and lightweight Python contract interface.
tags: [quickstart, jef-data, data-layer, eod, operations, verification]
verified:
  - by: openwiki/0.7.2
    at: 2026-10-28T09:59:03.506Z
sources:
  - id: openwiki-source-ec9bde4e4dac5e86ea9e9241
    resource: repo://deploy/daily.sh
  - id: openwiki-source-2ea8b51eb906e6ec42d1d6f1
    resource: repo://deploy/EXTERNALS.md
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
  - id: openwiki-source-66d9a84517d39a737a0f89ff
    resource: repo://src/jef/data/__init__.py
  - id: openwiki-source-d12b92a8129cb78f43aafcb4
    resource: repo://src/jef/data/__main__.py
  - id: openwiki-source-471ff7423bb268c6424d97b0
    resource: repo://src/jef/data/adjust.py
  - id: openwiki-source-7aef9869bf4f71025f82b7e0
    resource: repo://src/jef/data/cli.py
  - id: openwiki-source-87c07f77ae74915eb60c1e02
    resource: repo://src/jef/data/collectors/base.py
  - id: openwiki-source-78baa03aa35d8e1f36c6a783
    resource: repo://src/jef/data/collectors/eodhd.py
  - id: openwiki-source-bd47ee5fb9bed4bd3364a1bd
    resource: repo://src/jef/data/contract.py
  - id: openwiki-source-aa860d5c54a02851270df361
    resource: repo://src/jef/data/differential.py
  - id: openwiki-source-b83e6a16a28b8b0313c622c1
    resource: repo://src/jef/data/health.py
  - id: openwiki-source-eefe369117cf6763052e337a
    resource: repo://src/jef/data/store.py
  - id: openwiki-source-ba177959c236211872f717aa
    resource: repo://src/jef/data/sync.py
  - id: openwiki-source-ba12ae28763bb2fa92efb31c
    resource: repo://src/jef/data/universe.py
generated: { by: "openwiki/0.7.2", at: "2026-10-28T09:59:03.506Z" }
---

# JEF Data Layer Quickstart

Use this page to choose the right change surface before editing code. `jef.data` is an EOD acquisition, local-store, adjustment, and health subsystem; it is not the implementation of the downstream model, event ledger, dashboard, scheduler, or object store. Start with [Data Layer Boundaries and Public Surfaces](architecture/data-layer-boundaries.md) when a change crosses one of those handoffs.

## Start from a supported entry point

| Need | Entry point | What it is for |
| --- | --- | --- |
| Operate or inspect the subsystem | `jef-data` | The installed command for contract validation, configured acquisition, health, interchange, comparison, and universe inspection. |
| Invoke the same CLI without its console-script wrapper | `python -m jef.data` | Calls the same CLI `main()` as `jef-data`. |
| Validate an EOD frame in Python without loading store or HTTP machinery | `from jef.data import validate, validate_or_raise` | The intentionally small package-root API. `ContractError` and `ContractReport` are also available there. |

The CLI is deliberately the normal integration surface. Treat imports from explicit lower-level modules such as `jef.data.sync` or `jef.data.store` as implementation coupling: use them when changing or testing that subsystem, not as a replacement for the package-root contract API.

## Fast, low-risk orientation

Run these commands before a configuration or workflow change. They read the packaged declaration and local store state; the dry run does not construct collectors, make network requests, require `EODHD_API_KEY`, or write data.

```text
jef-data universe
jef-data sync --dry-run --store data
jef-data status --store data --json
```

`status` is a read-only, offline verdict. An alert returns exit code `1`; warnings and notes alone remain visible without making the command fail. A never-filled store is therefore an expected alert while bringing up a new source, not a reason to bypass the check.

For a real configured update, use `sync`, then inspect `status`:

```text
jef-data sync --store data
jef-data status --store data --json
```

Selected live EODHD legs require `EODHD_API_KEY`; Binance and committed CSV legs have different acquisition paths. Do not emulate a normal batch update by looping over `load`: `sync` owns universe selection, source-specific ordering, bounded tail reconciliation, and aggregate failure handling.

## Route the change

| If the task changes… | Read first | Then read | Safe first check |
| --- | --- | --- | --- |
| The package boundary, CLI contract, local-store seam, or a deployment-time handoff | [Data Layer Boundaries and Public Surfaces](architecture/data-layer-boundaries.md) | The domain page for the actual change | Confirm whether the named consumer is repository-owned before changing its interface. |
| Seven-column input/output, Parquet fields, corporate actions, raw values, split adjustment, locking, or a data repair | [EOD Data Model, Persistence, and Adjustment](concepts/eod-data-model-and-adjustment.md) | [Verification, Dry Runs, and Replay Seams](testing/verification-and-replay-seams.md) | Export a controlled store series and validate the resulting contract frame. |
| An asset, source, `asset_class`, source bounds, modeled feed, or classification evidence | [Universe Declarations and Classification Evidence](concepts/universe-and-classification.md) | [Universe Sync and Tail Reconciliation](workflows/universe-sync-and-reconciliation.md) | Run `jef-data universe` and `jef-data sync --dry-run` against the intended TOML. |
| EODHD, Binance, Yahoo CSV, authentication, retries, rate limiting, normalized bars, or recorded fixtures | [Market-Data Collector Integrations](integrations/market-data-collectors.md) | [Verification, Dry Runs, and Replay Seams](testing/verification-and-replay-seams.md) | Exercise the adapter with an injected transport or replay fixture, never a production token in a fixture. |
| Selection filters, action refresh ordering, first fill, tail size, provider corrections, revision reporting, or per-leg failures | [Universe Sync and Tail Reconciliation](workflows/universe-sync-and-reconciliation.md) | [EOD Data Model, Persistence, and Adjustment](concepts/eod-data-model-and-adjustment.md) | Plan with `sync --dry-run`; test both an empty store and an existing tail. |
| Freshness, missing sessions, actions freshness, phantom splits, coarse prices, class disagreement, or cross-venue spread | [Store Health, Status, and Alert Severity](operations/store-health-and-alerts.md) | [Universe Declarations and Classification Evidence](concepts/universe-and-classification.md) | Run `jef-data status --json` on a representative local store and check its exit code as well as its report. |
| S3 restore/publish, stage order, ECS provenance, timeout/signal behavior, telemetry, dashboard publication, or `JEF_*` environment | [Daily Run, Telemetry, and Publication Gates](operations/daily-run-and-publication.md) | [Data Layer Boundaries and Public Surfaces](architecture/data-layer-boundaries.md) | Trace the complete shell gate; do not test a stage in isolation and assume it will publish. |
| A regression test, deterministic clock, provider replay, dry run, export, or provider comparison | [Verification, Dry Runs, and Replay Seams](testing/verification-and-replay-seams.md) | The page for the behavior under test | Pick the narrowest offline surface that proves the invariant. |

## Invariants to identify before editing

These are routing signals, not substitutes for the linked specifications:

- **Changing data representation or adjustment?** Main OHLCV can be regenerated from raw inputs and stored splits for a raw-basis series; applying the split pass to a `split_adjusted` series is refused. Read the data-model page before modifying fields, reconciliation, or a repair command.
- **Changing a class or source declaration?** The universe parser is strict, and the declared class controls the store asset type and sync behavior. A change that alters basis, corporate-action eligibility, or expected-session calendar is a stored-data semantic change, not a harmless label change; plan a rebuild or migration.
- **Changing sync?** An established series re-fetches only a recent tail. Revisions inside that fetched window are replaced and reported; older history is not normally re-fetched. For raw EODHD legs, actions are refreshed before bars and the stored series is re-derived afterwards.
- **Changing a health finding?** Preserve the severity contract. `status` aggregates reports and returns nonzero for alerts, while warnings—including ordinary cross-venue breaches—do not stop the default daily path.
- **Changing the daily script?** The operational order is restore, sync, status, binning, then publish. The final store and run-artifact uploads are attempted only after those computation gates pass; telemetry and dashboard helpers are best effort.

## Focused verification recipes

Use a check that corresponds to the changed boundary rather than treating a successful live sync as universal proof.

### Contract and store handoff

```text
jef-data validate path/to/eod.csv
jef-data export --store data --exchange eodhd --symbol AAPL.US --output /tmp/AAPL.csv
jef-data validate /tmp/AAPL.csv
```

The contract command distinguishes errors from notes. The export path checks the repository-owned stored-to-seven-column representation; it does not prove an external binning implementation accepted the file.

### Planned versus live acquisition

```text
jef-data sync --dry-run --store data --asset AAPL --provider eodhd --tail 10
jef-data sync --store data --asset AAPL --provider eodhd --tail 10
jef-data status --store data --asset AAPL --json
```

Use dry run to review filters, source bounds, first-fill versus tail behavior, and the crypto completed-day guard. Use a live invocation only when credentials and provider access are appropriate, then evaluate the store with `status` rather than assuming a completed request was healthy.

### Cross-source comparison and deterministic tests

```text
jef-data differential --store data \
  --a-exchange eodhd --a-symbol AAPL.US \
  --b-csv /tmp/reference.csv --tolerance 1e-4
```

A differential is a tolerance-based evidence report, not a bit-equality assertion across providers. For implementation tests, inject collectors and the UTC clock into `run_sync()`, and inject transports, clocks, sleepers, or a `ReplayTransport` at the collector boundary. This makes retry, quota, date-boundary, action-order, and reconciliation cases deterministic without exposing credentials.

## Operational boundary checklist

Before merging or running a change, answer these questions:

1. Is this a configuration, acquisition, storage, health, deployment, or external-handoff change? Follow the corresponding route above before editing.
2. Does it change raw versus pre-adjusted basis, the action-before-load order, a store coordinate, or the modeled source? If so, account for existing persisted data and downstream consumers.
3. Can it be proven with `validate`, export, differential, dry run, status, or replay before using live credentials?
4. Will it change the status exit result or a stage result in `deploy/daily.sh`? If yes, review the S3 publication gate and the distinction between operational failures and best-effort telemetry.
5. Does the proposed change assume behavior from `jef-binning`, events, dashboard, S3, ECS, or scheduling code not implemented by this package? Stop at the architecture boundary and verify that external contract separately.

For the command registration and CLI dispatch code, see [`pyproject.toml`](../pyproject.toml), [`src/jef/data/__main__.py`](../src/jef/data/__main__.py), and [`src/jef/data/cli.py`](../src/jef/data/cli.py). For the package-root Python contract surface, see [`src/jef/data/__init__.py`](../src/jef/data/__init__.py).
