#!/usr/bin/env bash
# The venue's daily chain: restore -> sync -> status -> binning -> publish.
#
# Scheduling is not defined here: an EventBridge rule (infrastructure,
# declared elsewhere) starts the ECS task whose entrypoint is this script.
# The task's exit status is the operational result that the CloudWatch
# alarm reads, so every operational failure must surface as a nonzero exit
# and telemetry must never change it.
#
# Inputs:
#   JEF_S3_BUCKET   required: store/, runs/, events/ and dashboard/ live here
#   EODHD_API_KEY   injected from Secrets Manager; read by jef-data itself
#   JEF_ASSETS      space-separated selection (default below)
#   JEF_APP_DIR     working directory (default /app); a test seam that lets
#                   the gating chain run against stubs outside the container
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- provenance: captured once, before override dispatch, and exported so
# the outer->inner re-exec and every child share the same values.
if [[ -z "${JEF_RUN_STAMP:-}" ]]; then
    JEF_RUN_STAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"
fi
export JEF_RUN_STAMP

if [[ -z "${JEF_IMAGE_DIGEST:-}" ]]; then
    JEF_IMAGE_DIGEST="unknown"
    if [[ -n "${ECS_CONTAINER_METADATA_URI_V4:-}" ]]; then
        # One best-effort lookup. Prints three lines: digest, vCPU, memory GB.
        meta="$(python3 - "${ECS_CONTAINER_METADATA_URI_V4}/task" <<'JEF_META_PY' 2>/dev/null || true
import json
import sys
import urllib.request

try:
    with urllib.request.urlopen(sys.argv[1], timeout=2) as resp:
        task = json.load(resp)
except Exception:
    print("unknown")
    print("")
    print("")
    raise SystemExit(0)
digest = "unknown"
containers = task.get("Containers") or []
if containers:
    first = containers[0] or {}
    digest = first.get("ImageDigest") or first.get("ImageID") or "unknown"
limits = task.get("Limits") or {}
cpu = limits.get("CPU")
memory = limits.get("Memory")
print(digest)
print("" if cpu is None else cpu)
print("" if memory is None else memory / 1024)
JEF_META_PY
)"
        if [[ -n "${meta}" ]]; then
            meta_digest="$(sed -n 1p <<<"${meta}")"
            meta_vcpu="$(sed -n 2p <<<"${meta}")"
            meta_mem="$(sed -n 3p <<<"${meta}")"
            [[ -n "${meta_digest}" ]] && JEF_IMAGE_DIGEST="${meta_digest}"
            if [[ -z "${JEF_TASK_VCPU:-}" && -n "${meta_vcpu}" ]]; then
                JEF_TASK_VCPU="${meta_vcpu}"
                export JEF_TASK_VCPU
            fi
            if [[ -z "${JEF_TASK_MEMORY_GB:-}" && -n "${meta_mem}" ]]; then
                JEF_TASK_MEMORY_GB="${meta_mem}"
                export JEF_TASK_MEMORY_GB
            fi
        fi
    fi
fi
export JEF_IMAGE_DIGEST

# --- ECS command overrides arrive as entrypoint arguments: run them as-is
# (with the provenance above) instead of swallowing them into a daily run.
if [[ $# -gt 0 && "${1}" != "--inner" ]]; then
    exec "$@"
fi

# --- hard deadline: the inner chain gets 3600 s, then TERM, then a KILL
# 60 s later, so a wedged task cannot hold the venue lock indefinitely.
if [[ "${1:-}" != "--inner" ]]; then
    exec timeout --signal=TERM --kill-after=60 3600 "$0" --inner
fi

: "${JEF_S3_BUCKET:?JEF_S3_BUCKET is required}"
JEF_APP_DIR="${JEF_APP_DIR:-/app}"
JEF_ASSETS="${JEF_ASSETS:-AAPL BTC TLT NVDA TSLA IBM}"
cd "${JEF_APP_DIR}"

RUN_DATE="$(date -u +%Y-%m-%d)"
OUT="out/${RUN_DATE}"
DIAG="${OUT}/.diagnostics"
STORE="data"
export RUN_DATE STORE

ASSET_ARGS=()
for asset in ${JEF_ASSETS}; do
    ASSET_ARGS+=(--asset "${asset}")
done

# Given telemetry/publishing legs (functions only, safe under set -e).
# shellcheck source=events.sh
source "${HERE}/events.sh"
# shellcheck source=dashboard.sh
source "${HERE}/dashboard.sh"

STAGE="unknown"
STAGE_T0="$(date +%s)"

on_term() {
    trap - TERM
    jef_emit "${STAGE:-unknown}" 143 "${STAGE_T0}" "$(date +%s)"
    jef_put "${STAGE:-unknown}"
    exit 143
}
trap on_term TERM

# Dashboard publication is telemetry: it runs on green and red exits and
# always returns 0, so the exit status set below is preserved.
trap jef_publish_dashboard EXIT

# --- restore the working copy (an empty bucket is a valid first run).
mkdir -p "${STORE}" "${DIAG}"
aws s3 sync "s3://${JEF_S3_BUCKET}/store/" "${STORE}/" --only-show-errors

# --- 1. sync: a red sync still writes its summary and emits, then stops.
STAGE="sync"
STAGE_T0="$(date +%s)"
rc=0
jef-data sync "${ASSET_ARGS[@]}" --store "${STORE}" \
    --summary-json "${DIAG}/sync.json" || rc=$?
mapfile -t attach < <(jef_attach_if_present "${DIAG}/sync.json")
jef_emit sync "${rc}" "${STAGE_T0}" "$(date +%s)" "${attach[@]}"
jef_put sync
if [[ "${rc}" -ne 0 ]]; then
    exit "${rc}"
fi

# --- 2. status: ONE evaluation, teed to diagnostics and gated on.
STAGE="status"
STAGE_T0="$(date +%s)"
rc=0
jef-data status "${ASSET_ARGS[@]}" --store "${STORE}" --json \
    | tee "${DIAG}/status.json" || rc=$?
mapfile -t attach < <(jef_attach_if_present "${DIAG}/status.json")
jef_emit status "${rc}" "${STAGE_T0}" "$(date +%s)" "${attach[@]}"
jef_put status
if [[ "${rc}" -ne 0 ]]; then
    exit "${rc}"
fi

# --- 3. binning: the external model, once per asset, latest counter only.
STAGE="binning"
rc=0
for asset in ${JEF_ASSETS}; do
    STAGE_T0="$(date +%s)"
    asset_out="${OUT}/${asset}"
    jef-binning --asset "${asset}" --store "${STORE}" \
        --counter-start latest --counter-end latest \
        --output-dir "${asset_out}" || rc=$?
    extra=(--asset "${asset}")
    manifest="$(find "${asset_out}" -maxdepth 1 -name 'run_manifest*.json' \
        -type f 2>/dev/null | sort | head -n 1 || true)"
    if [[ -n "${manifest}" ]]; then
        keys="${DIAG}/${asset}-manifest-keys.json"
        jef_manifest_keys "${manifest}" "${keys}"
        mapfile -t attach < <(jef_attach_if_present "${keys}")
        extra+=("${attach[@]}")
    fi
    jef_emit binning "${rc}" "${STAGE_T0}" "$(date +%s)" "${extra[@]}"
    if [[ "${rc}" -ne 0 ]]; then
        break
    fi
done
jef_put binning
if [[ "${rc}" -ne 0 ]]; then
    exit "${rc}"
fi

# --- publish: green only. Sequential, not a transaction.
aws s3 sync "${STORE}/" "s3://${JEF_S3_BUCKET}/store/" --only-show-errors
aws s3 sync "${OUT}/" "s3://${JEF_S3_BUCKET}/runs/${RUN_DATE}/" --only-show-errors
printf '%s\n' "${JEF_IMAGE_DIGEST}" \
    | aws s3 cp - "s3://${JEF_S3_BUCKET}/runs/${RUN_DATE}/image_digest.txt" \
        --only-show-errors
