#!/usr/bin/env python3
"""
Extract requested target proteins from the local PXD030304/DepMap harmonized proteomics matrix.

This uses the already-downloaded harmonized public proteomics matrix rather than the
237 GB DIA-NN search output from PRIDE. That is the practical first-pass route.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


TARGETS = {
    "MYMK": "A6NI61",
    "MYMX": "A0A1B0GTQ4",
    "MYOD1": "P15172",
    "MYOG": "P15173",
}


def load_model_rows(path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(path.open("r", encoding="utf-8", newline=""), delimiter="\t"))
    return [r for r in rows if r.get("matched_model_id")]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--proteomics",
        default="metadata/tmt_ccle_depmap/pxd030304_depmap/harmonized_MS_CCLE_Gygi_24Q4.csv",
    )
    parser.add_argument(
        "--model_availability",
        default="metadata/tmt_ccle_depmap/pxd030304_depmap/PXD030304_requested_models_modality_availability.tsv",
    )
    parser.add_argument(
        "--out_tsv",
        default="results/tmt_ccle_depmap/PXD030304_harmonized_4target_requested_models.tsv",
    )
    parser.add_argument(
        "--out_json",
        default="results/tmt_ccle_depmap/PXD030304_harmonized_4target_summary.json",
    )
    args = parser.parse_args()

    proteomics_path = Path(args.proteomics)
    model_path = Path(args.model_availability)
    out_tsv = Path(args.out_tsv)
    out_json = Path(args.out_json)
    out_tsv.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)

    model_rows = load_model_rows(model_path)

    with proteomics_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        target_col_idx = {gene: header.index(acc) for gene, acc in TARGETS.items() if acc in header}
        matrix_rows = {row[0]: row for row in reader if row and row[0]}

    out_rows: list[dict[str, str]] = []
    for model in model_rows:
        model_id = model["matched_model_id"]
        matrix_row = matrix_rows.get(model_id)
        for gene, accession in TARGETS.items():
            present_in_matrix = gene in target_col_idx
            raw_value = ""
            detected = "False"
            if present_in_matrix and matrix_row is not None:
                idx = target_col_idx[gene]
                if idx < len(matrix_row):
                    raw_value = matrix_row[idx]
                    detected = "True" if raw_value != "" else "False"

            out_rows.append(
                {
                    "requested_model": model["requested_model"],
                    "matched_model_id": model_id,
                    "matched_ccle_name": model["matched_ccle_name"],
                    "gene": gene,
                    "uniprot_accession": accession,
                    "present_as_matrix_column": str(present_in_matrix),
                    "detected_in_requested_model": detected,
                    "harmonized_value": raw_value,
                }
            )

    with out_tsv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out_rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(out_rows)

    present_targets = [g for g in TARGETS if g in target_col_idx]
    absent_targets = [g for g in TARGETS if g not in target_col_idx]
    per_target_detected_models: dict[str, int] = {}
    for gene in TARGETS:
        per_target_detected_models[gene] = sum(
            1 for row in out_rows if row["gene"] == gene and row["detected_in_requested_model"] == "True"
        )

    summary = {
        "proteomics_matrix": str(proteomics_path),
        "requested_models_with_matches": len(model_rows),
        "targets_present_as_matrix_columns": present_targets,
        "targets_absent_as_matrix_columns": absent_targets,
        "detected_requested_model_counts": per_target_detected_models,
        "notes": [
            "Matrix columns are UniProt accessions.",
            "Blank values mean no harmonized proteomics value for that model/protein.",
            "Absence from matrix columns means the protein is not represented in this processed harmonized release, not merely missing in selected RMS models.",
        ],
    }
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Wrote TSV: {out_tsv}")
    print(f"Wrote JSON: {out_json}")


if __name__ == "__main__":
    main()
