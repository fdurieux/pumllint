#!/usr/bin/env bash
# Daily chain: restore -> sync -> status -> binning -> publish.
#
# Scheduling lives in EventBridge infrastructure, not here. The task's exit
# status is the operational result that CloudWatch alarming reads; event and
# dashboard telemetry are best effort and never change it.
#
# Overrides: any argument other than the private --inner marker is exec'd
# as a command (ECS command overrides arrive as entrypoint arguments).

JEF_ASSETS="${JEF_ASSETS:-AAPL BTC TLT NVDA TSLA IBM}"
JEF_APP_DIR="${JEF_APP_DIR:-/app}"
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---- provenance, captured once per invocation and inherited by re-execs ----
if [[ -z "${JEF_RUN_STAMP:-}" ]]; then
    JEF_RUN_STAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"
fi
export JEF_RUN_STAMP

if [[ -z "${JEF_IMAGE_DIGEST:-}" ]]; then
    JEF_IMAGE_DIGEST="unknown"
    if [[ -n "${ECS_CONTAINER_METADATA_URI_V4:-}" ]]; then
        ecs_meta="$(python3 - "${ECS_CONTAINER_METADATA_URI_V4}/task" 2>/dev/null <<'JEF_ECS_PY' || true
import json
import sys
import urllib.request

with urllib.request.urlopen(sys.argv[1], timeout=2) as resp:
    task = json.load(resp)
containers = task.get("Containers") or []
first = containers[0] if containers else {}
digest = first.get("ImageDigest") or first.get("ImageID") or ""
limits = task.get("Limits") or {}
cpu = limits.get("CPU")
mem = limits.get("Memory")
print(digest)
print("" if cpu is None else cpu)
print("" if mem is None else mem / 1024)
JEF_ECS_PY
)"
        if [[ -n "${ecs_meta}" ]]; then
            ecs_digest="$(sed -n 1p <<<"${ecs_meta}")"
            ecs_cpu="$(sed -n 2p <<<"${ecs_meta}")"
            ecs_mem_gb="$(sed -n 3p <<<"${ecs_meta}")"
            if [[ -n "${ecs_digest}" ]]; then
                JEF_IMAGE_DIGEST="${ecs_digest}"
            fi
            if [[ -z "${JEF_TASK_VCPU:-}" && -n "${ecs_cpu}" ]]; then
                export JEF_TASK_VCPU="${ecs_cpu}"
            fi
            if [[ -z "${JEF_TASK_MEMORY_GB:-}" && -n "${ecs_mem_gb}" ]]; then
                export JEF_TASK_MEMORY_GB="${ecs_mem_gb}"
            fi
        fi
    fi
fi
export JEF_IMAGE_DIGEST

# ---- entrypoint dispatch ----------------------------------------------------
if [[ $# -gt 0 && "$1" != "--inner" ]]; then
    exec "$@"
fi
if [[ "${1:-}" != "--inner" ]]; then
    # Hard one-hour cap on the inner chain: TERM at 3600 s, KILL 60 s later.
    exec timeout --signal=TERM --kill-after=60 3600 "$0" --inner
fi

# ---- inner daily chain ------------------------------------------------------
: "${JEF_S3_BUCKET:?JEF_S3_BUCKET is required}"
cd "${JEF_APP_DIR}"

RUN_DATE="$(date -u +%Y-%m-%d)"
OUT_DIR="out/${RUN_DATE}"
DIAG_DIR="${OUT_DIR}/.diagnostics"
STORE="data"
mkdir -p "${DIAG_DIR}"

read -r -a ASSETS <<<"${JEF_ASSETS}"
ASSET_ARGS=()
for asset in "${ASSETS[@]}"; do
    ASSET_ARGS+=(--asset "${asset}")
done

# shellcheck source=events.sh
source "${SCRIPT_DIR}/events.sh"
# shellcheck source=dashboard.sh
source "${SCRIPT_DIR}/dashboard.sh"

STAGE=""
STAGE_T0=""

on_term() {
    local stage="${STAGE:-unknown}" t1
    t1="$(date -u +%s)"
    jef_emit "${stage}" 143 "${STAGE_T0:-${t1}}" "${t1}"
    jef_put "${stage}"
    exit 143
}
trap on_term TERM
trap jef_publish_dashboard EXIT

# Restore the working copy; an empty bucket is a valid first run.
aws s3 sync "s3://${JEF_S3_BUCKET}/store/" "${STORE}/" --only-show-errors

# ---- 1. sync -----------------------------------------------------------------
STAGE="sync"
STAGE_T0="$(date -u +%s)"
rc=0
jef-data sync "${ASSET_ARGS[@]}" --store "${STORE}" \
    --summary-json "${DIAG_DIR}/sync.json" || rc=$?
t1="$(date -u +%s)"
mapfile -t attach < <(jef_attach_if_present "${DIAG_DIR}/sync.json")
jef_emit sync "${rc}" "${STAGE_T0}" "${t1}" "${attach[@]}"
jef_put sync
if [[ "${rc}" -ne 0 ]]; then
    echo "sync failed (rc=${rc}); status, binning and publication skipped" >&2
    exit "${rc}"
fi

# ---- 2. status: evaluated once, the same JSON gates and is attached ----------
STAGE="status"
STAGE_T0="$(date -u +%s)"
rc=0
jef-data status "${ASSET_ARGS[@]}" --store "${STORE}" --json \
    | tee "${DIAG_DIR}/status.json" || rc=$?
t1="$(date -u +%s)"
mapfile -t attach < <(jef_attach_if_present "${DIAG_DIR}/status.json")
jef_emit status "${rc}" "${STAGE_T0}" "${t1}" "${attach[@]}"
jef_put status
if [[ "${rc}" -ne 0 ]]; then
    echo "status reported alerts (rc=${rc}); binning and publication skipped" >&2
    exit "${rc}"
fi

# ---- 3. binning, once per selected asset -------------------------------------
STAGE="binning"
STAGE_T0="$(date -u +%s)"
rc=0
for asset in "${ASSETS[@]}"; do
    a0="$(date -u +%s)"
    arc=0
    jef-binning --asset "${asset}" --store "${STORE}" \
        --counter-start latest --counter-end latest \
        --output-dir "${OUT_DIR}/${asset}" || arc=$?
    a1="$(date -u +%s)"
    extra=()
    manifest="$(find "${OUT_DIR}/${asset}" -name 'run_manifest*.json' -type f 2>/dev/null \
        | sort | head -n 1 || true)"
    if [[ -n "${manifest}" ]]; then
        keys="${DIAG_DIR}/binning-${asset}-keys.json"
        jef_manifest_keys "${manifest}" "${keys}"
        mapfile -t extra < <(jef_attach_if_present "${keys}")
    fi
    jef_emit binning "${arc}" "${a0}" "${a1}" --asset "${asset}" "${extra[@]}"
    if [[ "${arc}" -ne 0 ]]; then
        rc="${arc}"
        echo "binning failed for ${asset} (rc=${rc})" >&2
        break
    fi
done
jef_put binning
if [[ "${rc}" -ne 0 ]]; then
    exit "${rc}"
fi

# ---- 4. publish (green only; sequential, not transactional) ------------------
aws s3 sync "${STORE}/" "s3://${JEF_S3_BUCKET}/store/" --only-show-errors
aws s3 sync "${OUT_DIR}/" "s3://${JEF_S3_BUCKET}/runs/${RUN_DATE}/" --only-show-errors
printf '%s\n' "${JEF_IMAGE_DIGEST}" \
    | aws s3 cp - "s3://${JEF_S3_BUCKET}/runs/${RUN_DATE}/image_digest.txt" --only-show-errors
