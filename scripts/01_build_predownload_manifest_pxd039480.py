#!/usr/bin/env python3
"""
Build a PRE-download manifest for ProteomeXchange dataset PXD039480.

What this script does:
1) Queries the official PRIDE Archive API for the dataset file list.
2) Collects file names, file sizes, and checksums (when provided).
3) Writes a TSV and JSON manifest BEFORE downloading any raw data.

Why this matters:
- You can review exactly what will be downloaded.
- You keep reproducible metadata/provenance from the start.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


API_BASE = "https://www.ebi.ac.uk/pride/ws/archive/v2"


@dataclass
class RemoteFileRecord:
    """One remote file entry from PRIDE."""

    project_accession: str
    file_name: str
    file_size_bytes: int
    checksum: str
    checksum_type: str
    ftp_url: str
    aspera_url: str
    file_category: str
    submission_date: str
    publication_date: str
    updated_date: str


def fetch_json(url: str) -> Any:
    """Fetch JSON from a URL using only the Python standard library."""
    with urlopen(url) as response:  # nosec B310 - controlled public API URL
        return json.loads(response.read().decode("utf-8"))


def infer_checksum_type(checksum: str) -> str:
    """
    Infer checksum type from hash length.

    PRIDE often provides 40-hex checksums (SHA-1), but we infer instead of assuming.
    """
    length = len(checksum)
    if length == 32:
        return "md5"
    if length == 40:
        return "sha1"
    if length == 64:
        return "sha256"
    return "unknown"


def extract_locations(public_file_locations: list[dict[str, Any]]) -> tuple[str, str]:
    """Extract FTP and Aspera URLs from PRIDE location list."""
    ftp_url = ""
    aspera_url = ""
    for location in public_file_locations:
        name = location.get("name", "")
        value = location.get("value", "")
        if "FTP" in name.upper():
            ftp_url = value
        if "ASPERA" in name.upper():
            aspera_url = value
    return ftp_url, aspera_url


def fetch_all_project_files(project_accession: str, page_size: int = 500) -> list[RemoteFileRecord]:
    """Fetch all file pages for a PRIDE project until an empty page is reached."""
    records: list[RemoteFileRecord] = []
    page = 0

    while True:
        url = (
            f"{API_BASE}/projects/{project_accession}/files"
            f"?page={page}&pageSize={page_size}"
        )
        payload = fetch_json(url)

        if not payload:
            break

        for item in payload:
            checksum = item.get("checksum", "")
            ftp_url, aspera_url = extract_locations(item.get("publicFileLocations", []))
            category = item.get("fileCategory", {}).get("value", "")

            records.append(
                RemoteFileRecord(
                    project_accession=project_accession,
                    file_name=item.get("fileName", ""),
                    file_size_bytes=int(item.get("fileSizeBytes", 0) or 0),
                    checksum=checksum,
                    checksum_type=infer_checksum_type(checksum) if checksum else "",
                    ftp_url=ftp_url,
                    aspera_url=aspera_url,
                    file_category=category,
                    submission_date=item.get("submissionDate", ""),
                    publication_date=item.get("publicationDate", ""),
                    updated_date=item.get("updatedDate", ""),
                )
            )

        page += 1

    # Stable ordering improves reproducibility for diffs and auditing.
    records.sort(key=lambda x: x.file_name.lower())
    return records


def write_tsv(records: list[RemoteFileRecord], out_path: Path) -> None:
    """Write a tabular manifest for easy human review."""
    fieldnames = list(asdict(records[0]).keys()) if records else [
        "project_accession",
        "file_name",
        "file_size_bytes",
        "checksum",
        "checksum_type",
        "ftp_url",
        "aspera_url",
        "file_category",
        "submission_date",
        "publication_date",
        "updated_date",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))


def write_json(records: list[RemoteFileRecord], out_path: Path) -> None:
    """Write structured JSON metadata for scripts and pipelines."""
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": "PRIDE Archive API v2",
        "project_accession": "PXD039480",
        "record_count": len(records),
        "records": [asdict(record) for record in records],
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build pre-download manifest for PXD039480")
    parser.add_argument("--project", default="PXD039480", help="ProteomeXchange accession")
    parser.add_argument("--outdir", default="metadata", help="Output directory")
    args = parser.parse_args()

    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    try:
        records = fetch_all_project_files(args.project)
    except HTTPError as err:
        raise SystemExit(f"HTTP error while querying PRIDE API: {err}") from err
    except URLError as err:
        raise SystemExit(f"Network error while querying PRIDE API: {err}") from err

    if not records:
        raise SystemExit("No files returned by PRIDE API. Check accession or connectivity.")

    tsv_path = outdir / f"download_manifest_{args.project.lower()}.tsv"
    json_path = outdir / f"download_manifest_{args.project.lower()}.json"

    write_tsv(records, tsv_path)
    write_json(records, json_path)

    total_bytes = sum(r.file_size_bytes for r in records)
    total_gib = total_bytes / (1024 ** 3)

    print(f"Wrote {len(records)} files to:")
    print(f"  - {tsv_path}")
    print(f"  - {json_path}")
    print(f"Total expected size: {total_bytes} bytes ({total_gib:.2f} GiB)")


if __name__ == "__main__":
    main()
