#!/usr/bin/env python3
"""
Build HPC-oriented download manifests for large external proteomics resources.

This script does not download data itself.
It converts the metadata we already collected into small, explicit files that
can be copied to an HPC scratch space and used there.

Current scope:
- PXD030304: fully enumerated from PRIDE metadata, so we can build exact
  manifests and command lists with sizes/checksums.
- MSV000085836: only partially enumerated locally, so we record the known root
  locations and provide a mirror plan rather than pretending we have a full
  file manifest.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "metadata" / "tmt_ccle_depmap" / "hpc_downloads"

PXD030304_FILES = ROOT / "metadata" / "tmt_ccle_depmap" / "pride" / "PXD030304_files.tsv"
MSV000085836_INDEX = ROOT / "metadata" / "tmt_ccle_depmap" / "massive" / "MSV000085836_index.tsv"


def load_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def build_pxd030304_manifests() -> dict[str, object]:
    rows = load_tsv(PXD030304_FILES)

    raw_rows = [r for r in rows if r.get("file_category") == "RAW"]
    large_rows = [r for r in rows if int(r.get("file_size_bytes") or 0) >= 1_000_000_000]
    diann_rows = [r for r in rows if "DIANN" in r.get("file_name", "").upper() or r.get("file_name", "").endswith(".tsv")]

    raw_manifest = [
        {
            "accession": r["accession"],
            "file_name": r["file_name"],
            "file_size_bytes": r["file_size_bytes"],
            "checksum": r["checksum"],
            "file_category": r["file_category"],
            "ftp_url": r["ftp_url"],
            "aspera_url": r["aspera_url"],
        }
        for r in raw_rows
    ]
    raw_manifest.sort(key=lambda r: r["file_name"])

    large_manifest = [
        {
            "accession": r["accession"],
            "file_name": r["file_name"],
            "file_size_bytes": r["file_size_bytes"],
            "checksum": r["checksum"],
            "file_category": r["file_category"],
            "ftp_url": r["ftp_url"],
            "aspera_url": r["aspera_url"],
        }
        for r in large_rows
    ]
    large_manifest.sort(key=lambda r: int(r["file_size_bytes"]), reverse=True)

    write_tsv(OUT / "PXD030304_raw_manifest.tsv", raw_manifest)
    write_tsv(OUT / "PXD030304_large_files_manifest.tsv", large_manifest)

    # Simple command lists are useful on HPC because they can be fed to GNU
    # parallel or inspected before any transfer starts.
    with (OUT / "PXD030304_wget_commands.txt").open("w", encoding="utf-8") as handle:
        for row in large_manifest:
            handle.write(f"wget -c '{row['ftp_url']}'\n")

    with (OUT / "PXD030304_aspera_commands.txt").open("w", encoding="utf-8") as handle:
        for row in large_manifest:
            # The remote path after the colon is what ascp needs.
            remote = row["aspera_url"]
            handle.write(f"ascp -QT -l 300m -P 33001 {remote} .\n")

    return {
        "record_count_total": len(rows),
        "record_count_raw": len(raw_manifest),
        "record_count_large_ge_1gb": len(large_manifest),
        "total_bytes_all_files": sum(int(r.get("file_size_bytes") or 0) for r in rows),
        "total_bytes_raw": sum(int(r.get("file_size_bytes") or 0) for r in raw_rows),
        "total_bytes_large_ge_1gb": sum(int(r.get("file_size_bytes") or 0) for r in large_rows),
        "diann_related_files": [r["file_name"] for r in diann_rows],
    }


def build_msv000085836_plan() -> dict[str, object]:
    rows = load_tsv(MSV000085836_INDEX)

    # The local index is only partial. We keep the known roots explicit so the
    # HPC job can mirror them recursively from source instead of depending on
    # our incomplete one-level crawl.
    root_urls = {
        "metadata": "ftp://massive-ftp.ucsd.edu/v03/MSV000085836/metadata/",
        "sequence": "ftp://massive-ftp.ucsd.edu/v03/MSV000085836/sequence/",
        "raw_recursive_root": "ftp://massive-ftp.ucsd.edu/v03/MSV000085836/raw/raw/",
    }

    plan = {
        "accession": "MSV000085836",
        "local_index_note": (
            "The local MassIVE index is one-level deep only. Use recursive mirroring "
            "from the raw/root FTP paths on HPC to obtain the actual raw-file set."
        ),
        "known_root_urls": root_urls,
        "known_nonraw_files_from_local_index": [
            {
                "name": row["name"],
                "href": row["href"],
                "size_or_target": row["size_or_target"],
                "parent": row["parent"],
            }
            for row in rows
            if row.get("entry_type") == "File"
        ],
    }

    (OUT / "MSV000085836_download_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    return plan


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    summary = {
        "PXD030304": build_pxd030304_manifests(),
        "MSV000085836": build_msv000085836_plan(),
    }

    (OUT / "hpc_download_manifest_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print(OUT / "PXD030304_raw_manifest.tsv")
    print(OUT / "PXD030304_large_files_manifest.tsv")
    print(OUT / "PXD030304_wget_commands.txt")
    print(OUT / "PXD030304_aspera_commands.txt")
    print(OUT / "MSV000085836_download_plan.json")
    print(OUT / "hpc_download_manifest_summary.json")


if __name__ == "__main__":
    main()
