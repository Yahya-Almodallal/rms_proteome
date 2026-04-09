#!/usr/bin/env python3
"""
Prepare a contained MSFragger search workspace for the MSV000085836 target subset.

What this script does:
- links mzML files into one search directory
- writes a closed-search MSFragger parameter file for a first-pass TMT10 search

Why this exists:
- MSFragger writes outputs next to the mzML inputs
- we want the search outputs isolated under one scratch folder
- the user is inspecting four target proteins first, not building a final
  publication-grade TMT quantification workflow

Important limitation:
- this is a rescue/inspection search recipe
- it is appropriate for peptide/protein identification support
- it is not yet the final reporter-ion quantification workflow
"""

from __future__ import annotations

import argparse
from pathlib import Path


PARAMS_TEXT = """# MSFragger closed-search parameters for a first-pass TMT10 inspection.
# This file is intentionally explicit so a beginner can see what was set.

database_name = {fasta}
num_threads = {threads}
output_format = tsv_pepXML

# Orbitrap-style precursor and fragment tolerances.
precursor_mass_lower = -20
precursor_mass_upper = 20
precursor_mass_units = 1
precursor_true_tolerance = 20
precursor_true_units = 1
fragment_mass_tolerance = 20
fragment_mass_units = 1

# Enzyme settings.
search_enzyme_name = trypsin
search_enzyme_cutafter = KR
search_enzyme_butnotafter = P
num_enzyme_termini = 2
allowed_missed_cleavage = 2

# Peptide constraints.
digest_min_length = 7
digest_max_length = 50
digest_mass_range = 500.0 5000.0

# Fixed modifications.
add_C_cysteine = 57.021464
add_K_lysine = 229.162932
add_Nterm_peptide = 229.162932

# Minimal variable modifications for a first pass.
variable_mod_01 = 15.9949 M 3
variable_mod_02 = 42.0106 [^ 1
allow_multiple_variable_mods_on_residue = 0
max_variable_mods_per_peptide = 3
max_variable_mods_combinations = 65534

# Basic precursor/isotope behavior.
isotope_error = 0/1/2
mass_offsets = 0
deisotope = 1
search_mode = 1

# Basic spectrum filtering.
minimum_peaks = 10
use_topN_peaks = 150
minimum_ratio = 0.01
clear_mz_range = 0.0 0.0
remove_precursor_peak = 0
remove_precursor_range = -1.5 1.5

# Peptide generation behavior.
clip_nTerm_M = 1
allow_multiple_variable_mods_on_residue = 0
max_fragment_charge = 3
track_zero_topN = 0
zero_bin_accept_expect = 1
"""


def link_mzml_files(mzml_dir: Path, search_dir: Path) -> list[Path]:
    linked: list[Path] = []
    for mzml_path in sorted(mzml_dir.glob("*.mzML")):
        link_path = search_dir / mzml_path.name
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
        link_path.symlink_to(mzml_path)
        linked.append(link_path)
    return linked


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mzml-dir", required=True, help="Directory containing converted mzML files.")
    ap.add_argument("--search-dir", required=True, help="Contained search workspace on scratch.")
    ap.add_argument("--fasta", required=True, help="FASTA file used for searching.")
    ap.add_argument("--threads", type=int, default=8, help="Thread count to write into the params file.")
    ap.add_argument("--params-name", default="msv000085836_tmt10_closed.params")
    args = ap.parse_args()

    mzml_dir = Path(args.mzml_dir)
    search_dir = Path(args.search_dir)
    fasta = Path(args.fasta)

    if not mzml_dir.is_dir():
        raise SystemExit(f"mzML directory not found: {mzml_dir}")
    if not fasta.is_file():
        raise SystemExit(f"FASTA not found: {fasta}")

    search_dir.mkdir(parents=True, exist_ok=True)
    linked = link_mzml_files(mzml_dir, search_dir)
    if not linked:
        raise SystemExit(f"No mzML files found under {mzml_dir}")

    params_path = search_dir / args.params_name
    params_path.write_text(
        PARAMS_TEXT.format(fasta=fasta, threads=args.threads),
        encoding="utf-8",
    )

    print(params_path)
    print(f"linked_mzml_files\t{len(linked)}")


if __name__ == "__main__":
    main()
