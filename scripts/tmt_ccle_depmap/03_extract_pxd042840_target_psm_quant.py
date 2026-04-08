#!/usr/bin/env python3
"""
Extract target-linked PSM-level quantitative support from PXD042840 .msf files.

Important limitation:
- These .msf files do not expose a clean protein-level abundance table.
- We therefore extract PSM-level values and define an abundance proxy:
  PrecursorAbundance if present and > 0, otherwise raw PSM Intensity.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path


TARGETS = {
    "MYMK": "A6NI61",
    "MYMX": "A0A1B0GTQ4",
    "MYOD1": "P15172",
    "MYOG": "P15173",
}

CONDITION_BY_FILE = {
    "blank.msf": "blank",
    "EV71.msf": "EV71",
    "EV71_PZH.msf": "EV71_PZH",
}


def extract_rows(msf_path: Path) -> list[dict[str, str]]:
    condition = CONDITION_BY_FILE.get(msf_path.name, msf_path.stem)
    con = sqlite3.connect(msf_path)
    cur = con.cursor()

    out: list[dict[str, str]] = []
    for gene, accession in TARGETS.items():
        cur.execute(
            """
            SELECT
                t.Accession,
                t.Description,
                p.WorkflowID,
                p.PeptideID,
                p.Sequence,
                p.ModifiedSequence,
                p.Charge,
                p.SpectrumFileName,
                p.FirstScan,
                p.RetentionTime,
                p.Intensity,
                p.PrecursorAbundance,
                p.PercolatorqValue,
                p.MatchConfidence,
                p.XCorr,
                p.IdentifyingNodeName
            FROM TargetPsms p
            JOIN TargetProteinsTargetPsms tp
              ON tp.TargetPsmsPeptideID = p.PeptideID
             AND tp.TargetPsmsWorkflowID = p.WorkflowID
            JOIN TargetProteins t
              ON t.UniqueSequenceID = tp.TargetProteinsUniqueSequenceID
            WHERE t.Accession = ?
            ORDER BY p.FirstScan, p.PeptideID
            """,
            (accession,),
        )

        for row in cur.fetchall():
            (
                acc,
                description,
                workflow_id,
                peptide_id,
                sequence,
                modified_sequence,
                charge,
                spectrum_file_name,
                first_scan,
                retention_time,
                intensity,
                precursor_abundance,
                percolator_qvalue,
                match_confidence,
                xcorr,
                node_name,
            ) = row

            proxy_value = precursor_abundance if precursor_abundance not in (None, 0) else intensity
            proxy_source = "PrecursorAbundance" if precursor_abundance not in (None, 0) else "Intensity"

            out.append(
                {
                    "condition": condition,
                    "msf_file": msf_path.name,
                    "gene": gene,
                    "accession": acc or "",
                    "description": description or "",
                    "workflow_id": str(workflow_id),
                    "peptide_id": str(peptide_id),
                    "sequence": sequence or "",
                    "modified_sequence": modified_sequence or "",
                    "charge": "" if charge is None else str(charge),
                    "spectrum_file_name": spectrum_file_name or "",
                    "first_scan": "" if first_scan is None else str(first_scan),
                    "retention_time": "" if retention_time is None else str(retention_time),
                    "intensity": "" if intensity is None else str(intensity),
                    "precursor_abundance": "" if precursor_abundance is None else str(precursor_abundance),
                    "abundance_proxy": "" if proxy_value is None else str(proxy_value),
                    "abundance_proxy_source": proxy_source,
                    "percolator_qvalue": "" if percolator_qvalue is None else str(percolator_qvalue),
                    "match_confidence": "" if match_confidence is None else str(match_confidence),
                    "xcorr": "" if xcorr is None else str(xcorr),
                    "identifying_node_name": node_name or "",
                }
            )

    con.close()
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--indir",
        default="data/tmt_ccle_depmap/PXD042840/processed",
        help="Directory containing downloaded .msf files",
    )
    parser.add_argument(
        "--out",
        default="results/tmt_ccle_depmap/PXD042840_target_psm_quant.tsv",
        help="Output TSV for target-linked PSM quant support",
    )
    args = parser.parse_args()

    indir = Path(args.indir)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    for msf_path in sorted(indir.glob("*.msf")):
        rows.extend(extract_rows(msf_path))

    if not rows:
        raise SystemExit(f"No target-linked rows extracted from {indir}")

    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
