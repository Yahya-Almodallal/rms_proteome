# rms_proteome

Reproducible proteomics workflow starter for rhabdomyosarcoma (RMS) analysis.

## Goal

1. Quantify evidence and expression for `MYMK`, `MYMX`, `MYOD1`, and `MYOG` across prioritized RMS proteomics datasets.
2. Keep full provenance (pre-download file manifest + metadata) from day zero.
3. Preserve completed first-pass outputs while moving incrementally across accessions.

## Why this skeleton

The review in `review.txt` prioritizes:
- Starting with `PXD039480` (RMS models + myoblast controls, membrane/surface-enriched).
- Using peptide-level evidence (critical for low-abundance membrane targets like MYMK/MYMX).
- Building reproducible metadata early to avoid ambiguous downstream analysis.

Current status:
- `PXD039480`: done for now.
- `PXD042840`: done for now.
- `PXD030304`: reviewed and skipped for now.
- `MSV000085836`: done for now, with processed-matrix limitations recorded.
- `depmap_transcriptomics`: active.

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

1. Work on `depmap_transcriptomics` as the active next resource for RNA support and RNA-protein concordance.
2. Keep `MSV000085836` as a limited processed-proteomics result: `MYMK`/`MYMX` were absent from the harmonized matrix, and raw reprocessing is deferred.
3. Preserve `PXD039480` and `PXD042840` as completed reference accessions.

## Scope note on MSV000085836

For `MSV000085836`, we used the local processed DepMap harmonized CCLE/Gygi proteomics matrix as the practical first-pass resource.

Result:
- `MYMK` and `MYMX` were not present as columns in the harmonized matrix.
- `MYOD1` and `MYOG` were detected only in `RH-30` and `RH-41` among the 5 requested lines (`A-204`, `RD`, `RH-41`, `RH-30`, `KYM-1`).

Limitation:
- this is a processed-matrix result, not a raw-file reanalysis
- low-observability targets such as `MYMK`/`MYMX` may have been filtered out during harmonization
- raw TMT reprocessing is deferred for now because it is a substantially heavier workflow
