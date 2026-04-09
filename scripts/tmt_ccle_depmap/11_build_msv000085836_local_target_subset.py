#!/usr/bin/env python3
"""
Build a target-file manifest from a local MSV000085836 raw mirror.

Use this on HPC after the MassIVE mirror finishes.

Why this exists:
- after the full raw mirror lands on scratch, we no longer need the live FTP
  listing to identify the files of interest
- we want a reproducible subset manifest for the five cell lines we care about
- the subset should be derived from what actually exists on disk
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET


TARGET_LINES = ["A-204", "RD", "RH-41", "RH-30", "KYM-1"]


def load_sample_info_subset(sample_info_xlsx: Path) -> list[dict[str, str]]:
    with ZipFile(sample_info_xlsx) as zf:
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


def write_tsv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-info-xlsx", required=True)
    ap.add_argument("--raw-dir", required=True)
    ap.add_argument("--out-manifest", required=True)
    ap.add_argument("--out-summary", required=True)
    args = ap.parse_args()

    sample_rows = load_sample_info_subset(Path(args.sample_info_xlsx))
    raw_dir = Path(args.raw_dir)
    raw_files = sorted(raw_dir.glob("*.raw"))

    by_plex = {row["Protein 10-Plex ID"]: row for row in sample_rows}
    manifest_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for plex_id, sample in sorted(by_plex.items(), key=lambda kv: int(kv[0])):
        hits = []
        marker = f"Prot_{plex_id}_"
        for raw_path in raw_files:
            if marker not in raw_path.name:
                continue
            frac_match = re.search(rf"Prot_{plex_id}_(\d+)\.raw$", raw_path.name)
            fraction_index = frac_match.group(1) if frac_match else ""
            hits.append(
                {
                    "cell_line": sample["Cell Line"],
                    "ccle_code": sample["CCLE Code"],
                    "protein_10plex_id": plex_id,
                    "protein_tmt_label": sample["Protein TMT Label"],
                    "fraction_index": fraction_index,
                    "file_name": raw_path.name,
                    "file_size_bytes": raw_path.stat().st_size,
                    "local_path": str(raw_path),
                }
            )

        hits.sort(key=lambda row: int(row["fraction_index"]) if str(row["fraction_index"]).isdigit() else 999)
        manifest_rows.extend(hits)
        summary_rows.append(
            {
                "cell_line": sample["Cell Line"],
                "protein_10plex_id": plex_id,
                "protein_tmt_label": sample["Protein TMT Label"],
                "n_raw_files_found": len(hits),
                "total_bytes": sum(int(row["file_size_bytes"]) for row in hits),
                "total_gb_decimal": round(sum(int(row["file_size_bytes"]) for row in hits) / 1e9, 3),
            }
        )

    if not manifest_rows:
        raise RuntimeError(f"No matching raw files found under {raw_dir}")

    write_tsv(Path(args.out_manifest), manifest_rows)
    write_tsv(Path(args.out_summary), summary_rows)
    print(args.out_manifest)
    print(args.out_summary)


if __name__ == "__main__":
    main()
