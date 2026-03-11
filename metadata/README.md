# Metadata Folder

This folder stores reproducible metadata artifacts.

## Surfaceome (`PXD039480`)

- `surfaceome_pxd039480/download_manifest_pxd039480.tsv`: file list from PRIDE before download.
- `surfaceome_pxd039480/download_manifest_pxd039480.json`: same information in JSON format.

Generate with:

```bash
python3 scripts/surfaceome_pxd039480/01_build_predownload_manifest_pxd039480.py --project PXD039480 --outdir metadata/surfaceome_pxd039480
```

## Future data lanes (folders created)

- `tmt_ccle_depmap/`: for CCLE TMT proteomics (`MSV000085836`) + DepMap RNA integration metadata.
- `normal_muscle/`: retained only as an archival placeholder; adult normal muscle references (`PXD011967`, `PXD034908`) are not in the active `MYMK`/`MYMX` plan.
