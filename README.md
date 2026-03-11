# rms_proteome

Reproducible proteomics workflow starter for rhabdomyosarcoma (RMS) analysis.

## Goal

1. Download and organize data for ProteomeXchange dataset `PXD039480`.
2. Quantify evidence for `MYMK`, `MYMX`, and additional proteins encoded by genes listed in `ann.genes.sheets.csv`.
3. Keep full provenance (pre-download file manifest + metadata) from day zero.

## Why this skeleton

The review in `review.txt` prioritizes:
- Starting with `PXD039480` (RMS models + myoblast controls, membrane/surface-enriched).
- Using peptide-level evidence (critical for low-abundance membrane targets like MYMK/MYMX).
- Building reproducible metadata early to avoid ambiguous downstream analysis.

## Repository layout

- `config/`: dataset and target settings.
- `data/surfaceome/PXD039480/`: current downloaded + derived surfaceome files.
- `data/tmt/`: scaffold for CCLE deep mass-spec (MSV000085836) + DepMap transcriptomics.
- `scripts/surfaceome_pxd039480/`: current analysis scripts for the surfaceome dataset.
- `scripts/tmt_ccle_depmap/`: placeholder for upcoming TMT/DepMap pipeline code.
- `metadata/`: manifests and metadata grouped by data modality.
- `docs/`: protocol and decision notes.
- `analysis/`: notebooks and analysis code.
- `results/`: outputs grouped by data modality.

## Scope note on normal muscle

Adult normal skeletal muscle references (`PXD011967`, `PXD034908`) were considered for context but are removed from the active plan.

Reason: adult muscle is not expected to robustly express `MYMK`/`MYMX`, so these datasets are weak comparators for those targets. If normal developmental context is needed later, prioritize fetal/embryonic muscle proteomics references if available.

## Quick start

```bash
git init
python3 scripts/surfaceome_pxd039480/01_build_predownload_manifest_pxd039480.py --project PXD039480 --outdir metadata/surfaceome_pxd039480
```

## Next immediate steps

1. Review `metadata/surfaceome_pxd039480/download_manifest_pxd039480.tsv` before download.
2. Build sample sheet for `PXD039480` in `metadata/samples.pxd039480.tsv`.
3. Add first extraction script for MYMK/MYMX peptide/protein hits.
