#!/usr/bin/env bash
# The daily chain: restore the store, sync, status, binning, publish on green.
set -euo pipefail

# Prologue (every invocation): image digest and task size from the task metadata.
if [[ -z "${JEF_IMAGE_DIGEST:-}" ]]; then
    _meta="$(curl -s "${ECS_CONTAINER_METADATA_URI_V4:-}/task" 2>/dev/null || true)"
    JEF_IMAGE_DIGEST="$(printf '%s' "${_meta}" | python3 -c 'import json, sys; c = json.load(sys.stdin)["Containers"][0]; print(c.get("ImageDigest") or c.get("ImageID") or "unknown")' 2>/dev/null)" || JEF_IMAGE_DIGEST="unknown"
    [[ -n "${JEF_IMAGE_DIGEST}" ]] || JEF_IMAGE_DIGEST="unknown"
    if _size="$(printf '%s' "${_meta}" | python3 -c 'import json, sys; d = json.load(sys.stdin)["Limits"]; print(d["CPU"], d["Memory"] / 1024)' 2>/dev/null)"; then
        read -r _cpu _mem <<< "${_size}"
        if [[ -z "${JEF_TASK_VCPU+set}" ]]; then JEF_TASK_VCPU="${_cpu}"; fi
        if [[ -z "${JEF_TASK_MEMORY_GB+set}" ]]; then JEF_TASK_MEMORY_GB="${_mem}"; fi
        export JEF_TASK_VCPU JEF_TASK_MEMORY_GB
    fi
fi
export JEF_IMAGE_DIGEST

if [[ -z "${JEF_RUN_STAMP:-}" ]]; then
    JEF_RUN_STAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"
fi
export JEF_RUN_STAMP

# Exec guard: an override command runs in place of the chain.
if [[ $# -gt 0 && "$1" != "--inner" ]]; then
    exec "$@"
fi

# Hard cap: the stages run only in the --inner invocation under timeout.
if [[ "${1:-}" != "--inner" ]]; then
    exec timeout --signal=TERM --kill-after=60 3600 "$0" --inner
fi

: "${JEF_S3_BUCKET:?JEF_S3_BUCKET must name the venue bucket}"

read -r -d '' -a ASSETS <<< "${JEF_ASSETS:-AAPL BTC TLT NVDA TSLA IBM}" || true
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

aws s3 sync "s3://${JEF_S3_BUCKET}/store/" "data/" --only-show-errors

FILTERS=()
for asset in "${ASSETS[@]}"; do
    FILTERS+=(--asset "${asset}")
done

# Stage: sync.
STAGE=sync
STAGE_T0="$(date +%s)"
rc=0
jef-data sync "${FILTERS[@]}" --store data --summary-json "${DIAG}/sync.json" || rc=$?
# shellcheck disable=SC2046
jef_emit sync "${rc}" "${STAGE_T0}" "$(date +%s)" $(jef_attach_if_present "${DIAG}/sync.json")
jef_put sync
if [[ "${rc}" -ne 0 ]]; then
    exit "${rc}"
fi

# Stage: status (one evaluation, printed and captured).
STAGE=status
STAGE_T0="$(date +%s)"
rc=0
jef-data status "${FILTERS[@]}" --store data --json | tee "${DIAG}/status.json" || rc=$?
# shellcheck disable=SC2046
jef_emit status "${rc}" "${STAGE_T0}" "$(date +%s)" $(jef_attach_if_present "${DIAG}/status.json")
jef_put status
if [[ "${rc}" -ne 0 ]]; then
    exit "${rc}"
fi

# Stage: binning, one emit per asset, stopping at the first failure.
STAGE=binning
STAGE_T0="$(date +%s)"
rc=0
for asset in "${ASSETS[@]}"; do
    a_t0="$(date +%s)"
    a_rc=0
    jef-binning --asset "${asset}" --store data --counter-start latest --counter-end latest \
        --output-dir "${OUT}/${asset}" || a_rc=$?
    manifest=""
    if [[ -d "${OUT}/${asset}" ]]; then
        manifest="$(find "${OUT}/${asset}" -maxdepth 1 -name 'run_manifest*.json' -print -quit 2>/dev/null || true)"
    fi
    extra=(--asset "${asset}")
    if [[ -n "${manifest}" ]]; then
        jef_manifest_keys "${manifest}" "${DIAG}/binning-${asset}.json"
        extra+=(--manifest "${manifest}" --manifest-root "${OUT}" --manifest-prefix "runs/${RUN_DATE}")
    fi
    # shellcheck disable=SC2046
    jef_emit binning "${a_rc}" "${a_t0}" "$(date +%s)" "${extra[@]}" $(jef_attach_if_present "${DIAG}/binning-${asset}.json")
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
aws s3 sync "data/" "s3://${JEF_S3_BUCKET}/store/" --only-show-errors
aws s3 sync "${OUT}/" "s3://${JEF_S3_BUCKET}/runs/${RUN_DATE}/" --only-show-errors
echo "${JEF_IMAGE_DIGEST}" | aws s3 cp - "s3://${JEF_S3_BUCKET}/runs/${RUN_DATE}/image_digest.txt" --only-show-errors
echo "== green (${JEF_IMAGE_DIGEST})"
exit 0
