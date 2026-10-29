#!/usr/bin/env bash
# Dashboard publication for the venue's two callers (docs/A3B_PLAN.md
# A3b-4; owner decisions 2026-08-29: publish UNCONDITIONALLY, ship the
# page). SOURCED by daily.sh and model.sh, never executed - functions
# only, safe under `set -euo pipefail`, the deploy/events.sh pattern:
# one definition, two callers, because a pair duplicated across scripts
# is the drift shape PRs #101/#102 already paid for.
#
# PUBLICATION IS TELEMETRY, NEVER OPERATIONS. jef_publish_dashboard is
# installed as an EXIT trap, so it runs on green AND red exits - the
# page shows a red day within minutes instead of going stale for the
# length of a red streak - and every path here returns 0, so a broken
# dashboard build can never change a run's exit code. store/ and runs/
# stay green-gated in the caller, untouched (docs/DATA_CONTRACT.md §7
# item 9).
#
# The publisher (python3 -m jef.dashboard publish) joins the FULL
# ledger (synced down; this run's local objects overlaid, because a put
# may have WARN-failed) with the store, writes dashboard/v1/ plus this
# cycle's health_snapshot, and the shell puts everything - the package
# carries no AWS SDK by decision.

JEF_DASH_DIR="${JEF_DASH_DIR:-/tmp/jef-dashboard}"

jef_publish_dashboard() {
    local store="${STORE:-data}" restore="${1:-}"
    local wc="${JEF_EVENT_DIR}-wc" out="${JEF_DASH_DIR}"
    # The model leg carries no store restore of its own; its caller
    # passes --restore-store. The daily leg's restore already ran, so a
    # missing store there means the restore failed - and a health
    # snapshot computed over an absent store would record "never
    # filled" verdicts that are really a restore failure. Absence is
    # the signal: skip, loudly.
    if [[ ! -d "${store}/market_data" && "${restore}" == "--restore-store" ]]; then
        aws s3 sync "s3://${JEF_S3_BUCKET}/store/" "${store}/" \
            --only-show-errors \
            || echo "WARN: store restore for dashboard publish failed"
    fi
    if [[ ! -d "${store}/market_data" ]]; then
        echo "WARN: no store at ${store}/market_data, dashboard publish skipped"
        return 0
    fi
    mkdir -p "${wc}" "${out}" 2>/dev/null || true
    aws s3 sync "s3://${JEF_S3_BUCKET}/events/v1/" "${wc}/" \
        --only-show-errors \
        || echo "WARN: ledger sync-down failed, publishing what is local"
    cp -f "${JEF_EVENT_DIR}"/*.jsonl "${wc}/" 2>/dev/null || true
    local snap="${wc}/${JEF_RUN_STAMP}-health.jsonl"
    if ! python3 -m jef.dashboard publish --events "${wc}" \
            --store "${store}" --out "${out}" \
            --run-date "${RUN_DATE}" --snapshot-out "${snap}"; then
        echo "WARN: dashboard publish failed, page unchanged (telemetry only)"
        return 0
    fi
    # no-cache = revalidate, not "don't store": the edge already runs
    # the managed CachingDisabled policy, but a response with NO
    # Cache-Control invites BROWSER heuristic caching - seen 2026-08-31,
    # the proof-run morning: S3 held the fresh document while a phone
    # reload kept rendering yesterday's fetch. With this header every
    # layer revalidates and a 304 keeps it cheap.
    aws s3 sync "${out}/" "s3://${JEF_S3_BUCKET}/dashboard/v1/" \
        --cache-control "no-cache" --only-show-errors \
        || echo "WARN: dashboard document sync failed (telemetry only)"
    aws s3 cp dashboard/index.html \
        "s3://${JEF_S3_BUCKET}/dashboard/index.html" \
        --cache-control "no-cache" --only-show-errors \
        || echo "WARN: page upload failed (telemetry only)"
    if [[ -s "${snap}" ]]; then
        aws s3 cp "${snap}" \
            "s3://${JEF_S3_BUCKET}/events/v1/$(basename "${snap}")" \
            --only-show-errors \
            || echo "WARN: health snapshot put failed (telemetry only)"
    fi
    return 0
}
