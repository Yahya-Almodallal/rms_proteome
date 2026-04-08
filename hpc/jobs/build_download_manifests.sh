#!/usr/bin/env bash
set -euo pipefail

source "${RMS_PROTEOME_ROOT:-/users/almrb2/rms_proteome}/hpc/env/rms_proteome_hpc.env.sh"

cd "$RMS_PROTEOME_ROOT"
"${RMS_PROTEOME_HELPER_PYTHON}" scripts/tmt_ccle_depmap/08_build_hpc_download_manifests.py
