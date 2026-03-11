#!/usr/bin/env python3
"""
Download PXD011967 SEARCH files and scan them for target proteins/genes.

Why this script:
- The SEARCH set is large (~96 GB), so downloads may need resume behavior.
- We want a reproducible, beginner-friendly command that both downloads and scans.

Outputs:
- data/tmt_normal/PXD011967/search/*.dat
- results/tmt_ccle_depmap/PXD011967_search_target_hits.tsv
- results/tmt_ccle_depmap/PXD011967_search_download_progress.tsv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import subprocess
from pathlib import Path


ROOT = Path("/home/yahya/Scripts/rms_proteome")
META_TSV = ROOT / "metadata" / "tmt_ccle_depmap" / "pride" / "PXD011967_files.tsv"
OUT_DIR = ROOT / "data" / "tmt_normal" / "PXD011967" / "search"
RESULT_DIR = ROOT / "results" / "tmt_ccle_depmap"
HITS_TSV = RESULT_DIR / "PXD011967_search_target_hits.tsv"
PROGRESS_TSV = RESULT_DIR / "PXD011967_search_download_progress.tsv"


def load_search_rows() -> list[dict[str, str]]:
    rows = list(csv.DictReader(META_TSV.open("r", encoding="utf-8"), delimiter="\t"))
    search_rows = [r for r in rows if (r.get("file_category") or "").upper() == "SEARCH"]

    # De-duplicate exact repeated URLs in metadata listings.
    unique: list[dict[str, str]] = []
    seen = set()
    for r in search_rows:
        key = r.get("ftp_url", "")
        if key and key not in seen:
            unique.append(r)
            seen.add(key)
    return unique


def compile_patterns() -> dict[str, re.Pattern[str]]:
    # Include core symbols plus common aliases for MYMK/MYMX.
    return {
        "MYMK": re.compile(r"\b(MYMK|TMEM8C|MYOMAKER)\b", re.IGNORECASE),
        "MYMX": re.compile(r"\b(MYMX|MYOMIXER|MINION)\b", re.IGNORECASE),
        "MYOD1": re.compile(r"\bMYOD1\b", re.IGNORECASE),
        "MYOG": re.compile(r"\bMYOG\b", re.IGNORECASE),
    }


def local_name(row: dict[str, str]) -> str:
    """
    Create a stable, collision-safe local filename.
    Rationale: PRIDE listings can include repeated basenames from different locations.
    """
    base = row.get("file_name", "unknown.dat")
    checksum = (row.get("checksum") or "").strip()
    if checksum:
        suffix = checksum[:10]
    else:
        suffix = hashlib.sha1((row.get("ftp_url") or "").encode("utf-8")).hexdigest()[:10]
    if "." in base:
        stem, ext = base.rsplit(".", 1)
        return f"{stem}.{suffix}.{ext}"
    return f"{base}.{suffix}"


def scan_file_text(path: Path, patterns: dict[str, re.Pattern[str]]) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return {k: len(p.findall(text)) for k, p in patterns.items()}


def append_tsv(path: Path, fieldnames: list[str], row: dict[str, str]) -> None:
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        if not exists:
            w.writeheader()
        w.writerow(row)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-files", type=int, default=0, help="Optional limit for a dry run; 0 means all files.")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    rows = load_search_rows()
    if args.max_files and args.max_files > 0:
        rows = rows[: args.max_files]

    patterns = compile_patterns()

    hit_fields = [
        "local_file_name",
        "file_name",
        "ftp_url",
        "MYMK_hits",
        "MYMX_hits",
        "MYOD1_hits",
        "MYOG_hits",
        "any_target_hit",
    ]
    progress_fields = ["file_name", "status", "expected_size_bytes", "local_size_bytes", "note"]

    for i, r in enumerate(rows, start=1):
        file_name = r.get("file_name", "")
        ftp_url = r.get("ftp_url", "")
        expected_size = int(r.get("file_size_bytes") or 0)
        safe_name = local_name(r)
        local_path = OUT_DIR / safe_name

        # Skip downloads that already match expected size.
        if local_path.exists() and local_path.stat().st_size == expected_size and expected_size > 0:
            status = "already_present"
        else:
            try:
                # Always perform a clean download to avoid append-related corruption.
                tmp_path = local_path.with_suffix(local_path.suffix + ".part")
                if tmp_path.exists():
                    tmp_path.unlink()
                subprocess.check_call(["wget", "-q", "-O", str(tmp_path), ftp_url])
                tmp_path.replace(local_path)
                status = "downloaded"
            except Exception as exc:
                if local_path.exists():
                    local_path.unlink()
                tmp_path = local_path.with_suffix(local_path.suffix + ".part")
                if tmp_path.exists():
                    tmp_path.unlink()
                append_tsv(
                    PROGRESS_TSV,
                    progress_fields,
                    {
                        "file_name": file_name,
                        "status": "download_failed",
                        "expected_size_bytes": str(expected_size),
                        "local_size_bytes": str(local_path.stat().st_size if local_path.exists() else 0),
                        "note": str(exc),
                    },
                )
                continue

        local_size = local_path.stat().st_size if local_path.exists() else 0
        size_ok = (expected_size == 0) or (local_size == expected_size)
        if not size_ok:
            append_tsv(
                PROGRESS_TSV,
                progress_fields,
                {
                    "file_name": file_name,
                    "status": "size_mismatch",
                    "expected_size_bytes": str(expected_size),
                    "local_size_bytes": str(local_size),
                    "note": "Downloaded bytes do not match metadata size.",
                },
            )
            continue

        counts = scan_file_text(local_path, patterns)
        any_hit = any(v > 0 for v in counts.values())

        append_tsv(
            HITS_TSV,
            hit_fields,
            {
                "local_file_name": safe_name,
                "file_name": file_name,
                "ftp_url": ftp_url,
                "MYMK_hits": str(counts["MYMK"]),
                "MYMX_hits": str(counts["MYMX"]),
                "MYOD1_hits": str(counts["MYOD1"]),
                "MYOG_hits": str(counts["MYOG"]),
                "any_target_hit": "true" if any_hit else "false",
            },
        )
        append_tsv(
            PROGRESS_TSV,
            progress_fields,
            {
                "file_name": file_name,
                "status": status,
                "expected_size_bytes": str(expected_size),
                "local_size_bytes": str(local_size),
                "note": f"processed_file_{i}_of_{len(rows)}",
            },
        )

    print(f"Processed {len(rows)} SEARCH files.")
    print(f"Progress table: {PROGRESS_TSV}")
    print(f"Hit table: {HITS_TSV}")


if __name__ == "__main__":
    main()
