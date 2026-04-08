#!/usr/bin/env python3
"""
Extract rows for target genes from PXD039480 processed results (Excel workbook).

Design goals:
- No external dependencies (uses Python standard library only).
- Works on large .xlsx files by streaming XML rows.
- Beginner-friendly comments and explicit steps.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
PRIMARY_TARGETS = {"MYMK", "MYMX", "MYOD1", "MYOG"}


@dataclass
class MatchRecord:
    """Minimal summary for one matched protein-group row."""

    matched_targets: str
    GN: str
    leading_protein: str
    protein_ids: str
    majority_protein_ids: str
    fasta_headers: str
    q_value: str
    score: str
    peptide_sequences: str
    potential_contaminant: str
    only_identified_by_site: str


def col_to_index(cell_ref: str) -> int:
    """Convert Excel column letters (A, B, AA) to zero-based index."""
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1


def load_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    """Load shared strings table used by .xlsx cells with type='s'."""
    xml = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for si in xml.findall(f"{NS}si"):
        # A shared-string entry may have multiple text nodes (rich text runs).
        text = "".join((t.text or "") for t in si.iter(f"{NS}t"))
        values.append(text)
    return values


def parse_workbook_sheet_map(zf: zipfile.ZipFile) -> dict[str, str]:
    """Map sheet names to worksheet XML paths (e.g., xl/worksheets/sheet1.xml)."""
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))

    rid_to_target = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels
        if rel.attrib.get("Type", "").endswith("/worksheet")
    }

    sheet_map: dict[str, str] = {}
    for sheet in workbook.find(f"{NS}sheets"):
        name = sheet.attrib.get("name", "")
        rid = sheet.attrib.get(REL_NS, "")
        target = rid_to_target.get(rid, "")
        if target:
            sheet_map[name] = f"xl/{target}" if not target.startswith("xl/") else target
    return sheet_map


def extract_cell_text(cell: ET.Element, shared_strings: list[str]) -> str:
    """Decode one cell value into plain text."""
    ctype = cell.attrib.get("t")
    v = cell.find(f"{NS}v")
    if v is None or v.text is None:
        return ""

    raw = v.text
    if ctype == "s":
        # Shared string index.
        idx = int(raw)
        return shared_strings[idx] if 0 <= idx < len(shared_strings) else ""
    return raw


def iter_sheet_rows(
    zf: zipfile.ZipFile,
    sheet_path: str,
    shared_strings: list[str],
) -> Iterable[dict[int, str]]:
    """
    Stream worksheet rows as dictionaries: {column_index: cell_text}.

    Using iterparse keeps memory usage bounded even on very large sheets.
    """
    with zf.open(sheet_path) as handle:
        context = ET.iterparse(handle, events=("end",))
        for _event, elem in context:
            if elem.tag != f"{NS}row":
                continue

            row_data: dict[int, str] = {}
            for cell in elem.findall(f"{NS}c"):
                ref = cell.attrib.get("r", "")
                if not ref:
                    continue
                idx = col_to_index(ref)
                row_data[idx] = extract_cell_text(cell, shared_strings)

            yield row_data
            # Important: clear parsed XML nodes to prevent memory growth.
            elem.clear()


def load_targets(target_csv: Path) -> set[str]:
    """Load target symbols from ann.genes.sheets.csv and force-add primary proteins."""
    targets: set[str] = set()

    with target_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            for key in ("gene_symbol", "original_symbol"):
                val = (row.get(key) or "").strip().upper()
                if val:
                    targets.add(val)

            # Aliases are often separated by ';' or commas; capture both.
            aliases = (row.get("aliases") or "").strip()
            if aliases:
                for token in re.split(r"[;,]", aliases):
                    token = token.strip().upper()
                    if token:
                        targets.add(token)

    # Always include key proteins discussed in this project, even if the CSV changes.
    targets.update(PRIMARY_TARGETS)
    return targets


def extract_genes_from_row(gn_field: str, fasta_headers: str) -> set[str]:
    """Build a set of gene symbols suggested by GN and FASTA header annotations."""
    genes: set[str] = set()

    # GN field can contain one or many symbols separated by ';'.
    for token in gn_field.split(";"):
        tok = token.strip().upper()
        if tok:
            genes.add(tok)

    # Fasta headers contain patterns like 'GN=MYMX'.
    for match in re.findall(r"\bGN=([A-Za-z0-9_-]+)", fasta_headers):
        genes.add(match.upper())

    return genes


def keep_column(header_name: str) -> bool:
    """Decide which columns are useful to keep in the output table."""
    if header_name in {
        "Leading_Protein",
        "GN",
        "Protein IDs",
        "Majority protein IDs",
        "Fasta headers",
        "Q-value",
        "Score",
        "Peptide sequences",
        "Potential contaminant",
        "Only identified by site",
    }:
        return True

    prefixes = ("LFQ ", "iLFQ ", "Top3 ", "iTop3 ", "Seen in ")
    return header_name.startswith(prefixes)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract target-gene rows from PXD039480 workbook")
    parser.add_argument(
        "--xlsx",
        default="data/surfaceome/PXD039480/raw/20210720_MQres_AT.xlsx",
        help="Path to PXD039480 workbook",
    )
    parser.add_argument(
        "--targets_csv",
        default="ann.genes.sheets.csv",
        help="CSV containing target genes",
    )
    parser.add_argument(
        "--sheet",
        default="proteinGroups cleaned",
        help="Workbook sheet to parse",
    )
    parser.add_argument(
        "--out_tsv",
        default="results/surfaceome_pxd039480/targets_pxd039480_proteinGroups_cleaned.tsv",
        help="Output TSV for matched rows",
    )
    parser.add_argument(
        "--summary_json",
        default="results/surfaceome_pxd039480/targets_pxd039480_summary.json",
        help="Output JSON summary",
    )
    args = parser.parse_args()

    xlsx_path = Path(args.xlsx)
    targets_csv = Path(args.targets_csv)
    out_tsv = Path(args.out_tsv)
    summary_json = Path(args.summary_json)

    if not xlsx_path.exists():
        raise SystemExit(f"Workbook not found: {xlsx_path}")
    if not targets_csv.exists():
        raise SystemExit(f"Target CSV not found: {targets_csv}")

    targets = load_targets(targets_csv)

    out_tsv.parent.mkdir(parents=True, exist_ok=True)
    summary_json.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(xlsx_path) as zf:
        sheet_map = parse_workbook_sheet_map(zf)
        if args.sheet not in sheet_map:
            available = ", ".join(sorted(sheet_map))
            raise SystemExit(f"Sheet '{args.sheet}' not found. Available: {available}")

        shared_strings = load_shared_strings(zf)
        row_iter = iter_sheet_rows(zf, sheet_map[args.sheet], shared_strings)

        try:
            header_row = next(row_iter)
        except StopIteration as err:
            raise SystemExit("Selected sheet is empty.") from err

        headers = {idx: value for idx, value in header_row.items()}
        needed_columns = {idx: name for idx, name in headers.items() if keep_column(name)}

        # Mandatory columns for matching logic.
        required_names = ["GN", "Fasta headers"]
        name_to_idx = {name: idx for idx, name in headers.items()}
        missing = [name for name in required_names if name not in name_to_idx]
        if missing:
            raise SystemExit(f"Missing required columns in sheet header: {missing}")

        gn_idx = name_to_idx["GN"]
        fasta_idx = name_to_idx["Fasta headers"]

        output_headers = ["matched_targets"] + [needed_columns[idx] for idx in sorted(needed_columns)]

        matched_rows = 0
        gene_counter: Counter[str] = Counter()
        tracked_counts: Counter[str] = Counter()

        with out_tsv.open("w", encoding="utf-8", newline="") as out_handle:
            writer = csv.DictWriter(out_handle, fieldnames=output_headers, delimiter="\t")
            writer.writeheader()

            for row in row_iter:
                gn_field = row.get(gn_idx, "")
                fasta_field = row.get(fasta_idx, "")

                row_genes = extract_genes_from_row(gn_field, fasta_field)
                matched = sorted(row_genes.intersection(targets))
                if not matched:
                    continue

                matched_rows += 1
                gene_counter.update(matched)
                for target in PRIMARY_TARGETS:
                    if target in matched:
                        tracked_counts[target] += 1

                out_row = {"matched_targets": ";".join(matched)}
                for idx in sorted(needed_columns):
                    out_row[needed_columns[idx]] = row.get(idx, "")
                writer.writerow(out_row)

    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "input_workbook": str(xlsx_path),
        "input_sheet": args.sheet,
        "targets_csv": str(targets_csv),
        "target_symbol_count": len(targets),
        "matched_row_count": matched_rows,
        "matched_target_counts": dict(gene_counter.most_common()),
        "tracked_primary_counts": dict(sorted(tracked_counts.items())),
        "output_tsv": str(out_tsv),
    }

    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Wrote matched rows: {matched_rows}")
    for key in sorted(PRIMARY_TARGETS):
        print(f"{key} rows: {tracked_counts.get(key, 0)}")
    print(f"Output TSV: {out_tsv}")
    print(f"Summary JSON: {summary_json}")


if __name__ == "__main__":
    main()
