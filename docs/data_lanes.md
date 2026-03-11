# Data Lanes

This project now uses modality-specific lanes so analyses do not get mixed.

## 1) Surfaceome (active)

- Dataset: `PXD039480`
- Data: `data/surfaceome/PXD039480/`
- Scripts: `scripts/surfaceome_pxd039480/`
- Metadata: `metadata/surfaceome_pxd039480/`
- Results: `results/surfaceome_pxd039480/`

## 2) TMT + DepMap (planned)

- Datasets: `MSV000085836` (CCLE TMT), `depmap_transcriptomics`
- Data: `data/tmt/MSV000085836/`, `data/tmt/depmap_transcriptomics/`
- Scripts: `scripts/tmt_ccle_depmap/`
- Metadata: `metadata/tmt_ccle_depmap/`
- Results: `results/tmt_ccle_depmap/`

## 3) Adult normal muscle references (deprioritized)

- Considered datasets: `PXD011967`, `PXD034908`
- Status: removed from active plan for `MYMK`/`MYMX` benchmarking.
- Reason: adult skeletal muscle is not expected to robustly express these developmental fusion factors.
- If normal reference is added later, prioritize fetal/embryonic muscle datasets.

This separation is intentional: each lane should keep its own manifests, processing scripts, and outputs.
