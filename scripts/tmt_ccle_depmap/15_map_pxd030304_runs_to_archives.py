#!/usr/bin/env python3
"""
Map PXD030304 DIA-NN hits back to candidate raw ZIP archives.

This is intended for HPC use after downloading the large DIA-NN TSV. The main
problem with PXD030304 is that PRIDE exposes raw data as date-named ZIP files
rather than cell-line-named bundles. DIA-NN rows still retain run/file names,
and those run names typically start with the same 6-digit date token used by
the corresponding raw ZIP archive.

Typical use:

1. Search only the run-identifying columns.
2. Use stricter regex patterns than plain "RD" substring matching.
3. Aggregate to unique runs, then to candidate ZIP archives.

Example:
    python3 scripts/tmt_ccle_depmap/15_map_pxd030304_runs_to_archives.py \
      --regex '(^|[_./-])00drd([_./-]|$)' \
              '(^|[_./-])004rd([_./-]|$)' \
              '(^|[_./-])005rd([_./-]|$)' \
      --out-prefix pxd030304_rd_candidates
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


DEFAULT_TSV = "/scratch/almrb2/rms.omics/proteome/ProCan-DepMapSanger_DIANN_output.tsv"
DEFAULT_MANIFEST = "metadata/tmt_ccle_depmap/pride/PXD030304_files.tsv"
DEFAULT_SEARCH_COLUMNS = ["File.Name", "Run"]
FAST_PATH_COLUMNS = ["File.Name", "Run"]


@dataclass
class RunSummary:
    run: str
    file_name: str
    matched_rows: int
    inferred_archive: str


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--tsv",
        default=DEFAULT_TSV,
        help="Path to ProCan-DepMapSanger_DIANN_output.tsv on HPC scratch.",
    )
    ap.add_argument(
        "--manifest",
        default=DEFAULT_MANIFEST,
        help="Path to the local PRIDE PXD030304 manifest TSV.",
    )
    ap.add_argument(
        "--terms",
        nargs="*",
        default=[],
        help="Case-insensitive literal substrings to match.",
    )
    ap.add_argument(
        "--regex",
        nargs="*",
        default=[],
        help="Case-insensitive regular expressions to match.",
    )
    ap.add_argument(
        "--search-columns",
        nargs="*",
        default=DEFAULT_SEARCH_COLUMNS,
        help="Columns to search. Defaults to File.Name and Run.",
    )
    ap.add_argument(
        "--min-run-hits",
        type=int,
        default=1,
        help="Keep only runs with at least this many matched rows.",
    )
    ap.add_argument(
        "--max-runs",
        type=int,
        default=200,
        help="Maximum number of runs to print in the terminal summary.",
    )
    ap.add_argument(
        "--max-archives",
        type=int,
        default=200,
        help="Maximum number of candidate archives to print in the terminal summary.",
    )
    ap.add_argument(
        "--out-prefix",
        default="",
        help="Optional prefix for writing .runs.tsv, .archives.tsv, and .wget.txt outputs.",
    )
    ap.add_argument(
        "--progress-every",
        type=int,
        default=2_000_000,
        help="Print a progress update to stderr every N data rows. Use 0 to disable.",
    )
    return ap.parse_args()


def validate_columns(header: list[str], requested: list[str], flag_name: str) -> list[str]:
    missing = [col for col in requested if col not in header]
    if missing:
        raise SystemExit(f"{flag_name} columns not present in header: {', '.join(missing)}")
    return requested


def load_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        return next(reader)


def compile_patterns(terms: list[str], regexes: list[str]) -> tuple[list[str], list[re.Pattern[str]]]:
    if not terms and not regexes:
        raise SystemExit("Provide at least one --term or --regex.")
    compiled = [re.compile(expr, re.IGNORECASE) for expr in regexes]
    return [t.lower() for t in terms], compiled


def build_search_text(row: dict[str, str], columns: list[str]) -> str:
    return "\t".join(row.get(col, "") for col in columns)


def row_matches(text: str, literal_terms: list[str], regex_terms: list[re.Pattern[str]]) -> bool:
    text_low = text.lower()
    if any(term in text_low for term in literal_terms):
        return True
    return any(rx.search(text) for rx in regex_terms)


def infer_archive_name(run_name: str) -> str:
    prefix = run_name[:6]
    if re.fullmatch(r"\d{6}", prefix):
        return f"{prefix}.zip"
    return ""


def maybe_report_progress(
    line_no: int,
    counts: Counter[str],
    progress_every: int,
) -> None:
    if progress_every <= 0 or line_no % progress_every != 0:
        return
    matched_rows = sum(counts.values())
    unique_runs = len(counts)
    print(
        f"[progress] scanned_rows={line_no:,} matched_rows={matched_rows:,} unique_runs={unique_runs:,}",
        file=sys.stderr,
        flush=True,
    )


def stream_run_matches_fast_path(
    diann_tsv: Path,
    literal_terms: list[str],
    regex_terms: list[re.Pattern[str]],
    progress_every: int,
) -> dict[str, RunSummary]:
    counts: Counter[str] = Counter()
    first_file_name: dict[str, str] = {}

    with diann_tsv.open("r", encoding="utf-8", newline="") as handle:
        next(handle)
        for line_no, raw_line in enumerate(handle, start=1):
            parts = raw_line.rstrip("\n").split("\t", 2)
            if len(parts) < 2:
                maybe_report_progress(line_no, counts, progress_every)
                continue

            file_name = parts[0].strip()
            run_name = parts[1].strip()
            search_text = f"{file_name}\t{run_name}"

            if row_matches(search_text, literal_terms, regex_terms):
                if run_name:
                    counts[run_name] += 1
                    if run_name not in first_file_name:
                        first_file_name[run_name] = file_name

            maybe_report_progress(line_no, counts, progress_every)

    summaries: dict[str, RunSummary] = {}
    for run_name, matched_rows in counts.items():
        summaries[run_name] = RunSummary(
            run=run_name,
            file_name=first_file_name.get(run_name, ""),
            matched_rows=matched_rows,
            inferred_archive=infer_archive_name(run_name),
        )
    return summaries


def stream_run_matches_generic(
    diann_tsv: Path,
    header: list[str],
    search_columns: list[str],
    literal_terms: list[str],
    regex_terms: list[re.Pattern[str]],
    progress_every: int,
) -> dict[str, RunSummary]:
    counts: Counter[str] = Counter()
    first_file_name: dict[str, str] = {}

    search_indexes = [header.index(col) for col in search_columns]
    run_idx = header.index("Run")
    file_idx = header.index("File.Name")

    with diann_tsv.open("r", encoding="utf-8", newline="") as handle:
        next(handle)
        for line_no, raw_line in enumerate(handle, start=1):
            parts = raw_line.rstrip("\n").split("\t")

            selected = []
            for idx in search_indexes:
                selected.append(parts[idx] if idx < len(parts) else "")
            search_text = "\t".join(selected)

            if row_matches(search_text, literal_terms, regex_terms):
                run_name = parts[run_idx].strip() if run_idx < len(parts) else ""
                file_name = parts[file_idx].strip() if file_idx < len(parts) else ""
                if run_name:
                    counts[run_name] += 1
                    if run_name not in first_file_name:
                        first_file_name[run_name] = file_name

            maybe_report_progress(line_no, counts, progress_every)

    summaries: dict[str, RunSummary] = {}
    for run_name, matched_rows in counts.items():
        summaries[run_name] = RunSummary(
            run=run_name,
            file_name=first_file_name.get(run_name, ""),
            matched_rows=matched_rows,
            inferred_archive=infer_archive_name(run_name),
        )
    return summaries


def stream_run_matches(
    diann_tsv: Path,
    header: list[str],
    search_columns: list[str],
    literal_terms: list[str],
    regex_terms: list[re.Pattern[str]],
    progress_every: int,
) -> dict[str, RunSummary]:
    if search_columns == FAST_PATH_COLUMNS and header[:2] == FAST_PATH_COLUMNS:
        print(
            "[mode] fast path: scanning only File.Name and Run",
            file=sys.stderr,
            flush=True,
        )
        return stream_run_matches_fast_path(
            diann_tsv=diann_tsv,
            literal_terms=literal_terms,
            regex_terms=regex_terms,
            progress_every=progress_every,
        )

    print(
        "[mode] generic path: scanning requested columns via tab splitting",
        file=sys.stderr,
        flush=True,
    )
    return stream_run_matches_generic(
        diann_tsv=diann_tsv,
        header=header,
        search_columns=search_columns,
        literal_terms=literal_terms,
        regex_terms=regex_terms,
        progress_every=progress_every,
    )


def load_manifest(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = {}
        for row in reader:
            if row.get("file_category") != "RAW":
                continue
            file_name = row.get("file_name", "")
            if file_name.endswith(".zip"):
                rows[file_name] = row
        return rows


def bytes_to_gb(num_bytes: int) -> float:
    return num_bytes / (1024 ** 3)


def build_run_rows(
    run_summaries: dict[str, RunSummary],
    manifest_rows: dict[str, dict[str, str]],
    min_run_hits: int,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for summary in sorted(
        run_summaries.values(),
        key=lambda x: (-x.matched_rows, x.run),
    ):
        if summary.matched_rows < min_run_hits:
            continue
        manifest = manifest_rows.get(summary.inferred_archive, {})
        size_bytes = manifest.get("file_size_bytes", "")
        size_gb = ""
        if size_bytes:
            size_gb = f"{bytes_to_gb(int(size_bytes)):.2f}"
        rows.append(
            {
                "run": summary.run,
                "file_name_example": summary.file_name,
                "matched_rows": str(summary.matched_rows),
                "inferred_archive": summary.inferred_archive,
                "archive_in_manifest": "True" if summary.inferred_archive in manifest_rows else "False",
                "archive_size_gb": size_gb,
            }
        )
    return rows


def build_archive_rows(
    run_rows: list[dict[str, str]],
    manifest_rows: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    archive_counts: Counter[str] = Counter()
    archive_run_counts: Counter[str] = Counter()

    for row in run_rows:
        archive = row["inferred_archive"]
        if not archive:
            continue
        archive_counts[archive] += int(row["matched_rows"])
        archive_run_counts[archive] += 1

    rows: list[dict[str, str]] = []
    for archive in sorted(archive_counts, key=lambda x: (-archive_counts[x], x)):
        manifest = manifest_rows.get(archive, {})
        size_bytes = manifest.get("file_size_bytes", "")
        size_gb = ""
        if size_bytes:
            size_gb = f"{bytes_to_gb(int(size_bytes)):.2f}"
        rows.append(
            {
                "archive": archive,
                "unique_runs": str(archive_run_counts[archive]),
                "matched_rows": str(archive_counts[archive]),
                "file_size_bytes": size_bytes,
                "size_gb": size_gb,
                "ftp_url": manifest.get("ftp_url", ""),
                "aspera_url": manifest.get("aspera_url", ""),
            }
        )
    return rows


def print_table(rows: list[dict[str, str]], title: str, max_rows: int) -> None:
    print(f"# {title}")
    if not rows:
        print("No rows.\n")
        return
    header = list(rows[0].keys())
    print("\t".join(header))
    for row in rows[:max_rows]:
        print("\t".join(row.get(col, "") for col in header))
    if len(rows) > max_rows:
        print(f"... truncated at {max_rows} rows")
    print()


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def write_wget(path: Path, archive_rows: list[dict[str, str]]) -> None:
    lines = [f"wget -c {row['ftp_url']}" for row in archive_rows if row.get("ftp_url")]
    if not lines:
        return
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    diann_tsv = Path(args.tsv)
    manifest_tsv = Path(args.manifest)

    if not diann_tsv.exists():
        raise SystemExit(f"DIA-NN TSV not found: {diann_tsv}")
    if not manifest_tsv.exists():
        raise SystemExit(f"PXD030304 manifest not found: {manifest_tsv}")

    header = load_header(diann_tsv)
    search_columns = validate_columns(header, args.search_columns, "--search-columns")
    literal_terms, regex_terms = compile_patterns(args.terms, args.regex)

    manifest_rows = load_manifest(manifest_tsv)
    run_summaries = stream_run_matches(
        diann_tsv=diann_tsv,
        header=header,
        search_columns=search_columns,
        literal_terms=literal_terms,
        regex_terms=regex_terms,
        progress_every=args.progress_every,
    )
    run_rows = build_run_rows(run_summaries, manifest_rows, args.min_run_hits)
    archive_rows = build_archive_rows(run_rows, manifest_rows)

    print(f"Matched unique runs: {len(run_rows)}", file=sys.stderr)
    print(f"Candidate archives: {len(archive_rows)}", file=sys.stderr)

    print_table(run_rows, "Unique Runs", args.max_runs)
    print_table(archive_rows, "Candidate Archives", args.max_archives)

    if args.out_prefix:
        prefix = Path(args.out_prefix)
        runs_path = prefix.with_suffix(".runs.tsv")
        archives_path = prefix.with_suffix(".archives.tsv")
        wget_path = prefix.with_suffix(".wget.txt")
        write_tsv(runs_path, run_rows)
        write_tsv(archives_path, archive_rows)
        write_wget(wget_path, archive_rows)
        print(f"Wrote {runs_path}", file=sys.stderr)
        print(f"Wrote {archives_path}", file=sys.stderr)
        if wget_path.exists():
            print(f"Wrote {wget_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
