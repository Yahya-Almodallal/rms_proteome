#!/usr/bin/env bash
set -euo pipefail

# Run Philosopher on MSFragger pepXML outputs in a clean workspace.
# This avoids .meta path issues when running inside the search directory.

source "${RMS_PROTEOME_ROOT:-/users/almrb2/rms_proteome}/hpc/env/rms_proteome_hpc.env.sh"
rms_proteome_load_modules || true

THREADS="${1:-4}"
MEM_GB="${2:-24}"
WALL="${3:-12:00}"
SEARCH_DIR="${4:-${RMS_PROTEOME_TARGET_SEARCH_ROOT}}"
WORK_DIR="${5:-${RMS_PROTEOME_TARGET_SUBSET_ROOT}/philosopher_ws}"

JOBNAME="rms_proteome_msv000085836_philosopher"
MEM_PER_SLOT_MB=$(( MEM_GB * 1024 / THREADS ))
TOTAL_MEM_KB=$(( MEM_GB * 1000000 ))

BSUB_OUTPUT="$({
  bsub \
    -J "${JOBNAME}" \
    -n "${THREADS}" \
    -R "span[hosts=1]" \
    -R "rusage[mem=${MEM_PER_SLOT_MB}]" \
    -M "${TOTAL_MEM_KB}" \
    -W "${WALL}" \
    -u "${RMS_PROTEOME_EMAIL}" \
    -N \
    -oo "${RMS_PROTEOME_LOGROOT}/${JOBNAME}.%J.out" \
    -eo "${RMS_PROTEOME_LOGROOT}/${JOBNAME}.%J.err" <<EOF
#!/usr/bin/env bash
set -euo pipefail
source "${RMS_PROTEOME_HPC_DIR}/env/rms_proteome_hpc.env.sh"
rms_proteome_load_modules || true

PHILOSOPHER="${RMS_PROTEOME_PHILOSOPHER_BIN}"
FASTA="${RMS_PROTEOME_FASTA}"

if [[ ! -x "\$PHILOSOPHER" ]]; then
  echo "Missing Philosopher binary: \$PHILOSOPHER" >&2
  exit 1
fi
if [[ ! -f "\$FASTA" ]]; then
  echo "Missing FASTA: \$FASTA" >&2
  exit 1
fi
if [[ ! -d "${SEARCH_DIR}" ]]; then
  echo "Missing search directory: ${SEARCH_DIR}" >&2
  exit 1
fi

mkdir -p "${WORK_DIR}"
rm -rf "${WORK_DIR:?}/"*

# Copy pepXML files into a clean workspace so .meta is local.
cp "${SEARCH_DIR}"/*.pepXML "${WORK_DIR}/"

cd "${WORK_DIR}"

"\$PHILOSOPHER" workspace --clean
"\$PHILOSOPHER" workspace --init
"\$PHILOSOPHER" database --custom "\$FASTA"

DBFAS=\$(find . -maxdepth 1 -type f -name '*.fas' | head -n 1)
if [[ -z "\$DBFAS" ]]; then
  echo "No .fas database created in workspace." >&2
  exit 1
fi

# Use the actual decoy prefix seen in MSFragger pepXMLs (##).
"\$PHILOSOPHER" peptideprophet \
  --database "\$DBFAS" \
  --decoy '##' \
  --ppm \
  --accmass \
  --expectscore \
  --nonparam \
  *.pepXML

"\$PHILOSOPHER" proteinprophet interact-*.pep.xml
"\$PHILOSOPHER" filter --razor --picked --tag '##' --pepxml . --protxml interact.prot.xml
"\$PHILOSOPHER" report

# Extract the four target genes from the report tables.
"${RMS_PROTEOME_HELPER_PYTHON}" "${RMS_PROTEOME_ROOT}/scripts/tmt_ccle_depmap/13_extract_msv000085836_fragger_targets.py" \
  --search-dir "${WORK_DIR}" \
  --out-dir "${WORK_DIR}/targets"
EOF
})"

printf '%s\n' "$BSUB_OUTPUT" >&2
JOB_ID="$(printf '%s\n' "$BSUB_OUTPUT" | sed -n 's/Job <\([0-9][0-9]*\)>.*/\1/p')"
if [[ -z "$JOB_ID" ]]; then
  echo "Failed to parse LSF job ID from bsub output." >&2
  exit 1
fi
printf '%s\n' "$JOB_ID"
