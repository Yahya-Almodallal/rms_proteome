#!/usr/bin/env python3
"""
Extract DepMap transcriptomics for the 4 core targets.

Why this script is structured this way:
- The RNA matrix is large (~500 MB), so we read it once.
- The columns are labeled as "GENE (EntrezID)", not plain HGNC symbols.
- We want two outputs from the same pass:
  1. all RMS lines in DepMap 24Q4 for the 4 genes
  2. the 5 MSV000085836 requested lines, merged with processed proteomics

Fusion handling:
- We explicitly check the DepMap fusion file for PAX3/7--FOXO1 support.
- We do not infer fusion status from subtype names alone.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

MODEL_TABLE = ROOT / "metadata/tmt_ccle_depmap/pxd030304_depmap/Model_24Q4.csv"
MSV_REQUESTED = ROOT / "metadata/tmt_ccle_depmap/msv000085836/MSV000085836_requested_cell_lines.tsv"
RNA_MATRIX = ROOT / "data/tmt/depmap_transcriptomics/raw/OmicsExpressionProteinCodingGenesTPMLogp1_24Q4.csv"
FUSION_TABLE = ROOT / "metadata/tmt_ccle_depmap/depmap_24Q4/OmicsFusionFiltered_24Q4.csv"
PROTEOMICS_TABLE = ROOT / "results/tmt_ccle_depmap/MSV000085836_harmonized_4target_requested_lines.tsv"

OUT_RMS_RNA = ROOT / "results/tmt_ccle_depmap/depmap_24Q4_rms_4target_rna.tsv"
OUT_REQUESTED_MERGED = ROOT / "results/tmt_ccle_depmap/depmap_24Q4_msv_requested_4target_rna_protein.tsv"
OUT_SUMMARY = ROOT / "results/tmt_ccle_depmap/depmap_24Q4_4target_summary.json"

TARGET_HEADERS = {
    "MYMK": "MYMK (389827)",
    "MYMX": "MYMX (101929726)",
    "MYOD1": "MYOD1 (4654)",
    "MYOG": "MYOG (4656)",
}


def load_models(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as handle:
        return {row["ModelID"]: row for row in csv.DictReader(handle)}


def load_requested_lines(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def build_requested_model_lookup(
    requested_lines: list[dict[str, str]], models_by_id: dict[str, dict[str, str]]
) -> dict[str, dict[str, str]]:
    # We need a CCLEName -> ModelID lookup first, because the MSV table stores CCLE codes.
    ccle_to_model = {row["CCLEName"]: row for row in models_by_id.values() if row.get("CCLEName")}
    requested_by_model: dict[str, dict[str, str]] = {}
    for row in requested_lines:
        model = ccle_to_model.get(row["CCLE Code"])
        if model:
            requested_by_model[model["ModelID"]] = row
    return requested_by_model


def load_proteomics_table(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    with path.open(newline="") as handle:
        return {
            (row["requested_name"], row["gene_symbol"]): row
            for row in csv.DictReader(handle, delimiter="\t")
        }


def load_fusion_annotations(path: Path) -> tuple[dict[str, str], dict[str, list[str]]]:
    fusion_status_by_model: dict[str, str] = {}
    fusion_hits_by_model: dict[str, list[str]] = defaultdict(list)

    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            model_id = row["ModelID"]
            fusion_name = row["FusionName"]

            is_foxo1_fusion = (
                ("PAX3" in fusion_name and "FOXO1" in fusion_name)
                or ("PAX7" in fusion_name and "FOXO1" in fusion_name)
            )
            if is_foxo1_fusion:
                fusion_hits_by_model[model_id].append(fusion_name)

    for model_id, hits in fusion_hits_by_model.items():
        fusion_status_by_model[model_id] = "FOXO1_fusion_positive"

    return fusion_status_by_model, fusion_hits_by_model


def main() -> None:
    models_by_id = load_models(MODEL_TABLE)
    requested_lines = load_requested_lines(MSV_REQUESTED)
    requested_by_model = build_requested_model_lookup(requested_lines, models_by_id)
    proteomics_by_requested_gene = load_proteomics_table(PROTEOMICS_TABLE)
    fusion_status_by_model, fusion_hits_by_model = load_fusion_annotations(FUSION_TABLE)

    # Define the RMS set from the model table.
    rms_model_ids = {
        model_id
        for model_id, row in models_by_id.items()
        if "Rhabdomyosarcoma" in (row.get("OncotreeSubtype") or "")
    }

    OUT_RMS_RNA.parent.mkdir(parents=True, exist_ok=True)

    rms_rows: list[dict[str, str]] = []
    requested_merged_rows: list[dict[str, str]] = []
    summary = {
        "release": "DepMap Public 24Q4",
        "rna_matrix": str(RNA_MATRIX.relative_to(ROOT)),
        "fusion_table": str(FUSION_TABLE.relative_to(ROOT)),
        "n_rms_models": len(rms_model_ids),
        "targets": {gene: {"n_rms_detected_gt0": 0, "n_requested_lines_gt0": 0} for gene in TARGET_HEADERS},
        "notes": [
            "RNA values are DepMap log2(TPM+1)-style transcript expression from the 24Q4 release.",
            "Fusion status is based on explicit PAX3/7--FOXO1 calls in OmicsFusionFiltered, not on subtype labels alone.",
            "The proteomics side remains a processed-matrix proxy for MSV000085836, so RNA-protein discordance must be interpreted cautiously.",
        ],
    }

    with RNA_MATRIX.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        column_index = {name: i for i, name in enumerate(header)}

        for required_header in TARGET_HEADERS.values():
            if required_header not in column_index:
                raise KeyError(f"Missing expected RNA column: {required_header}")

        for row in reader:
            model_id = row[0]
            model = models_by_id.get(model_id)
            if not model:
                continue

            # First output: all RMS lines.
            if model_id in rms_model_ids:
                for gene_symbol, header_name in TARGET_HEADERS.items():
                    value = row[column_index[header_name]]
                    if value not in {"", "0.0", "0", "NA", "NaN", "nan"}:
                        summary["targets"][gene_symbol]["n_rms_detected_gt0"] += 1

                    rms_rows.append(
                        {
                            "model_id": model_id,
                            "cell_line": model.get("CellLineName", ""),
                            "ccle_name": model.get("CCLEName", ""),
                            "oncotree_subtype": model.get("OncotreeSubtype", ""),
                            "fusion_status": fusion_status_by_model.get(model_id, "no_PAX3_7_FOXO1_call_in_filtered_table"),
                            "fusion_hits": ";".join(fusion_hits_by_model.get(model_id, [])),
                            "gene_symbol": gene_symbol,
                            "rna_value_log2_tpm_plus_1": value,
                        }
                    )

            # Second output: requested MSV lines merged to existing proteomics result.
            if model_id in requested_by_model:
                requested = requested_by_model[model_id]
                for gene_symbol, header_name in TARGET_HEADERS.items():
                    value = row[column_index[header_name]]
                    if value not in {"", "0.0", "0", "NA", "NaN", "nan"}:
                        summary["targets"][gene_symbol]["n_requested_lines_gt0"] += 1

                    proteomics = proteomics_by_requested_gene.get((requested["requested_name"], gene_symbol), {})
                    requested_merged_rows.append(
                        {
                            "requested_name": requested["requested_name"],
                            "cell_line": requested["Cell Line"],
                            "ccle_code": requested["CCLE Code"],
                            "protein_10plex_id": requested["Protein 10-Plex ID"],
                            "protein_tmt_label": requested["Protein TMT Label"],
                            "model_id": model_id,
                            "oncotree_subtype": model.get("OncotreeSubtype", ""),
                            "fusion_status": fusion_status_by_model.get(model_id, "no_PAX3_7_FOXO1_call_in_filtered_table"),
                            "fusion_hits": ";".join(fusion_hits_by_model.get(model_id, [])),
                            "gene_symbol": gene_symbol,
                            "rna_value_log2_tpm_plus_1": value,
                            "protein_column_present_in_harmonized_matrix": proteomics.get("column_present_in_harmonized_matrix", ""),
                            "protein_detected_nonmissing_value": proteomics.get("detected_nonmissing_value", ""),
                            "protein_harmonized_value": proteomics.get("harmonized_value", ""),
                        }
                    )

    with OUT_RMS_RNA.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rms_rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(rms_rows)

    with OUT_REQUESTED_MERGED.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(requested_merged_rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(requested_merged_rows)

    with OUT_SUMMARY.open("w") as handle:
        json.dump(summary, handle, indent=2)

    print(OUT_RMS_RNA)
    print(OUT_REQUESTED_MERGED)
    print(OUT_SUMMARY)


if __name__ == "__main__":
    main()
