# Proteomics Paths: Surfaceome vs TMT

## Why two paths

This project has two complementary proteomics paths:

1. **Surfaceome path** (`PXD039480`): membrane/surface-enriched RMS study, best for difficult membrane targets (for example MYMK/MYMX).
2. **TMT path** (CCLE + DepMap): broad whole-proteome benchmarking inside RMS models.

These paths are intentionally separated because they answer different questions and use different measurement designs.

## What we already completed (Surfaceome path)

Scope completed so far: `PXD039480` only.

- Downloaded all files listed in the pre-download manifest and checksum-verified them.
- Extracted target rows from processed table (`proteinGroups cleaned`) for:
  - `MYMK`, `MYMX`, `ADGRL2`, `JAM3`, `L1CAM`
- Generated a two-panel figure:
  - Main panel: replicate-level abundance distribution using `log2(Top3/iTop3)` style values.
  - Second panel: detection-frequency panel (to avoid hiding sparse detection of proteins like `MYMK`).

Key outputs:

- Figure: `results/surfaceome_pxd039480/target_abundance_detection_itop3.png`
- Long-format table for plotting/statistics: `results/surfaceome_pxd039480/target_abundance_detection_itop3_long.tsv`
- Extracted targets table: `results/surfaceome_pxd039480/targets_pxd039480_proteinGroups_cleaned.tsv`
- Summary JSON: `results/surfaceome_pxd039480/targets_pxd039480_summary.json`

## TMT path goal (next phase)

Primary genes for this phase:

- `MYMK`, `MYMX`, `MYOD1`, `MYOG`

Questions to answer:

1. How often is each protein detected?
2. At what relative abundance is each observed?
3. Do FP-RMS and FN-RMS differ?
4. How do FP-RMS and FN-RMS compare in an RMS-focused framework?

Data sources:

- **Proteomics**:
  - `MSV000085836` (CCLE deep TMT proteomics)
- **RNA**:
  - DepMap transcriptomics (for RNA-protein concordance in RMS lines)

Normal-muscle note:
- Adult skeletal-muscle cohorts (`PXD011967`, `PXD034908`) were considered and then removed from the active plan.
- Rationale: adult muscle is not expected to strongly express `MYMK`/`MYMX`.
- If external normal reference is needed later, prioritize fetal/embryonic muscle datasets.

## Critical design rule

Do **not** directly mix raw abundance values across different proteomics platforms/dataset designs.

- Different specimen types + different platforms => raw absolute intensities are not directly comparable.

This is an inference from the dataset designs and should be treated as a pre-registered analysis constraint.

## TMT execution plan (succinct)

1. **Download processed tables first**
   - CCLE/DepMap normalized proteomics + cell line metadata + DepMap RNA.
   - Use raw/peptide-level files only if a key target is missing in processed tables.

2. **Curate RMS lines and fusion status**
   - Pull all RMS lines from CCLE/DepMap metadata.
   - Manually annotate each as FP or FN with metadata + literature cross-check.
   - Do not infer fusion status from subtype labels without verification.

3. **Harmonize identifiers**
   - Convert protein IDs to HGNC symbols.
   - Keep primary targets (`MYMK`, `MYMX`, `MYOD1`, `MYOG`) for first-pass analysis.
   - Build a tidy target table with columns:
     - `dataset, sample_id, sample_type, model_class, fusion_status, gene_symbol, detected, abundance_value`
   - Keep RNA in parallel table (e.g., log2(TPM+1) or DepMap standard metric).

4. **Define detection consistently**
   - Detected = non-missing quantitative value in processed matrix.
   - Never interpret non-detected as biological zero.
   - Compute detection % per target for:
     - FP-RMS, FN-RMS, RMS overall.

5. **Define abundance comparison**
   - Within each dataset: log2 transform if needed, then standardize per protein (z-score or percentile rank).
   - For FP-vs-FN RMS within CCLE, native normalized CCLE values are acceptable.

6. **Run core statistics**
   - Detection: Fisher exact test (FP vs FN).
   - Abundance among detected samples: Wilcoxon rank-sum.

7. **Add RNA-protein concordance (RMS lines only)**
   - Spearman correlation per gene between CCLE protein abundance and DepMap RNA expression.

8. **Produce minimum outputs**
   - Detection table (genes x cohorts).
   - Per-gene abundance plot across FP-RMS and FN-RMS.
   - RNA-protein scatter per gene across RMS lines.
   - Summary table: `n_detected/N`, median abundance among detected, p-values.

## Interpretation guardrails

- `MYOD1` and `MYOG` are expected to be easier to detect than `MYMK`/`MYMX`.
- For `MYMK`/`MYMX`, transcript may be present without robust protein detection.
- If RNA exists but protein is sparse, interpret as **low proteomic detectability**, not biological absence.
