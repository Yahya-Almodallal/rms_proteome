#!/usr/bin/env python3
"""
Download all files listed in a pre-download manifest and verify checksums.

Beginner notes:
- The manifest is a TSV file with one file per row.
- We download each file into an output folder.
- After download, we compute a hash and compare it to the expected checksum.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
from pathlib import Path
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse
from urllib.request import urlopen


def compute_hash(path: Path, checksum_type: str) -> str:
    """Compute file hash using the algorithm listed in the manifest."""
    algo = checksum_type.lower()
    if algo not in {"md5", "sha1", "sha256"}:
        raise ValueError(f"Unsupported checksum type: {checksum_type}")

    digest = hashlib.new(algo)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ftp_to_https(ftp_url: str) -> str:
    """
    Convert PRIDE FTP URLs to HTTPS URLs for easier firewall compatibility.

    Example:
    ftp://ftp.pride.ebi.ac.uk/pride/data/... -> https://ftp.pride.ebi.ac.uk/pride/data/...
    """
    if ftp_url.startswith("ftp://ftp.pride.ebi.ac.uk/"):
        return "https://ftp.pride.ebi.ac.uk/" + ftp_url.split("ftp://ftp.pride.ebi.ac.uk/", 1)[1]
    return ftp_url


def download_file(url: str, destination: Path) -> None:
    """Download one URL to destination path."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out, length=1024 * 1024)


def choose_url(row: dict[str, str]) -> str:
    """Pick the best URL for downloading."""
    ftp_url = row.get("ftp_url", "").strip()
    if ftp_url:
        return ftp_to_https(ftp_url)
    raise ValueError(f"No download URL found for file: {row.get('file_name', '')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download files listed in a manifest TSV")
    parser.add_argument(
        "--manifest",
        default="metadata/surfaceome_pxd039480/download_manifest_pxd039480.tsv",
        help="Path to manifest TSV",
    )
    parser.add_argument(
        "--outdir",
        default="data/surfaceome/PXD039480/raw",
        help="Directory where files will be stored",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    outdir = Path(args.outdir)

    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")

    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    if not rows:
        raise SystemExit("Manifest has no rows.")

    ok = 0
    skipped = 0

    for row in rows:
        file_name = row["file_name"].strip()
        expected_checksum = row.get("checksum", "").strip().lower()
        checksum_type = row.get("checksum_type", "").strip().lower() or "sha1"
        url = choose_url(row)
        target_path = outdir / file_name

        # Skip re-download if file already exists and hash matches.
        if target_path.exists() and expected_checksum:
            current = compute_hash(target_path, checksum_type)
            if current.lower() == expected_checksum:
                print(f"[skip] {file_name} (already downloaded, checksum OK)")
                skipped += 1
                continue
            print(f"[warn] {file_name} exists but checksum mismatch; re-downloading")

        print(f"[download] {file_name}")
        print(f"          URL: {urlparse(url).scheme}://{urlparse(url).netloc}{urlparse(url).path}")
        try:
            download_file(url, target_path)
        except (HTTPError, URLError) as err:
            raise SystemExit(f"Download failed for {file_name}: {err}") from err

        if expected_checksum:
            actual = compute_hash(target_path, checksum_type)
            if actual.lower() != expected_checksum:
                raise SystemExit(
                    f"Checksum failed for {file_name}: expected {expected_checksum}, got {actual}"
                )

        print(f"[ok] {file_name}")
        ok += 1

    print(f"Done. Downloaded: {ok}, skipped: {skipped}, total listed: {len(rows)}")


if __name__ == "__main__":
    main()
