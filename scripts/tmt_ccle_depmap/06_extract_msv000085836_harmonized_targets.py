#!/usr/bin/env python3
"""
Extract the 4 core target proteins for the MSV000085836 cell-line subset.

Why this script exists:
- The raw MassIVE accession is large and not the right starting point.
- We already have a processed proxy locally: the DepMap harmonized CCLE/Gygi
  proteomics matrix.
- That matrix is keyed by UniProt accession, not gene symbol, so the mapping
  is explicit below.

Current limitation:
- In the local harmonized matrix, MYMK and MYMX are absent as columns.
- Therefore this script can report them as "not represented in the matrix",
  but it cannot recover them from raw files.
"""

from __future__ import annotations

import csv
import json
from collections import OrderedDict
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[2]

MSV_SAMPLE_MAP = ROOT / "metadata/tmt_ccle_depmap/msv000085836/MSV000085836_requested_cell_lines.tsv"
MODEL_TABLE = ROOT / "metadata/tmt_ccle_depmap/pxd030304_depmap/Model_24Q4.csv"
PROTEOMICS_MATRIX = ROOT / "metadata/tmt_ccle_depmap/pxd030304_depmap/harmonized_MS_CCLE_Gygi_24Q4.csv"

OUT_TABLE = ROOT / "results/tmt_ccle_depmap/MSV000085836_harmonized_4target_requested_lines.tsv"
OUT_SUMMARY = ROOT / "results/tmt_ccle_depmap/MSV000085836_harmonized_4target_summary.json"

# UniProt accessions were chosen from prior direct proteomics hits and canonical
# protein identifiers for the 4 targets used throughout this project.
TARGET_ACCESSIONS = OrderedDict(
    [
        ("MYMK", "A6NI61"),
        ("MYMX", "A0A1B0GTQ4"),
        ("MYOD1", "P15172"),
        ("MYOG", "P15173"),
    ]
)


def load_requested_lines(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def load_models_by_ccle(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as handle:
        return {row["CCLEName"]: row for row in csv.DictReader(handle)}


def load_proteomics_matrix(path: Path) -> tuple[dict[str, int], dict[str, list[str]]]:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        column_index = {name: i for i, name in enumerate(header)}
        rows_by_model = {row[0]: row for row in reader}
    return column_index, rows_by_model


def main() -> None:
    requested_lines = load_requested_lines(MSV_SAMPLE_MAP)
    models_by_ccle = load_models_by_ccle(MODEL_TABLE)
    column_index, proteomics_rows = load_proteomics_matrix(PROTEOMICS_MATRIX)

    OUT_TABLE.parent.mkdir(parents=True, exist_ok=True)

    out_rows: list[dict[str, str]] = []
    summary: dict[str, dict[str, object]] = {
        gene: {
            "accession": accession,
            "column_present": accession in column_index,
            "detected_lines": 0,
            "values": [],
        }
        for gene, accession in TARGET_ACCESSIONS.items()
    }

    for requested in requested_lines:
        model = models_by_ccle.get(requested["CCLE Code"], {})
        model_id = model.get("ModelID", "")
        proteomics_row = proteomics_rows.get(model_id)

        for gene_symbol, accession in TARGET_ACCESSIONS.items():
            value = ""
            detected = False

            if accession in column_index and proteomics_row is not None:
                value = proteomics_row[column_index[accession]]
                detected = value not in {"", "NA", "NaN", "nan"}

            out_rows.append(
                {
                    "requested_name": requested["requested_name"],
                    "cell_line": requested["Cell Line"],
                    "ccle_code": requested["CCLE Code"],
                    "protein_10plex_id": requested["Protein 10-Plex ID"],
                    "protein_tmt_label": requested["Protein TMT Label"],
                    "model_id": model_id,
                    "oncotree_subtype": model.get("OncotreeSubtype", ""),
                    "gene_symbol": gene_symbol,
                    "uniprot_accession": accession,
                    "column_present_in_harmonized_matrix": str(accession in column_index),
                    "detected_nonmissing_value": str(detected),
                    "harmonized_value": value,
                }
            )

            if detected:
                summary[gene_symbol]["detected_lines"] += 1
                summary[gene_symbol]["values"].append(float(value))

    with OUT_TABLE.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out_rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(out_rows)

    for gene_symbol, gene_summary in summary.items():
        values = gene_summary.pop("values")
        gene_summary["n_requested_lines"] = len(requested_lines)
        gene_summary["median_harmonized_value"] = median(values) if values else None

    summary_payload = {
        "source_proteomics_matrix": str(PROTEOMICS_MATRIX.relative_to(ROOT)),
        "source_model_table": str(MODEL_TABLE.relative_to(ROOT)),
        "source_msv_sample_map": str(MSV_SAMPLE_MAP.relative_to(ROOT)),
        "note": (
            "Uses the local DepMap harmonized CCLE/Gygi proteomics matrix (24Q4) "
            "as a processed proxy for MSV000085836. MYMK and MYMX are absent from "
            "the harmonized matrix columns; MYOD1 and MYOG are present."
        ),
        "summary": summary,
    }

    with OUT_SUMMARY.open("w") as handle:
        json.dump(summary_payload, handle, indent=2)

    print(OUT_TABLE)
    print(OUT_SUMMARY)


if __name__ == "__main__":
    main()
