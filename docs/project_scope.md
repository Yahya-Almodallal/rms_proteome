# Project Scope (v0)

## Primary question

Do RMS samples show detectable/changed abundance for MYMK, MYMX, and selected gene products compared with controls?

## Dataset priority

1. `PXD039480` is complete for the current first-pass surfaceome analysis.
2. `PXD042840` is complete for now as a small RD-condition reference accession.
3. `PXD030304` was reviewed and skipped for now: only `RH-41` showed processed `MYOD1`/`MYOG`, `MYMK`/`MYMX` were absent from the processed matrices, and the `237 GB` PRIDE output was not inspected for convenience.
4. `MSV000085836` was reviewed through the processed harmonized proteomics matrix: `MYMK`/`MYMX` were absent from the matrix columns, while `MYOD1`/`MYOG` were detected only in `RH-30` and `RH-41`; raw TMT reprocessing is deferred for now.
5. `depmap_transcriptomics` is now the active next-stage resource.
6. Adult normal muscle references (`PXD011967`, `PXD034908`) were considered but removed from the active plan for `MYMK`/`MYMX`; if a normal comparator is needed later, prioritize fetal/embryonic muscle resources.

## Core analysis rules

- Track peptide-level evidence before making strong protein-level claims.
- Treat missingness carefully (non-detection is not proof of absence).
- Keep explicit metadata for runs, conditions, and processing choices.
