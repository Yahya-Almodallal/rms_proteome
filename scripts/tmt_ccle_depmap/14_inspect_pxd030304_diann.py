#!/usr/bin/env python3
"""
Inspect the large PXD030304 DIA-NN output on HPC before attempting any raw subsetting.

Why this exists:
- the PRIDE raw payload is exposed as date-named ZIP archives rather than cell-line names
- we first need to learn how the DIA-NN output encodes sample/run/model identifiers
- once we know the relevant columns, we can search for RMS lines such as RD, SJRH30, RH41, KYM-1, or A204
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


DEFAULT_KEYWORDS = [
    "sample",
    "run",
    "file",
    "raw",
    "cell",
    "line",
    "model",
    "protein",
    "gene",
    "precursor",
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--tsv",
        default="/scratch/almrb2/rms.omics/proteome/ProCan-DepMapSanger_DIANN_output.tsv",
        help="Path to the DIA-NN TSV on HPC scratch.",
    )
    ap.add_argument(
        "--print-header",
        action="store_true",
        help="Print the full header with 1-based column indices.",
    )
    ap.add_argument(
        "--find-columns",
        nargs="*",
        default=None,
        help="Print header columns whose names contain any of these case-insensitive keywords. "
        "If omitted, uses a practical default keyword set.",
    )
    ap.add_argument(
        "--terms",
        nargs="*",
        default=[],
        help="Case-insensitive search terms to match in rows, e.g. RD SJRH30 RH41.",
    )
    ap.add_argument(
        "--search-columns",
        nargs="*",
        default=[],
        help="Restrict term matching to these column names. Default is all columns.",
    )
    ap.add_argument(
        "--show-columns",
        nargs="*",
        default=[],
        help="When printing matched rows, show only these columns. Default is all columns.",
    )
    ap.add_argument(
        "--max-rows",
        type=int,
        default=20,
        help="Maximum number of matched rows to print.",
    )
    ap.add_argument(
        "--out-tsv",
        default="",
        help="Optional path to write matched rows as TSV.",
    )
    return ap.parse_args()


def load_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        return next(reader)


def print_header(header: list[str]) -> None:
    for idx, col in enumerate(header, start=1):
        print(f"{idx}\t{col}")


def find_columns(header: list[str], keywords: list[str]) -> None:
    lowered = [k.lower() for k in keywords]
    for idx, col in enumerate(header, start=1):
        col_low = col.lower()
        if any(k in col_low for k in lowered):
            print(f"{idx}\t{col}")


def validate_columns(requested: list[str], header: list[str], flag_name: str) -> list[str]:
    missing = [c for c in requested if c not in header]
    if missing:
        raise SystemExit(
            f"{flag_name} columns not present in header: {', '.join(missing)}"
        )
    return requested


def row_matches(
    row: dict[str, str],
    terms: list[str],
    search_columns: list[str],
) -> bool:
    if not terms:
        return False
    haystack_columns = search_columns if search_columns else list(row.keys())
    text = "\t".join(row.get(col, "") for col in haystack_columns).lower()
    return any(term.lower() in text for term in terms)


def iter_matches(
    path: Path,
    terms: list[str],
    search_columns: list[str],
):
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for line_no, row in enumerate(reader, start=2):
            if row_matches(row, terms, search_columns):
                yield line_no, row


def print_matches(
    matches,
    show_columns: list[str],
    max_rows: int,
) -> list[dict[str, str]]:
    kept: list[dict[str, str]] = []
    for idx, (line_no, row) in enumerate(matches, start=1):
        if idx > max_rows:
            break
        if show_columns:
            slim = {"__line__": str(line_no)}
            for col in show_columns:
                slim[col] = row.get(col, "")
            row = slim
        else:
            row = {"__line__": str(line_no), **row}
        kept.append(row)
        print(f"MATCH\t{idx}\tline={line_no}")
        for key, value in row.items():
            print(f"{key}\t{value}")
        print()
    return kept


def write_matches(out_path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {out_path}")


def main() -> None:
    args = parse_args()
    path = Path(args.tsv)
    if not path.exists():
        raise SystemExit(f"TSV not found: {path}")

    header = load_header(path)

    if args.print_header:
        print_header(header)

    keywords = args.find_columns
    if keywords is not None:
        if not keywords:
            keywords = DEFAULT_KEYWORDS
        find_columns(header, keywords)

    if not args.terms:
        return

    search_columns = validate_columns(args.search_columns, header, "--search-columns")
    show_columns = validate_columns(args.show_columns, header, "--show-columns")

    matches = iter_matches(path, args.terms, search_columns)
    printed_rows = print_matches(matches, show_columns, args.max_rows)

    if args.out_tsv:
        write_matches(Path(args.out_tsv), printed_rows)

    if not printed_rows:
        print("No matching rows found.", file=sys.stderr)


if __name__ == "__main__":
    main()
