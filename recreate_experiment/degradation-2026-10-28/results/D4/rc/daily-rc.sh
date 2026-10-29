#!/usr/bin/env bash
# The daily venue chain: restore the store, sync, status, binning, then
# publish the store and the run outputs only when every stage is green.
set -euo pipefail

# Prologue (every invocation): image digest and task size from the task
# metadata, read once and only when no digest was handed in.
if [[ -z "${JEF_IMAGE_DIGEST:-}" ]]; then
    _meta="$(curl -s "${ECS_CONTAINER_METADATA_URI_V4:-}/task" 2>/dev/null || true)"
    JEF_IMAGE_DIGEST="$(python3 -c 'import json, sys; c = json.loads(sys.argv[1])["Containers"][0]; print(c.get("ImageDigest") or c.get("ImageID") or "unknown")' "${_meta}" 2>/dev/null || true)"
    if [[ -z "${JEF_IMAGE_DIGEST}" ]]; then
        JEF_IMAGE_DIGEST="unknown"
    fi
    _size="$(python3 -c 'import json, sys; m = json.loads(sys.argv[1])["Limits"]; print(m["CPU"], m["Memory"] / 1024)' "${_meta}" 2>/dev/null || true)"
    if [[ -n "${_size}" ]]; then
        read -r _vcpu _mem <<<"${_size}"
        : "${JEF_TASK_VCPU:=${_vcpu}}"
        : "${JEF_TASK_MEMORY_GB:=${_mem}}"
        export JEF_TASK_VCPU JEF_TASK_MEMORY_GB
    fi
fi
export JEF_IMAGE_DIGEST

if [[ -z "${JEF_RUN_STAMP:-}" ]]; then
    JEF_RUN_STAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"
fi
export JEF_RUN_STAMP

# Exec guard: an override command arrives as arguments and runs instead.
if [[ $# -gt 0 && "$1" != "--inner" ]]; then
    exec "$@"
fi

# Hard cap: the stages run only in the re-exec'd inner invocation.
if [[ "${1:-}" != "--inner" ]]; then
    exec timeout --signal=TERM --kill-after=60 3600 "$0" --inner
fi

: "${JEF_S3_BUCKET:?JEF_S3_BUCKET must name the venue bucket}"

read -r -a ASSETS <<<"${JEF_ASSETS:-AAPL BTC TLT NVDA TSLA IBM}"
RUN_DATE="$(date -u +%F)"
STORE="data"
OUT="out/${RUN_DATE}"
DIAG="${OUT}/.diagnostics"

HERE="$(dirname "$0")"
# shellcheck source=/dev/null
source "${HERE}/events.sh"
# shellcheck source=/dev/null
source "${HERE}/dashboard.sh"

cd "${JEF_APP_DIR:-/app}"
echo "== jef daily ${RUN_DATE} assets: ${ASSETS[*]}"
mkdir -p "${DIAG}"

trap 'jef_emit "${STAGE:-unknown}" 143 "${STAGE_T0:-0}" "$(date +%s)"; jef_put "${STAGE:-unknown}"; exit 143' TERM
trap 'jef_publish_dashboard' EXIT

aws s3 sync "s3://${JEF_S3_BUCKET}/store/" "${STORE}/" --only-show-errors

FILTERS=()
for asset in "${ASSETS[@]}"; do
    FILTERS+=(--asset "${asset}")
done

# Stage: sync
STAGE=sync
STAGE_T0="$(date +%s)"
rc=0
jef-data sync "${FILTERS[@]}" --store "${STORE}" --summary-json "${DIAG}/sync.json" || rc=$?
jef_emit sync "${rc}" "${STAGE_T0}" "$(date +%s)" $(jef_attach_if_present "${DIAG}/sync.json")
jef_put sync
if [[ "${rc}" -ne 0 ]]; then
    exit "${rc}"
fi

# Stage: status (one evaluation, printed and captured)
STAGE=status
STAGE_T0="$(date +%s)"
rc=0
jef-data status "${FILTERS[@]}" --store "${STORE}" --json | tee "${DIAG}/status.json" || rc=$?
jef_emit status "${rc}" "${STAGE_T0}" "$(date +%s)" $(jef_attach_if_present "${DIAG}/status.json")
jef_put status
if [[ "${rc}" -ne 0 ]]; then
    exit "${rc}"
fi

# Stage: binning (one emit per asset, one put for the stage)
STAGE=binning
STAGE_T0="$(date +%s)"
rc=0
for asset in "${ASSETS[@]}"; do
    a_t0="$(date +%s)"
    a_rc=0
    jef-binning --asset "${asset}" --store "${STORE}" --counter-start latest --counter-end latest \
        --output-dir "${OUT}/${asset}" || a_rc=$?
    manifest="$(find "${OUT}/${asset}" -maxdepth 1 -name 'run_manifest*.json' -print -quit 2>/dev/null || true)"
    extra=(--asset "${asset}")
    if [[ -n "${manifest}" ]]; then
        jef_manifest_keys "${manifest}" "${DIAG}/binning-${asset}.json"
        extra+=(--manifest "${manifest}" --manifest-root "${OUT}" --manifest-prefix "runs/${RUN_DATE}")
    fi
    jef_emit binning "${a_rc}" "${a_t0}" "$(date +%s)" "${extra[@]}" \
        $(jef_attach_if_present "${DIAG}/binning-${asset}.json")
    if [[ "${a_rc}" -ne 0 ]]; then
        rc="${a_rc}"
        break
    fi
done
jef_put binning
if [[ "${rc}" -ne 0 ]]; then
    exit "${rc}"
fi

# Publish: green only.
aws s3 sync "${STORE}/" "s3://${JEF_S3_BUCKET}/store/" --only-show-errors
aws s3 sync "${OUT}/" "s3://${JEF_S3_BUCKET}/runs/${RUN_DATE}/" --only-show-errors
echo "${JEF_IMAGE_DIGEST}" | aws s3 cp - "s3://${JEF_S3_BUCKET}/runs/${RUN_DATE}/image_digest.txt" --only-show-errors
echo "== green (${JEF_IMAGE_DIGEST})"
exit 0
