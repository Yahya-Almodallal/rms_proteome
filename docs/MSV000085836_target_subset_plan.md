# MSV000085836 Target Subset Plan

This note records the minimal next-step plan for the raw `MSV000085836` download.

## Which raw files matter first

We are not starting from all `552` raw files.

We are starting from the five TMT plexes that contain the lines of interest:

- `A-204` -> `Protein 10-Plex ID 23`
- `RD` -> `Protein 10-Plex ID 25`
- `RH-41` -> `Protein 10-Plex ID 27`
- `RH-30` -> `Protein 10-Plex ID 35`
- `KYM-1` -> `Protein 10-Plex ID 38`

Each of those plexes has `12` fractionated raw files, so the first-pass target subset is:

- `60` raw files total

The generated manifest is:
- [MSV000085836_target_plex_raw_manifest.tsv](/home/yahya/Scripts/rms_proteome/metadata/tmt_ccle_depmap/hpc_downloads/MSV000085836_target_plex_raw_manifest.tsv)

The summary by line/plex is:
- [MSV000085836_target_plex_summary.tsv](/home/yahya/Scripts/rms_proteome/metadata/tmt_ccle_depmap/hpc_downloads/MSV000085836_target_plex_summary.tsv)

## Minimal downstream search strategy

The goal is not a full reanalysis of all CCLE lines.

The goal is to answer a narrow question for:
- `MYMK`
- `MYMX`
- `MYOD1`
- `MYOG`

### Practical first pass

1. Restrict processing to the `60` raw files from the 5 plexes above.
2. Search them with the accession FASTA already mirrored from `sequence/`.
3. Produce peptide- and protein-level outputs.
4. Inspect the four target proteins at both levels.

### What to trust most

For `MYMK` and `MYMX`, protein-level absence after harmonization is not enough.

The first reliable evidence to look for is:
- unique peptide identifications
- PSM support quality
- consistency across multiple fractions within the relevant plex

### Minimal outputs we need

For each of the four genes:

- whether any peptide/PSM was identified
- how many fractions contain supporting evidence
- whether protein-level inference exists
- quantitative support if the search workflow provides TMT reporter intensities or protein abundance tables

### Interpretation rule

- `MYOD1` and `MYOG` are expected to be easier to recover.
- `MYMK` and `MYMX` may require peptide-level inspection even if protein-level summaries remain sparse.

## Immediate HPC use

After the full mirror finishes, confirm the target subset exists:

```bash
awk -F '\t' 'NR>1 {print $6}' /users/almrb2/rms_proteome/metadata/tmt_ccle_depmap/hpc_downloads/MSV000085836_target_plex_raw_manifest.tsv | while read -r p; do
  test -f "/scratch/almrb2/rms.omics/proteomics/MSV000085836/raw/$(basename "$p")" && echo "[OK] $(basename "$p")" || echo "[MISSING] $(basename "$p")"
done
```

If those files are present, the next coding step should be a small helper that:
- reads the target manifest
- stages or lists only those `60` raw files
- prepares the input table for whichever search engine you use on the HPC
