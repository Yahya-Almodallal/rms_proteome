#!/usr/bin/env python3
"""
Extract the four target genes from MSFragger/Philosopher report tables.

Why this exists:
- the search workspace will contain broad protein, peptide, and PSM tables
- the user only wants to inspect MYMK, MYMX, MYOD1, and MYOG first
- MYMK/MYMX also have common aliases that should count as the same target
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


TARGETS = {"MYMK", "MYMX", "MYOD1", "MYOG"}
ALIASES = {
    "TMEM8C": "MYMK",
    "MYOMAKER": "MYMK",
    "MYOMIXER": "MYMX",
    "MINION": "MYMX",
}

TABLE_CONFIG = [
    ("protein.tsv", ["Gene Name", "Gene"]),
    ("combined_protein.tsv", ["Gene Name", "Gene"]),
    ("peptide.tsv", ["Gene", "Gene Name", "Mapped Genes"]),
    ("psm.tsv", ["Gene", "Gene Name", "Mapped Genes"]),
]


def normalize_gene(text: str) -> str:
    gene = text.strip().upper()
    return ALIASES.get(gene, gene)


def extract_rows(table_path: Path, gene_columns: list[str], out_dir: Path) -> Path | None:
    if not table_path.exists():
        return None

    out_path = out_dir / f"{table_path.stem}.targets.tsv"
    with table_path.open(encoding="utf-8", newline="") as handle, out_path.open(
        "w", encoding="utf-8", newline=""
    ) as out_handle:
        reader = csv.DictReader(handle, delimiter="\t")
        writer = csv.DictWriter(out_handle, fieldnames=reader.fieldnames, delimiter="\t")
        writer.writeheader()
        for row in reader:
            observed: set[str] = set()
            for column in gene_columns:
                value = row.get(column, "")
                if not value:
                    continue
                cleaned = value.replace(";", ",")
                for token in cleaned.split(","):
                    norm = normalize_gene(token)
                    if norm:
                        observed.add(norm)
            if TARGETS & observed:
                writer.writerow(row)
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--search-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    search_dir = Path(args.search_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for table_name, gene_columns in TABLE_CONFIG:
        out_path = extract_rows(search_dir / table_name, gene_columns, out_dir)
        if out_path is not None:
            written.append(out_path)

    if not written:
        raise SystemExit(f"No expected report tables found under {search_dir}")

    for path in written:
        print(path)


if __name__ == "__main__":
    main()
