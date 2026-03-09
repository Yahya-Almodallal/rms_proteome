# Metadata Folder

This folder stores reproducible metadata artifacts.

## Pre-download manifest (remote inventory)

- `download_manifest_pxd039480.tsv`: file list from PRIDE before download.
- `download_manifest_pxd039480.json`: same information in JSON format.

Generate with:

```bash
python3 scripts/01_build_predownload_manifest_pxd039480.py --project PXD039480 --outdir metadata
```
