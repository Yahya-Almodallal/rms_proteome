#!/usr/bin/env bash
set -euo pipefail

source "${RMS_PROTEOME_ROOT:-/users/almrb2/rms_proteome}/hpc/env/rms_proteome_hpc.env.sh"
rms_proteome_load_modules || true

THREADS="${1:-8}"
MEM_GB="${2:-96}"
WALL="${3:-48:00}"
SEARCH_ROOT="${4:-${RMS_PROTEOME_TARGET_SEARCH_ROOT}}"

JOBNAME="rms_proteome_msv000085836_search"
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
cd "${RMS_PROTEOME_ROOT}"
if command -v conda >/dev/null 2>&1; then
  source "\$(conda info --base)/etc/profile.d/conda.sh"
  conda activate "${RMS_PROTEOME_CONDA_ENV_NAME}"
fi
"${RMS_PROTEOME_HELPER_PYTHON}" "${RMS_PROTEOME_ROOT}/scripts/tmt_ccle_depmap/12_prepare_msv000085836_fragger_search.py" \
  --mzml-dir "${RMS_PROTEOME_TARGET_MZML_ROOT}" \
  --search-dir "${SEARCH_ROOT}" \
  --fasta "${RMS_PROTEOME_FASTA}" \
  --threads "${THREADS}"
cd "${SEARCH_ROOT}"
java -Xmx${MEM_GB}G -jar "${RMS_PROTEOME_MSFRAGGER_JAR}" msv000085836_tmt10_closed.params *.mzML
"${RMS_PROTEOME_PHILOSOPHER_BIN}" workspace --clean
"${RMS_PROTEOME_PHILOSOPHER_BIN}" workspace --init
"${RMS_PROTEOME_PHILOSOPHER_BIN}" database --custom "${RMS_PROTEOME_FASTA}"
DBFAS=\$(find "${SEARCH_ROOT}" -maxdepth 1 -type f -name '*.fas' | head -n 1)
"${RMS_PROTEOME_PHILOSOPHER_BIN}" peptideprophet --database "\${DBFAS}" --decoy rev_ --ppm --accmass --expectscore --nonparam *.pepXML
"${RMS_PROTEOME_PHILOSOPHER_BIN}" proteinprophet interact-*.pep.xml
"${RMS_PROTEOME_PHILOSOPHER_BIN}" filter --razor --picked --tag rev_ --pepxml . --protxml interact.prot.xml
"${RMS_PROTEOME_PHILOSOPHER_BIN}" report
"${RMS_PROTEOME_HELPER_PYTHON}" "${RMS_PROTEOME_ROOT}/scripts/tmt_ccle_depmap/13_extract_msv000085836_fragger_targets.py" \
  --search-dir "${SEARCH_ROOT}" \
  --out-dir "${RMS_PROTEOME_TARGET_RESULTS_ROOT}"
EOF
})"

printf '%s\n' "$BSUB_OUTPUT" >&2
JOB_ID="$(printf '%s\n' "$BSUB_OUTPUT" | sed -n 's/Job <\([0-9][0-9]*\)>.*/\1/p')"
if [[ -z "$JOB_ID" ]]; then
  echo "Failed to parse LSF job ID from bsub output." >&2
  exit 1
fi
printf '%s\n' "$JOB_ID"
