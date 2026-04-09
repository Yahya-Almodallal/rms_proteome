#!/usr/bin/env python3
"""
Build a manifest for the MSV000085836 raw files that correspond to the five
requested cell lines:
- A-204
- RD
- RH-41
- RH-30
- KYM-1

Why this script exists:
- the full accession contains 552 raw files
- each requested line maps to one Protein 10-Plex ID
- each of those plexes has 12 fractionated raw files
- we want an explicit, machine-readable subset manifest before any search step

This script queries the live MassIVE directory listing because the local saved
index was intentionally shallow and does not enumerate raw/raw/ in full.
"""

from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
SAMPLE_INFO_XLSX = ROOT / "metadata/tmt_ccle_depmap/msv000085836/Table_S1_Sample_Information.xlsx"
OUT_TSV = ROOT / "metadata/tmt_ccle_depmap/hpc_downloads/MSV000085836_target_plex_raw_manifest.tsv"
OUT_SUMMARY = ROOT / "metadata/tmt_ccle_depmap/hpc_downloads/MSV000085836_target_plex_summary.tsv"

TARGET_LINES = ["A-204", "RD", "RH-41", "RH-30", "KYM-1"]
RAW_ROOT = "ftp://massive-ftp.ucsd.edu/v03/MSV000085836/raw/raw/"


def load_sample_info_subset() -> list[dict[str, str]]:
    with ZipFile(SAMPLE_INFO_XLSX) as zf:
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        ns = {
            "x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
            "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        }
        sheets = [
            (
                s.attrib["name"],
                s.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"],
            )
            for s in wb.find("x:sheets", ns)
        ]
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rid_to_target = {r.attrib["Id"]: r.attrib["Target"] for r in rels}

        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            sst_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in sst_root:
                parts = [t.text or "" for t in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")]
                shared_strings.append("".join(parts))

        def cell_value(cell: ET.Element) -> str:
            cell_type = cell.attrib.get("t")
            value_node = cell.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
            if value_node is None:
                return ""
            value = value_node.text or ""
            if cell_type == "s" and value.isdigit():
                idx = int(value)
                if 0 <= idx < len(shared_strings):
                    return shared_strings[idx]
            return value

        # "Sample_Information" is the second sheet in this workbook.
        _, sheet_rid = sheets[1]
        sheet_path = "xl/" + rid_to_target[sheet_rid].lstrip("/")
        sheet_root = ET.fromstring(zf.read(sheet_path))
        rows = sheet_root.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row")

        matrix: list[list[str]] = []
        for row in rows:
            matrix.append([cell_value(c) for c in row.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c")])

    header = matrix[0]
    idx = {name: i for i, name in enumerate(header)}
    subset = []
    for values in matrix[1:]:
        if values and values[idx["Cell Line"]] in TARGET_LINES:
            subset.append({name: values[pos] if pos < len(values) else "" for name, pos in idx.items()})
    return subset


def fetch_raw_listing() -> list[tuple[str, int]]:
    html = subprocess.check_output(["wget", "-qO-", RAW_ROOT], text=True, errors="replace")
    pattern = re.compile(r'<a href="[^"]+">([^<]+)</a>\s+\((\d+) bytes\)')
    return [(name, int(size)) for name, size in pattern.findall(html)]


def main() -> None:
    sample_rows = load_sample_info_subset()
    raw_rows = fetch_raw_listing()

    by_plex = {row["Protein 10-Plex ID"]: row for row in sample_rows}
    manifest_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for plex_id, sample in sorted(by_plex.items(), key=lambda kv: int(kv[0])):
        hits = []
        marker = f"Prot_{plex_id}_"
        for file_name, file_size_bytes in raw_rows:
            if marker in file_name:
                frac_match = re.search(rf"Prot_{plex_id}_(\d+)\.raw$", file_name)
                fraction_index = frac_match.group(1) if frac_match else ""
                hits.append(
                    {
                        "cell_line": sample["Cell Line"],
                        "ccle_code": sample["CCLE Code"],
                        "protein_10plex_id": plex_id,
                        "protein_tmt_label": sample["Protein TMT Label"],
                        "fraction_index": fraction_index,
                        "file_name": file_name,
                        "file_size_bytes": file_size_bytes,
                        "ftp_url": RAW_ROOT + file_name,
                    }
                )

        hits.sort(key=lambda row: int(row["fraction_index"]) if str(row["fraction_index"]).isdigit() else 999)
        manifest_rows.extend(hits)
        summary_rows.append(
            {
                "cell_line": sample["Cell Line"],
                "protein_10plex_id": plex_id,
                "protein_tmt_label": sample["Protein TMT Label"],
                "n_raw_files": len(hits),
                "total_bytes": sum(int(row["file_size_bytes"]) for row in hits),
                "total_gb_decimal": round(sum(int(row["file_size_bytes"]) for row in hits) / 1e9, 3),
            }
        )

    for out_path, rows in [(OUT_TSV, manifest_rows), (OUT_SUMMARY, summary_rows)]:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)

    print(OUT_TSV)
    print(OUT_SUMMARY)


if __name__ == "__main__":
    main()
