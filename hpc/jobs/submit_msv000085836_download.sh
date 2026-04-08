#!/usr/bin/env bash
set -euo pipefail

source "${RMS_PROTEOME_ROOT:-/users/almrb2/rms_proteome}/hpc/env/rms_proteome_hpc.env.sh"
rms_proteome_load_modules || true

THREADS="${1:-4}"
MEM_MB="${2:-8000}"
WALL="${3:-48:00}"
DEST_ROOT="${4:-${RMS_PROTEOME_DOWNLOADS_ROOT}/MSV000085836}"

JOBNAME="rms_proteome_msv000085836_mirror"
TOTAL_MEM_MB=$(( THREADS * MEM_MB ))

BSUB_OUTPUT="$({
  bsub \
    -J "${JOBNAME}" \
    -n "${THREADS}" \
    -R "span[hosts=1]" \
    -R "rusage[mem=${MEM_MB}]" \
    -M "${TOTAL_MEM_MB}000" \
    -W "${WALL}" \
    -u "${RMS_PROTEOME_EMAIL}" \
    -N \
    -oo "${RMS_PROTEOME_LOGROOT}/${JOBNAME}.%J.out" \
    -eo "${RMS_PROTEOME_LOGROOT}/${JOBNAME}.%J.err" <<EOF
#!/usr/bin/env bash
set -euo pipefail
source "${RMS_PROTEOME_HPC_DIR}/env/rms_proteome_hpc.env.sh"
rms_proteome_load_modules || true
cd "${RMS_PROTEOME_ROOT}"
bash "${RMS_PROTEOME_ROOT}/scripts/tmt_ccle_depmap/09_prepare_msv000085836_hpc_mirror.sh" "${DEST_ROOT}"
EOF
})"

printf '%s\n' "$BSUB_OUTPUT" >&2
JOB_ID="$(printf '%s\n' "$BSUB_OUTPUT" | sed -n 's/Job <\([0-9][0-9]*\)>.*/\1/p')"
if [[ -z "$JOB_ID" ]]; then
  echo "Failed to parse LSF job ID from bsub output." >&2
  exit 1
fi
printf '%s\n' "$JOB_ID"
