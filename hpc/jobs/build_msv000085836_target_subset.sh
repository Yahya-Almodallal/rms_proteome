#!/usr/bin/env bash
set -euo pipefail

source "${RMS_PROTEOME_ROOT:-/users/almrb2/rms_proteome}/hpc/env/rms_proteome_hpc.env.sh"

RAW_DIR="${1:-${RMS_PROTEOME_DOWNLOADS_ROOT}/MSV000085836/raw}"
OUT_MANIFEST="${2:-${RMS_PROTEOME_MANIFEST_DIR}/MSV000085836_target_plex_local_manifest.tsv}"
OUT_SUMMARY="${3:-${RMS_PROTEOME_MANIFEST_DIR}/MSV000085836_target_plex_local_summary.tsv}"

cd "$RMS_PROTEOME_ROOT"
"${RMS_PROTEOME_HELPER_PYTHON}" \
  scripts/tmt_ccle_depmap/11_build_msv000085836_local_target_subset.py \
  --sample-info-xlsx "$RMS_PROTEOME_ROOT/metadata/tmt_ccle_depmap/msv000085836/Table_S1_Sample_Information.xlsx" \
  --raw-dir "$RAW_DIR" \
  --out-manifest "$OUT_MANIFEST" \
  --out-summary "$OUT_SUMMARY"
