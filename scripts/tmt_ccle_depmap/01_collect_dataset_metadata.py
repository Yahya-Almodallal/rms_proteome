#!/usr/bin/env python3
"""
Collect metadata for requested RMS proteomics datasets.

Outputs are written under metadata/tmt_ccle_depmap/.
This script uses only standard-library modules for portability.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import zipfile
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path("/home/yahya/Scripts/rms_proteome")
OUT = ROOT / "metadata" / "tmt_ccle_depmap"
INDEX_CSV = OUT / "depmap_files_index.csv"

PRIDE_ACCESSIONS = [
    "PXD011967",
    "PXD034908",
    "PXD030304",
    "PXD042840",
    "PXD052488",
    "PXD035131",
]

MASSIVE_ACCESSIONS = ["MSV000085836", "MSV000086494"]
TARGET_MSV_LINES = ["A-204", "RD", "RH-30", "KYM-1", "RH-41"]

PXD030304_MODELS = [
    "RH-18", "RD", "TE-125-T", "KYM-1", "A204", "TE-441-T", "RH-3", "SCMC-RM2",
    "RH-JT", "RH-36", "SJRH30", "RH-28", "SMS-CTR", "RH-4", "TTC-442", "CW9019",
    "DL", "JR", "SCMC-RM2-1", "Hs-729-T", "TE-617-T", "TE-159-T", "RMZ-RC2",
    "RMZ", "RMZ-RC5", "RH-41", "RMS-YM",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_text(url: str) -> str:
    req = Request(url, headers={"User-Agent": "rms_proteome-metadata/1.0"})
    with urlopen(req) as r:
        return r.read().decode("utf-8", errors="replace")


def get_json(url: str) -> Any:
    return json.loads(get_text(url))


class FtpIndexParser(HTMLParser):
    """Parse Apache-style FTP directory index HTML rows into structured entries."""

    def __init__(self) -> None:
        super().__init__()
        self.in_pre = False
        self.lines: list[str] = []
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "pre":
            self.in_pre = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "pre":
            self.in_pre = False

    def handle_data(self, data: str) -> None:
        if self.in_pre:
            self._buf.append(data)

    def close(self) -> None:
        super().close()
        if self._buf:
            joined = "".join(self._buf)
            self.lines = joined.splitlines()


def parse_massive_index(html: str, base_ftp: str) -> list[dict[str, str]]:
    # Parse directly from HTML so <a href> attributes are preserved.
    line_re = re.compile(
        r"\s*(\d{4})\s+([A-Za-z]{3})\s+(\d{2})\s+"
        r"(Directory|File|Link)\s+<a href=\"([^\"]+)\">([^<]+)</a>\s*(?:\(([^\)]+)\))?"
    )
    rows: list[dict[str, str]] = []
    for m in line_re.finditer(html):
        rows.append(
            {
                "date": f"{m.group(1)}-{m.group(2)}-{m.group(3)}",
                "entry_type": m.group(4),
                "name": m.group(6).rstrip("/"),
                "href": m.group(5),
                "size_or_target": m.group(7) or "",
                "base_ftp": base_ftp,
            }
        )
    return rows


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), delimiter="\t")
        w.writeheader()
        w.writerows(rows)


def collect_pride_files() -> dict[str, dict[str, Any]]:
    out = {}
    pride_dir = OUT / "pride"
    pride_dir.mkdir(parents=True, exist_ok=True)

    for acc in PRIDE_ACCESSIONS:
        try:
            project = get_json(f"https://www.ebi.ac.uk/pride/ws/archive/v2/projects/{acc}")
        except Exception as exc:
            out[acc] = {
                "project_title": "",
                "record_count": 0,
                "total_bytes": 0,
                "error": str(exc),
            }
            # Keep a machine-readable marker file so unresolved accessions are explicit.
            (pride_dir / f"{acc}_project_error.json").write_text(
                json.dumps(
                    {
                        "accession": acc,
                        "error": str(exc),
                        "note": "Project metadata endpoint was not reachable/resolvable at runtime.",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            continue

        files: list[dict[str, Any]] = []
        page = 0
        while True:
            try:
                chunk = get_json(
                    f"https://www.ebi.ac.uk/pride/ws/archive/v2/projects/{acc}/files?page={page}&pageSize=500"
                )
            except Exception:
                break
            if not chunk:
                break
            files.extend(chunk)
            page += 1

        records: list[dict[str, Any]] = []
        for it in files:
            ftp = ""
            aspera = ""
            for loc in it.get("publicFileLocations", []):
                nm = (loc.get("name") or "").lower()
                val = loc.get("value") or ""
                if "ftp" in nm:
                    ftp = val
                if "aspera" in nm:
                    aspera = val
            records.append(
                {
                    "accession": acc,
                    "file_name": it.get("fileName", ""),
                    "file_size_bytes": it.get("fileSizeBytes", 0),
                    "checksum": it.get("checksum", ""),
                    "file_category": (it.get("fileCategory") or {}).get("value", ""),
                    "submission_date": it.get("submissionDate", ""),
                    "publication_date": it.get("publicationDate", ""),
                    "ftp_url": ftp,
                    "aspera_url": aspera,
                }
            )

        records.sort(key=lambda x: x["file_name"].lower())
        write_tsv(pride_dir / f"{acc}_files.tsv", records)
        (pride_dir / f"{acc}_project.json").write_text(json.dumps(project, indent=2), encoding="utf-8")

        out[acc] = {
            "project_title": project.get("title", ""),
            "record_count": len(records),
            "total_bytes": int(sum(int(r.get("file_size_bytes", 0) or 0) for r in records)),
        }

        if acc == "PXD034908":
            baseline_patterns = re.compile(r"baseline|day0|day 0|d0|pre", re.IGNORECASE)
            baseline = [r for r in records if baseline_patterns.search(r["file_name"])]
            write_tsv(pride_dir / "PXD034908_baseline_name_candidates.tsv", baseline)

    return out


def collect_massive_indexes() -> dict[str, Any]:
    out = {}
    massive_dir = OUT / "massive"
    massive_dir.mkdir(parents=True, exist_ok=True)

    for acc in MASSIVE_ACCESSIONS:
        root_ftp = f"ftp://massive-ftp.ucsd.edu/v03/{acc}/"
        root_html = subprocess.check_output(["wget", "-qO-", root_ftp], text=True, errors="replace")
        root_entries = parse_massive_index(root_html, root_ftp)
        for e in root_entries:
            e["level"] = "root"
            e["parent"] = ""

        all_entries = list(root_entries)
        # One-level recursion into directories (enough for metadata/raw structure capture).
        for e in root_entries:
            if e["entry_type"] == "Directory" and e["name"]:
                try:
                    # MassIVE listing sometimes emits :21 links that return empty bodies here.
                    # Building the directory URL from the entry name is more reliable.
                    sub_url = f"{root_ftp}{e['name'].strip('/')}/"
                    sub_html = subprocess.check_output(["wget", "-qO-", sub_url], text=True, errors="replace")
                    sub_entries = parse_massive_index(sub_html, sub_url)
                    for se in sub_entries:
                        se["level"] = "sub"
                        se["parent"] = e["name"]
                    all_entries.extend(sub_entries)
                except Exception:
                    pass

        write_tsv(massive_dir / f"{acc}_index.tsv", all_entries)
        out[acc] = {
            "record_count": len(all_entries),
            "top_level_entries": len(root_entries),
            "root_ftp": root_ftp,
        }

    return out


# -----------------------
# XLSX parsing helpers
# -----------------------
XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
XLSX_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def col_idx(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1


def xlsx_cell_text(cell: ET.Element, shared: list[str]) -> str:
    ctype = cell.attrib.get("t", "")
    if ctype == "inlineStr":
        t = cell.find(f"{XLSX_NS}is/{XLSX_NS}t")
        return (t.text or "") if t is not None else ""

    v = cell.find(f"{XLSX_NS}v")
    if v is None or v.text is None:
        return ""
    raw = v.text
    if ctype == "s":
        try:
            return shared[int(raw)]
        except Exception:
            return ""
    return raw


def load_shared_strings(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    out: list[str] = []
    for si in root.findall(f"{XLSX_NS}si"):
        out.append("".join((t.text or "") for t in si.iter(f"{XLSX_NS}t")))
    return out


def read_xlsx_sheet(path: Path, sheet_name: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as z:
        shared = load_shared_strings(z)
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rel = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rid_to_target = {r.attrib["Id"]: r.attrib["Target"] for r in rel}

        sheet_path = None
        for s in wb.find(f"{XLSX_NS}sheets"):
            if s.attrib.get("name") == sheet_name:
                rid = s.attrib.get(XLSX_REL, "")
                target = rid_to_target.get(rid, "")
                sheet_path = f"xl/{target}" if not target.startswith("xl/") else target
                break
        if not sheet_path:
            raise ValueError(f"Sheet not found: {sheet_name}")

        ws = ET.fromstring(z.read(sheet_path))
        rows = ws.find(f"{XLSX_NS}sheetData").findall(f"{XLSX_NS}row")
        if not rows:
            return []

        # First row is header in this file.
        header_map: dict[int, str] = {}
        for c in rows[0].findall(f"{XLSX_NS}c"):
            ref = c.attrib.get("r", "")
            if not ref:
                continue
            header_map[col_idx(ref)] = xlsx_cell_text(c, shared)

        out_rows: list[dict[str, str]] = []
        for r in rows[1:]:
            d: dict[str, str] = {}
            for c in r.findall(f"{XLSX_NS}c"):
                ref = c.attrib.get("r", "")
                if not ref:
                    continue
                i = col_idx(ref)
                if i in header_map:
                    d[header_map[i]] = xlsx_cell_text(c, shared)
            if d:
                out_rows.append(d)
        return out_rows


def norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def collect_msv000085836_target_lines() -> dict[str, Any]:
    out_dir = OUT / "msv000085836"
    out_dir.mkdir(parents=True, exist_ok=True)

    xlsx_path = out_dir / "Table_S1_Sample_Information.xlsx"
    if not xlsx_path.exists():
        # Primary metadata file listed by MassIVE.
        data = urlopen("ftp://massive-ftp.ucsd.edu/v03/MSV000085836/metadata/Table_S1_Sample_Information.xlsx").read()
        xlsx_path.write_bytes(data)

    rows = read_xlsx_sheet(xlsx_path, "Sample_Information")

    # Expected columns in this sheet are the first row values.
    # In this dataset: Cell line / CCLE name / lineage / plex / channel.
    headers = set(rows[0].keys()) if rows else set()

    target_norm = {norm(x): x for x in TARGET_MSV_LINES}
    matched: list[dict[str, str]] = []
    for r in rows:
        vals = list(r.values())
        line_name = vals[0] if len(vals) > 0 else ""
        if norm(line_name) in target_norm:
            out_row = {"requested_name": target_norm[norm(line_name)]}
            # Keep all sheet columns as-is for provenance.
            out_row.update(r)
            matched.append(out_row)

    write_tsv(out_dir / "MSV000085836_requested_cell_lines.tsv", matched)
    return {
        "sample_info_rows": len(rows),
        "sample_info_columns": sorted(headers),
        "requested_line_matches": len(matched),
    }


def depmap_file_url(release_prefix: str, filename: str) -> str:
    with INDEX_CSV.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            if row["release"].startswith(release_prefix) and row["filename"] == filename:
                return row["url"]
    raise KeyError(f"URL not found for {release_prefix} / {filename}")


def download_csv(url: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "rms_proteome-metadata/1.0"})
    with urlopen(req) as r, out_path.open("wb") as w:
        w.write(r.read())


def collect_pxd030304_availability() -> dict[str, Any]:
    out_dir = OUT / "pxd030304_depmap"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Use stable 24Q4 figshare URLs for mapping matrices.
    model_url = depmap_file_url("DepMap Public 24Q4", "Model.csv")
    omics_profiles_url = depmap_file_url("DepMap Public 24Q4", "OmicsProfiles.csv")
    crispr_map_url = depmap_file_url("DepMap Public 24Q4", "CRISPRScreenMap.csv")

    prism_cell_meta_url = depmap_file_url(
        "PRISM Primary Repurposing DepMap Public 24Q2",
        "Repurposing_Public_24Q2_Cell_Line_Meta_Data.csv",
    )
    proteomics_url = depmap_file_url("Harmonized Public Proteomics 24Q4", "harmonized_MS_CCLE_Gygi.csv")
    methyl_url = depmap_file_url("Methylation (RRBS)", "CCLE_RRBS_TSS_1kb_20180614.txt")

    paths = {
        "model": out_dir / "Model_24Q4.csv",
        "omics_profiles": out_dir / "OmicsProfiles_24Q4.csv",
        "crispr_map": out_dir / "CRISPRScreenMap_24Q4.csv",
        "prism_cell_meta": out_dir / "Repurposing_Public_24Q2_Cell_Line_Meta_Data.csv",
        "proteomics": out_dir / "harmonized_MS_CCLE_Gygi_24Q4.csv",
    }

    if not paths["model"].exists():
        download_csv(model_url, paths["model"])
    if not paths["omics_profiles"].exists():
        download_csv(omics_profiles_url, paths["omics_profiles"])
    if not paths["crispr_map"].exists():
        download_csv(crispr_map_url, paths["crispr_map"])
    if not paths["prism_cell_meta"].exists():
        download_csv(prism_cell_meta_url, paths["prism_cell_meta"])
    if not paths["proteomics"].exists():
        download_csv(proteomics_url, paths["proteomics"])

    # Build model map (requested name -> ModelID/CCLEName where available).
    model_rows = list(csv.DictReader(paths["model"].open("r", encoding="utf-8", newline="")))

    requested_norm = {norm(x): x for x in PXD030304_MODELS}
    matched_models: dict[str, dict[str, str]] = {}

    for row in model_rows:
        candidates = [
            row.get("CellLineName", ""),
            row.get("StrippedCellLineName", ""),
            row.get("CCLEName", "").split("_")[0],
        ]
        cand_norms = {norm(c) for c in candidates if c}
        for n, req in requested_norm.items():
            if n in cand_norms and req not in matched_models:
                matched_models[req] = {
                    "ModelID": row.get("ModelID", ""),
                    "CellLineName": row.get("CellLineName", ""),
                    "CCLEName": row.get("CCLEName", ""),
                    "OncotreeLineage": row.get("OncotreeLineage", ""),
                }

    # Omics profiles: infer DNA/RNA availability (Profile datatype grouping).
    omics_rows = csv.DictReader(paths["omics_profiles"].open("r", encoding="utf-8", newline=""))
    has_dna = set()
    has_rna = set()
    for row in omics_rows:
        model_id = row.get("ModelID", "")
        dtype = (row.get("Datatype") or "").lower()
        if not model_id:
            continue
        if dtype == "dna" or dtype == "wes":
            has_dna.add(model_id)
        if dtype == "rna":
            has_rna.add(model_id)

    # CRISPR availability via screen map.
    crispr_rows = csv.DictReader(paths["crispr_map"].open("r", encoding="utf-8", newline=""))
    has_crispr = {r.get("ModelID", "") for r in crispr_rows if r.get("ModelID")}

    # Drug (PRISM) availability.
    prism_rows = list(csv.DictReader(paths["prism_cell_meta"].open("r", encoding="utf-8", newline="")))
    has_drug_model = set()
    has_drug_name_norm = set()
    for r in prism_rows:
        for k, v in r.items():
            if not v:
                continue
            if "model" in k.lower() and v.startswith("ACH-"):
                has_drug_model.add(v)
            if "cell" in k.lower() or "ccle" in k.lower() or "name" in k.lower():
                has_drug_name_norm.add(norm(v.split("_")[0]))

    # Proteomics availability.
    # harmonized_MS_CCLE_Gygi_24Q4.csv is a matrix where row[0] is ModelID (ACH-...).
    # Using row values is more robust than trying to infer IDs from column headers.
    has_prot_model = set()
    with paths["proteomics"].open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        _ = next(reader, None)  # header
        for row in reader:
            if not row:
                continue
            candidate = (row[0] or "").strip()
            if candidate.startswith("ACH-"):
                has_prot_model.add(candidate)

    # DNA methylation availability (legacy matrix header has CCLE sample names as columns).
    methyl_header = get_text(methyl_url).splitlines()[0]
    methyl_cols = methyl_header.split("\t")
    methyl_name_norm = {norm(c.split("_")[0]) for c in methyl_cols if c}

    availability_rows: list[dict[str, Any]] = []
    for req in PXD030304_MODELS:
        m = matched_models.get(req, {})
        model_id = m.get("ModelID", "")
        ccle = m.get("CCLEName", "")
        ccle_norm = norm(ccle.split("_")[0]) if ccle else norm(req)

        dna = bool(model_id and model_id in has_dna)
        rna = bool(model_id and model_id in has_rna)

        availability_rows.append(
            {
                "requested_model": req,
                "matched_model_id": model_id,
                "matched_cell_line_name": m.get("CellLineName", ""),
                "matched_ccle_name": ccle,
                "mutation_data": dna,  # inference: mutation from DNA profile availability
                "cnv_data": dna,       # inference: CNV from DNA profile availability
                "rnaseq_data": rna,
                "dna_methylation_data": ccle_norm in methyl_name_norm,
                "crispr_dependency_data": bool(model_id and model_id in has_crispr),
                "drug_response_data": bool((model_id and model_id in has_drug_model) or (ccle_norm in has_drug_name_norm)),
                "fusion_data": rna,    # inference: fusions from RNA profile availability
                "proteomics_data": bool(model_id and model_id in has_prot_model),
            }
        )

    write_tsv(out_dir / "PXD030304_requested_models_modality_availability.tsv", availability_rows)
    (out_dir / "PXD030304_requested_models_modality_availability.json").write_text(
        json.dumps(
            {
                "generated_utc": now_utc(),
                "depmap_release_reference": "DepMap Public 24Q4 (plus PRISM 24Q2 and legacy RRBS/proteomics files)",
                "inference_notes": [
                    "mutation_data/cnv_data inferred from DNA-profile availability in OmicsProfiles.csv",
                    "fusion_data inferred from RNA-profile availability in OmicsProfiles.csv",
                    "drug/proteomics/methylation availability mapped by ModelID and/or normalized cell-line name matching",
                ],
                "rows": availability_rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "requested_models": len(PXD030304_MODELS),
        "matched_models": sum(1 for r in availability_rows if r["matched_model_id"]),
    }


def write_summary(summary: dict[str, Any]) -> None:
    (OUT / "metadata_collection_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    if not INDEX_CSV.exists():
        # Keep the index local for reproducibility.
        INDEX_CSV.write_text(get_text("https://depmap.org/portal/api/download/files"), encoding="utf-8")

    summary: dict[str, Any] = {
        "generated_utc": now_utc(),
        "pride": collect_pride_files(),
        "massive": collect_massive_indexes(),
        "msv000085836_target_lines": collect_msv000085836_target_lines(),
        "pxd030304_model_availability": collect_pxd030304_availability(),
    }

    write_summary(summary)
    print("Metadata collection complete.")
    print(f"Summary: {OUT / 'metadata_collection_summary.json'}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise
