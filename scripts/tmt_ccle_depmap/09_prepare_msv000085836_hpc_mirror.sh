#!/usr/bin/env bash
set -euo pipefail

# Mirror the large MSV000085836 accession onto HPC scratch.
#
# Why this script mirrors directories instead of using a file manifest:
# - our local MassIVE metadata crawl was intentionally shallow
# - the actual raw files live under raw/raw/ and need recursive listing
# - HPC scratch is the right place to do that large transfer
#
# Usage:
#   bash 09_prepare_msv000085836_hpc_mirror.sh /scratch/$USER/rms_proteome/MSV000085836

DEST_ROOT="${1:-$PWD/MSV000085836}"

ACC="MSV000085836"
BASE_FTP="ftp://massive-ftp.ucsd.edu/v03/${ACC}"

mkdir -p "${DEST_ROOT}"/{metadata,sequence,raw}

echo "Mirroring metadata/"
wget -m -np -nH --cut-dirs=4 -R "index.html*" -P "${DEST_ROOT}/metadata" "${BASE_FTP}/metadata/"

echo "Mirroring sequence/"
wget -m -np -nH --cut-dirs=4 -R "index.html*" -P "${DEST_ROOT}/sequence" "${BASE_FTP}/sequence/"

echo "Mirroring raw/raw/ recursively"
wget -m -np -nH --cut-dirs=4 -R "index.html*" -P "${DEST_ROOT}/raw" "${BASE_FTP}/raw/raw/"

echo "Finished mirror into: ${DEST_ROOT}"
