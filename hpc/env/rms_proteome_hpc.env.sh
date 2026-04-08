#!/usr/bin/env bash

# Shared HPC environment for rms_proteome.
#
# Keep this file simple:
# - paths
# - tool variables
# - helper functions
# Strict shell mode belongs in the wrapper scripts that source this file.

export RMS_PROTEOME_ROOT="${RMS_PROTEOME_ROOT:-/users/almrb2/rms_proteome}"
export RMS_PROTEOME_HPC_DIR="${RMS_PROTEOME_HPC_DIR:-${RMS_PROTEOME_ROOT}/hpc}"

export RMS_PROTEOME_DOWNLOADS_ROOT="${RMS_PROTEOME_DOWNLOADS_ROOT:-/scratch/almrb2/rms.omics/proteomics}"
export RMS_PROTEOME_LOGROOT="${RMS_PROTEOME_LOGROOT:-${RMS_PROTEOME_DOWNLOADS_ROOT}/logs}"
export RMS_PROTEOME_TMPROOT="${RMS_PROTEOME_TMPROOT:-${RMS_PROTEOME_DOWNLOADS_ROOT}/tmp}"
export RMS_PROTEOME_MANIFEST_DIR="${RMS_PROTEOME_MANIFEST_DIR:-${RMS_PROTEOME_ROOT}/metadata/tmt_ccle_depmap/hpc_downloads}"

export RMS_PROTEOME_HELPER_PYTHON="${RMS_PROTEOME_HELPER_PYTHON:-python3}"
export RMS_PROTEOME_EMAIL="${RMS_PROTEOME_EMAIL:-yahya.almodallal@cchmc.org}"

rms_proteome_init_modules() {
  if command -v module >/dev/null 2>&1; then
    return 0
  fi
  if [[ -f /etc/profile.d/modules.sh ]]; then
    # shellcheck disable=SC1091
    source /etc/profile.d/modules.sh
  elif [[ -f /usr/share/Modules/init/bash ]]; then
    # shellcheck disable=SC1091
    source /usr/share/Modules/init/bash
  fi
  command -v module >/dev/null 2>&1
}

rms_proteome_load_modules() {
  if ! rms_proteome_init_modules; then
    return 0
  fi
  # Add modules here only if the HPC requires them for wget/ascp/python.
  return 0
}

mkdir -p "$RMS_PROTEOME_DOWNLOADS_ROOT" "$RMS_PROTEOME_LOGROOT" "$RMS_PROTEOME_TMPROOT"
