# Metadata Folder

This folder stores machine-readable snapshots of repository files.

- `files_manifest.tsv`: one row per file with hash + size + modified time.
- `files_metadata.json`: same data in JSON format for scripting.

Regenerate with:

```bash
python3 scripts/00_build_manifest.py --root . --outdir metadata
```
