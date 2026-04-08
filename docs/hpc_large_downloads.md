# HPC Large Downloads

This note records the current plan for large-file transfers that should happen on HPC scratch rather than the local workstation.

## Why HPC

- `MSV000085836` raw TMT data will require recursive mirroring from MassIVE.
- `PXD030304` already enumerates to multi-terabyte scale in PRIDE metadata.
- These are not reasonable local-workstation downloads.

## Current large-file targets

### `MSV000085836` (MassIVE)

- Purpose: go beyond the processed harmonized proteomics proxy.
- Reason: `MYMK` and `MYMX` were absent from the processed matrix, which may reflect filtering rather than true absence.
- Local limitation: our local MassIVE index is only one level deep.
- HPC action: mirror these roots recursively:
  - `ftp://massive-ftp.ucsd.edu/v03/MSV000085836/metadata/`
  - `ftp://massive-ftp.ucsd.edu/v03/MSV000085836/sequence/`
  - `ftp://massive-ftp.ucsd.edu/v03/MSV000085836/raw/raw/`

Prepared helper:
- [09_prepare_msv000085836_hpc_mirror.sh](/home/yahya/Scripts/rms_proteome/scripts/tmt_ccle_depmap/09_prepare_msv000085836_hpc_mirror.sh)

### `PXD030304` (PRIDE)

- Local PRIDE file manifest is complete.
- Current total enumerated size: about `4.08 TB`.
- File count: `287`.
- Mostly `RAW` `.zip` archives, plus a very large DIA-NN `.tsv`.

Prepared manifests:
- [PXD030304_raw_manifest.tsv](/home/yahya/Scripts/rms_proteome/metadata/tmt_ccle_depmap/hpc_downloads/PXD030304_raw_manifest.tsv)
- [PXD030304_large_files_manifest.tsv](/home/yahya/Scripts/rms_proteome/metadata/tmt_ccle_depmap/hpc_downloads/PXD030304_large_files_manifest.tsv)
- [PXD030304_wget_commands.txt](/home/yahya/Scripts/rms_proteome/metadata/tmt_ccle_depmap/hpc_downloads/PXD030304_wget_commands.txt)
- [PXD030304_aspera_commands.txt](/home/yahya/Scripts/rms_proteome/metadata/tmt_ccle_depmap/hpc_downloads/PXD030304_aspera_commands.txt)

## Important analysis note

These downloads should be treated as escalation paths, not default inputs.

- `MSV000085836` raw download is justified because the processed matrix dropped `MYMK` and `MYMX`.
- `PXD030304` large-file download is lower priority and should only be revisited if we decide the current processed-matrix limitation is not acceptable.
