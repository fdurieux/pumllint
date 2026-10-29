#!/usr/bin/env bash
# The daily venue chain: restore the store, sync, status, binning per asset,
# then publish the store, the run outputs and the image digest (green only).
set -euo pipefail

# Image provenance and task size from the task metadata, fetched once.
if [[ -z "${JEF_IMAGE_DIGEST:-}" ]]; then
    _meta=$(curl -s "${ECS_CONTAINER_METADATA_URI_V4:-}/task" 2>/dev/null || true)
    JEF_IMAGE_DIGEST=$(printf '%s' "${_meta}" | python3 -c 'import json, sys; c = json.loads(sys.stdin.read())["Containers"][0]; print(c.get("ImageDigest") or c.get("ImageID") or "unknown")' 2>/dev/null || true)
    if [[ -z "${JEF_IMAGE_DIGEST}" ]]; then
        JEF_IMAGE_DIGEST=unknown
    fi
    if _size=$(printf '%s' "${_meta}" | python3 -c 'import json, sys; limits = json.loads(sys.stdin.read())["Limits"]; print(limits["CPU"], limits["Memory"] / 1024)' 2>/dev/null) && [[ -n "${_size}" ]]; then
        read -r _vcpu _mem <<<"${_size}"
        if [[ -z "${JEF_TASK_VCPU:-}" ]]; then
            JEF_TASK_VCPU="${_vcpu}"
        fi
        if [[ -z "${JEF_TASK_MEMORY_GB:-}" ]]; then
            JEF_TASK_MEMORY_GB="${_mem}"
        fi
        export JEF_TASK_VCPU JEF_TASK_MEMORY_GB
    fi
fi
export JEF_IMAGE_DIGEST

if [[ -z "${JEF_RUN_STAMP:-}" ]]; then
    JEF_RUN_STAMP=$(date -u +%Y-%m-%dT%H%M%SZ)
fi
export JEF_RUN_STAMP

# An override command arrives as arguments: run it instead of the chain.
if [[ $# -gt 0 && "$1" != "--inner" ]]; then
    exec "$@"
fi

# Hard cap: the stages run only in the re-exec'd inner invocation.
if [[ "${1:-}" != "--inner" ]]; then
    exec timeout --signal=TERM --kill-after=60 3600 "$0" --inner
fi

: "${JEF_S3_BUCKET:?JEF_S3_BUCKET must name the venue bucket}"

read -r -a ASSETS <<<"${JEF_ASSETS:-AAPL BTC TLT NVDA TSLA IBM}"
RUN_DATE=$(date -u +%F)
STORE=data
OUT="out/${RUN_DATE}"
DIAG="${OUT}/.diagnostics"

_here=$(dirname "$0")
# shellcheck source=/dev/null
source "${_here}/events.sh"
# shellcheck source=/dev/null
source "${_here}/dashboard.sh"

cd "${JEF_APP_DIR:-/app}"
echo "== jef daily ${RUN_DATE} assets: ${ASSETS[*]}"
mkdir -p "${DIAG}"

trap 'jef_emit "${STAGE:-unknown}" 143 "${STAGE_T0:-0}" "$(date +%s)"; jef_put "${STAGE:-unknown}"; exit 143' TERM
trap 'jef_publish_dashboard' EXIT

aws s3 sync "s3://${JEF_S3_BUCKET}/store/" "data/" --only-show-errors

FILTERS=()
for asset in "${ASSETS[@]}"; do
    FILTERS+=(--asset "${asset}")
done

# Stage: sync
STAGE=sync
STAGE_T0=$(date +%s)
rc=0
jef-data sync "${FILTERS[@]}" --store "${STORE}" --summary-json "${DIAG}/sync.json" || rc=$?
# shellcheck disable=SC2046
jef_emit sync "${rc}" "${STAGE_T0}" "$(date +%s)" $(jef_attach_if_present "${DIAG}/sync.json")
jef_put sync
if [[ "${rc}" -ne 0 ]]; then
    exit "${rc}"
fi

# Stage: status (one evaluation, printed and captured)
STAGE=status
STAGE_T0=$(date +%s)
rc=0
jef-data status "${FILTERS[@]}" --store "${STORE}" --json | tee "${DIAG}/status.json" || rc=$?
# shellcheck disable=SC2046
jef_emit status "${rc}" "${STAGE_T0}" "$(date +%s)" $(jef_attach_if_present "${DIAG}/status.json")
jef_put status
if [[ "${rc}" -ne 0 ]]; then
    exit "${rc}"
fi

# Stage: binning, one emit per asset, stopping at the first failing asset
STAGE=binning
STAGE_T0=$(date +%s)
rc=0
for asset in "${ASSETS[@]}"; do
    asset_t0=$(date +%s)
    asset_rc=0
    jef-binning --asset "${asset}" --store "${STORE}" --counter-start latest \
        --counter-end latest --output-dir "${OUT}/${asset}" || asset_rc=$?
    emit_args=(--asset "${asset}")
    manifest=$(find "${OUT}/${asset}" -maxdepth 1 -name 'run_manifest*.json' -print -quit 2>/dev/null || true)
    keys="${DIAG}/binning-${asset}.json"
    if [[ -n "${manifest}" ]]; then
        jef_manifest_keys "${manifest}" "${keys}"
        emit_args+=(--manifest "${manifest}" --manifest-root "${OUT}" --manifest-prefix "runs/${RUN_DATE}")
    fi
    # shellcheck disable=SC2046
    jef_emit binning "${asset_rc}" "${asset_t0}" "$(date +%s)" "${emit_args[@]}" $(jef_attach_if_present "${keys}")
    if [[ "${asset_rc}" -ne 0 ]]; then
        rc="${asset_rc}"
        break
    fi
done
jef_put binning
if [[ "${rc}" -ne 0 ]]; then
    exit "${rc}"
fi

# Publish (green only)
aws s3 sync "data/" "s3://${JEF_S3_BUCKET}/store/" --only-show-errors
aws s3 sync "${OUT}/" "s3://${JEF_S3_BUCKET}/runs/${RUN_DATE}/" --only-show-errors
echo "${JEF_IMAGE_DIGEST}" | aws s3 cp - "s3://${JEF_S3_BUCKET}/runs/${RUN_DATE}/image_digest.txt" --only-show-errors
echo "== green (${JEF_IMAGE_DIGEST})"
exit 0
