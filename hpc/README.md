# rms_proteome HPC handoff

This is the minimal HPC scaffold for the current proteomics work.

It is intentionally small.

What it does:
- centralizes HPC paths in one env file
- builds the large-download manifests already defined in the repo
- previews and submits the `MSV000085836` recursive MassIVE mirror job
- previews and submits the first-pass `MSV000085836` MSFragger/Philosopher search

What it does not do:
- it does not implement a full proteomics processing pipeline
- it does not submit large batch waves
- it does not implement final TMT reporter-ion quantification yet

Default HPC paths:
- repo clone: `/users/almrb2/rms_proteome`
- downloads root: `/scratch/almrb2/rms.omics/proteomics`

Recommended order on HPC:

```bash
cd /users/almrb2/rms_proteome
source hpc/env/rms_proteome_hpc.env.sh
bash hpc/scripts/check_rms_proteome_hpc_env.sh
bash hpc/jobs/build_download_manifests.sh
bash hpc/jobs/preview_msv000085836_download.sh 4 8000 48:00
bash hpc/jobs/submit_msv000085836_download.sh 4 8000 48:00
bash hpc/jobs/build_msv000085836_target_subset.sh
bash hpc/jobs/stage_msv000085836_target_subset.sh
bash hpc/jobs/preview_msv000085836_search.sh 8 96 48:00
bash hpc/jobs/submit_msv000085836_search.sh 8 96 48:00
```

Current job scope:
- `MSV000085836`: recursive MassIVE mirror onto scratch
- `PXD030304`: manifest generation only for now
- `MSV000085836` target subset: local manifest + symlink staging for the 5 plexes of interest
- `MSV000085836` target subset search: first-pass closed TMT10 identification search

Important note:
- the actual large files should land under `${RMS_PROTEOME_DOWNLOADS_ROOT}`
- the repo on home should stay small
- `MSFragger.jar` is expected under `${RMS_PROTEOME_TOOLS_ROOT}/msfragger/MSFragger.jar`
- `philosopher` is expected under `${RMS_PROTEOME_TOOLS_ROOT}/philosopher/philosopher`
