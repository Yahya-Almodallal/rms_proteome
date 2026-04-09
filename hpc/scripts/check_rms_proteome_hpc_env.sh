#!/usr/bin/env bash

set -euo pipefail

source "${RMS_PROTEOME_ROOT:-/users/almrb2/rms_proteome}/hpc/env/rms_proteome_hpc.env.sh"
rms_proteome_load_modules || true

missing=0

check_file() {
  local path="$1"
  if [[ ! -e "$path" ]]; then
    printf '[MISSING] %s\n' "$path" >&2
    missing=1
  else
    printf '[OK] %s\n' "$path"
  fi
}

check_dir() {
  local path="$1"
  if [[ ! -d "$path" ]]; then
    printf '[MISSING DIR] %s\n' "$path" >&2
    missing=1
  else
    printf '[OK DIR] %s\n' "$path"
  fi
}

check_tool() {
  local tool="$1"
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf '[MISSING TOOL] %s\n' "$tool" >&2
    missing=1
  else
    printf '[OK TOOL] %s -> %s\n' "$tool" "$(command -v "$tool")"
  fi
}

check_tool bash
check_tool wget
check_tool python3
check_tool java

if command -v bsub >/dev/null 2>&1; then
  printf '[OK TOOL] %s -> %s\n' "bsub" "$(command -v bsub)"
else
  printf '[WARN] bsub not found in current shell. Submit wrappers will not work until LSF is available.\n'
fi

check_dir "$RMS_PROTEOME_ROOT"
check_dir "$RMS_PROTEOME_DOWNLOADS_ROOT"
check_dir "$RMS_PROTEOME_LOGROOT"
check_dir "$RMS_PROTEOME_TMPROOT"

check_file "$RMS_PROTEOME_ROOT/scripts/tmt_ccle_depmap/08_build_hpc_download_manifests.py"
check_file "$RMS_PROTEOME_ROOT/scripts/tmt_ccle_depmap/09_prepare_msv000085836_hpc_mirror.sh"
check_file "$RMS_PROTEOME_ROOT/metadata/tmt_ccle_depmap/massive/MSV000085836_index.tsv"
check_file "$RMS_PROTEOME_ROOT/metadata/tmt_ccle_depmap/pride/PXD030304_files.tsv"
check_file "$RMS_PROTEOME_ROOT/scripts/tmt_ccle_depmap/12_prepare_msv000085836_fragger_search.py"
check_file "$RMS_PROTEOME_ROOT/scripts/tmt_ccle_depmap/13_extract_msv000085836_fragger_targets.py"

if [[ -n "${RMS_PROTEOME_MSFRAGGER_JAR:-}" ]]; then
  check_file "$RMS_PROTEOME_MSFRAGGER_JAR"
fi

if [[ -n "${RMS_PROTEOME_PHILOSOPHER_BIN:-}" ]]; then
  check_file "$RMS_PROTEOME_PHILOSOPHER_BIN"
fi

printf '\nDerived paths\n'
printf '  RMS_PROTEOME_ROOT=%s\n' "$RMS_PROTEOME_ROOT"
printf '  RMS_PROTEOME_DOWNLOADS_ROOT=%s\n' "$RMS_PROTEOME_DOWNLOADS_ROOT"
printf '  RMS_PROTEOME_LOGROOT=%s\n' "$RMS_PROTEOME_LOGROOT"
printf '  RMS_PROTEOME_TMPROOT=%s\n' "$RMS_PROTEOME_TMPROOT"
printf '  RMS_PROTEOME_MANIFEST_DIR=%s\n' "$RMS_PROTEOME_MANIFEST_DIR"

if [[ "$missing" -ne 0 ]]; then
  printf '\nEnvironment check failed.\n' >&2
  exit 1
fi

printf '\nEnvironment check passed.\n'
