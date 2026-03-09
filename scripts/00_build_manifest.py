#!/usr/bin/env python3
"""
Build a reproducible file manifest and metadata snapshot for this repository.

This script is intentionally simple and heavily commented for beginners.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass
class FileRecord:
    """A single file entry for the manifest."""

    path: str
    size_bytes: int
    mtime_utc: str
    sha256: str


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA-256 safely by reading in chunks (good for large files)."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def should_skip(path: Path) -> bool:
    """
    Skip files that are not useful as scientific source inputs.

    We skip `.git/` internals and Windows Zone.Identifier sidecar files.
    """
    parts = set(path.parts)
    if ".git" in parts:
        return True
    if path.name.endswith(":Zone.Identifier"):
        return True
    # Avoid self-reference: generated manifest files should not hash themselves.
    if "metadata" in path.parts and path.name in {"files_manifest.tsv", "files_metadata.json"}:
        return True
    return False


def iter_files(root: Path) -> Iterable[Path]:
    """Yield all files under root in a stable sorted order."""
    for path in sorted(root.rglob("*")):
        if path.is_file() and not should_skip(path):
            yield path


def build_records(root: Path) -> list[FileRecord]:
    """Create file records for every relevant file in the repository."""
    records: list[FileRecord] = []
    for file_path in iter_files(root):
        stat = file_path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        rel = file_path.relative_to(root).as_posix()
        records.append(
            FileRecord(
                path=rel,
                size_bytes=stat.st_size,
                mtime_utc=mtime,
                sha256=sha256_file(file_path),
            )
        )
    return records


def write_tsv(records: list[FileRecord], out_path: Path) -> None:
    """Write a simple TSV manifest that is easy to inspect manually."""
    header = "path\tsize_bytes\tmtime_utc\tsha256\n"
    lines = [header]
    for rec in records:
        lines.append(f"{rec.path}\t{rec.size_bytes}\t{rec.mtime_utc}\t{rec.sha256}\n")
    out_path.write_text("".join(lines), encoding="utf-8")


def write_json(records: list[FileRecord], out_path: Path) -> None:
    """Write structured metadata for scripted reuse."""
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "record_count": len(records),
        "records": [asdict(r) for r in records],
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build repository file manifest + metadata")
    parser.add_argument("--root", default=".", help="Repository root directory")
    parser.add_argument("--outdir", default="metadata", help="Output directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    outdir = Path(args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    records = build_records(root)
    write_tsv(records, outdir / "files_manifest.tsv")
    write_json(records, outdir / "files_metadata.json")

    print(f"Wrote {len(records)} records to {outdir}")


if __name__ == "__main__":
    main()
