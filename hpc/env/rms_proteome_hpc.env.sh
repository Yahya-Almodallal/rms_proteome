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
export RMS_PROTEOME_TOOLS_ROOT="${RMS_PROTEOME_TOOLS_ROOT:-/users/almrb2/tools/proteomics}"

export RMS_PROTEOME_TARGET_SUBSET_ROOT="${RMS_PROTEOME_TARGET_SUBSET_ROOT:-${RMS_PROTEOME_DOWNLOADS_ROOT}/MSV000085836_target_subset}"
export RMS_PROTEOME_TARGET_MZML_ROOT="${RMS_PROTEOME_TARGET_MZML_ROOT:-${RMS_PROTEOME_TARGET_SUBSET_ROOT}/mzML}"
export RMS_PROTEOME_TARGET_SEARCH_ROOT="${RMS_PROTEOME_TARGET_SEARCH_ROOT:-${RMS_PROTEOME_TARGET_SUBSET_ROOT}/search_closed_tmt10}"
export RMS_PROTEOME_TARGET_RESULTS_ROOT="${RMS_PROTEOME_TARGET_RESULTS_ROOT:-${RMS_PROTEOME_TARGET_SEARCH_ROOT}/targets}"

export RMS_PROTEOME_CONDA_ENV_NAME="${RMS_PROTEOME_CONDA_ENV_NAME:-rms_proteome_ms}"
export RMS_PROTEOME_USE_CONDA="${RMS_PROTEOME_USE_CONDA:-0}"
export RMS_PROTEOME_JAVA_HOME="${RMS_PROTEOME_JAVA_HOME:-}"
export RMS_PROTEOME_MSFRAGGER_JAR="${RMS_PROTEOME_MSFRAGGER_JAR:-${RMS_PROTEOME_TOOLS_ROOT}/msfragger/MSFragger.jar}"
export RMS_PROTEOME_PHILOSOPHER_BIN="${RMS_PROTEOME_PHILOSOPHER_BIN:-${RMS_PROTEOME_TOOLS_ROOT}/philosopher/philosopher}"
export RMS_PROTEOME_FASTA="${RMS_PROTEOME_FASTA:-${RMS_PROTEOME_DOWNLOADS_ROOT}/MSV000085836/sequence/2014-02-04_REVuniprot_HUMAN_02_2014_contam_sorted.fasta}"

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

# Prefer a user-space Java install if provided (needed for MSFragger).
if [[ -z "$RMS_PROTEOME_JAVA_HOME" ]]; then
  for cand in /users/almrb2/tools/jdk17/jdk-17*; do
    if [[ -d "$cand" ]]; then
      RMS_PROTEOME_JAVA_HOME="$cand"
      break
    fi
  done
fi

if [[ -n "${RMS_PROTEOME_JAVA_HOME:-}" ]] && [[ -d "$RMS_PROTEOME_JAVA_HOME" ]]; then
  export JAVA_HOME="$RMS_PROTEOME_JAVA_HOME"
  export PATH="$JAVA_HOME/bin:$PATH"
fi

mkdir -p "$RMS_PROTEOME_DOWNLOADS_ROOT" "$RMS_PROTEOME_LOGROOT" "$RMS_PROTEOME_TMPROOT"
