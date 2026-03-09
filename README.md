# rms_proteome

Reproducible proteomics workflow starter for rhabdomyosarcoma (RMS) analysis.

## Goal

1. Download and organize data for ProteomeXchange dataset `PXD039480`.
2. Quantify evidence for `MYMK`, `MYMX`, and additional proteins encoded by genes listed in `ann.genes.sheets.csv`.
3. Keep full provenance (file manifest + metadata) from day zero.

## Why this skeleton

The review in `review.txt` prioritizes:
- Starting with `PXD039480` (RMS models + myoblast controls, membrane/surface-enriched).
- Using peptide-level evidence (critical for low-abundance membrane targets like MYMK/MYMX).
- Building reproducible metadata early to avoid ambiguous downstream analysis.

## Repository layout

- `config/`: dataset and target settings.
- `data/`: raw/interim/processed data (raw kept out of git by default).
- `scripts/`: small, commented helper scripts.
- `metadata/`: machine-readable snapshots of tracked files.
- `docs/`: protocol and decision notes.
- `analysis/`: notebooks and analysis code.
- `results/`: figures/tables/reports.

## Quick start

```bash
git init
python3 scripts/00_build_manifest.py --root . --outdir metadata
```

## Next immediate steps

1. Build sample sheet for `PXD039480` in `metadata/samples.pxd039480.tsv`.
2. Add a data download script with a dry-run mode.
3. Add first extraction script for MYMK/MYMX peptide/protein hits.
