#!/usr/bin/env bash
set -euo pipefail

source "${RMS_PROTEOME_ROOT:-/users/almrb2/rms_proteome}/hpc/env/rms_proteome_hpc.env.sh"

MANIFEST="${1:-${RMS_PROTEOME_MANIFEST_DIR}/MSV000085836_target_plex_local_manifest.tsv}"
DEST_ROOT="${2:-${RMS_PROTEOME_DOWNLOADS_ROOT}/MSV000085836_target_subset}"

if [[ ! -s "$MANIFEST" ]]; then
  echo "Manifest not found: $MANIFEST" >&2
  exit 1
fi

mkdir -p "$DEST_ROOT/raw"

awk -F '\t' 'NR>1 {print $1 "\t" $8}' "$MANIFEST" | while IFS=$'\t' read -r cell_line local_path; do
  [[ -z "$local_path" ]] && continue
  cell_dir="${DEST_ROOT}/raw/${cell_line}"
  mkdir -p "$cell_dir"
  ln -sfn "$local_path" "${cell_dir}/$(basename "$local_path")"
done

find "$DEST_ROOT/raw" -type l | sort
