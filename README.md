# Automated ASPECTS scoring from NCCT

Research prototype for an explainable, AISD-first pipeline. It is not a clinical device and must not be used for patient care without prospective validation, regulatory review, and radiologist oversight.

## First data-access actions

1. Start the AISD access/download process immediately. Record the source URL, version, access date, license/terms, and checksum in `data/README.md`. Do not commit scans or patient identifiers.
2. Submit the APIS registration form in parallel through the dataset provider. APIS is a later external validation set, not a dependency for the MVP.
3. Download the NCCT ASPECTS atlas from the linked Figshare record or the authors' repository. Store atlas files under `data/atlas/` and record their checksums.

The public AISD paper describes the dataset and task, but the paper page is not itself a download endpoint. Use the dataset access route supplied by the authors or host institution and preserve the terms of use.

## MVP scope

The first reproducible milestone is a rule-based baseline:

- load one NCCT volume and its metadata;
- normalize orientation and preserve calibrated HU;
- estimate a conservative HU-based brain mask and midline, with quality flags;
- align an atlas label volume to the scan with affine registration;
- compute mirrored contralateral density differences;
- produce per-region flags, score, heatmap, overlay, and JSON explanation.

The code deliberately keeps region decisions rule-based. A learned detector can later consume the same registered volumes and mirror-difference channels without changing the scoring contract.

## Expected local layout

```text
data/
  raw/aisd/                 # ignored by git
  raw/apis/                 # ignored by git
  atlas/                    # downloaded atlas resources
  manifests/aisd.csv       # case_id,ct_path,lesion_path,split
outputs/
src/aspects_stroke/
```

Use NIfTI (`.nii` or `.nii.gz`) for the first prototype. Convert DICOM series with a documented conversion tool before ingestion; never silently reorder slices.

## Setup on Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run a single case after placing a CT and an atlas label volume locally:

```powershell
aspects-score `
  --ct data/raw/aisd/example_ct.nii.gz `
  --atlas-labels data/atlas/aspects_labels.nii.gz `
  --output outputs/example
```

This baseline expects atlas labels encoded as integers `1..10`, with the region mapping documented in `data/atlas/README.md`. It will refuse to claim a score when a required region is absent or registration quality is inadequate.

For an atlas that is not already on the CT grid, provide the atlas intensity image as well. The CLI performs affine registration and nearest-neighbor label resampling:

```powershell
aspects-score `
  --ct data/raw/aisd/example_ct.nii.gz `
  --atlas-image data/atlas/atlas_brain.nii.gz `
  --atlas-labels data/atlas/aspects_labels.nii.gz `
  --output outputs/example
```

The output directory contains `ischemia_heatmap.nii.gz`, `overlay.png`, and `result.json`. The JSON includes per-region HU values, asymmetry, preprocessing quality flags, and registration metadata. A quality warning means the result requires manual review and should be treated as an abstention during evaluation.

For the downloaded age-specific two-level atlas, use BGL and SGL together:

```powershell
aspects-score `
  --ct data/processed/aisd/0019983_ct.nii.gz `
  --bgl-image data/atlas/BGL_image_70_89.nii.gz `
  --bgl-labels data/atlas/BGL_label_70_89.nii.gz `
  --sgl-image data/atlas/SGL_image_70_89.nii.gz `
  --sgl-labels data/atlas/SGL_label_70_89.nii.gz `
  --output outputs/0019983
```

This registers the two 2D levels independently, combines labels `1..7` and `8..10`, and renders overlays on the selected slices.

For the full converted manifest, let the batch runner select the atlas by each case's DICOM age:

```powershell
aspects-batch `
  --manifest data/processed/aisd/manifest.csv `
  --atlas-dir data/atlas/downloaded/ASPECTS-281 `
  --output outputs/aisd `
  --workers 6
```

Cases with missing age metadata are marked `abstain` and are not scored.
On an Intel i5-12450H, start with `--workers 6`. SimpleITK is limited to one thread per worker to prevent CPU oversubscription; lower this to `4` if memory pressure occurs.

## AISD evaluation

After rerunning scoring so each case contains `registered_regions.nii.gz`, evaluate against the AISD masks:

```powershell
aspects-evaluate `
  --manifest data/processed/aisd/known_age_manifest.csv `
  --output outputs/aisd_known_age `
  --output outputs/aisd_retry `
  --report outputs/evaluation.json
```

This reports lesion Dice and per-region flag agreement. Abstained cases are reported separately and excluded from scored metrics.

To explore a better heatmap threshold against AISD masks:

```powershell
aspects-tune `
  --manifest data/processed/aisd/known_age_manifest.csv `
  --output outputs/aisd_known_age `
  --output outputs/aisd_retry `
  --report outputs/threshold_tuning.json `
  --max-cases 50 `
  --start 0.02 `
  --stop 0.20 `
  --step 0.02
```

The result is exploratory because the current manifest splits are `unassigned`. Do not use the selected threshold as a test-set result until train/validation/test splits are defined.

Create the fixed age-stratified model split before training:

```powershell
aspects-split `
  --input data/processed/aisd/manifest.csv `
  --output data/processed/aisd/model_manifest.csv
```

The command excludes unknown-age and missing-file cases and assigns reproducible `train`, `validation`, and `test` labels using seed `20260908`.

## Batch AISD processing

Copy `data/manifests/aisd.example.csv` to `data/manifests/aisd.csv`, replace its example row with real AISD paths, and remove the comment row. Run from the project root:

```powershell
aspects-batch `
  --manifest data/manifests/aisd.csv `
  --bgl-image data/atlas/BGL_image_70_89.nii.gz `
  --bgl-labels data/atlas/BGL_label_70_89.nii.gz `
  --sgl-image data/atlas/SGL_image_70_89.nii.gz `
  --sgl-labels data/atlas/SGL_label_70_89.nii.gz `
  --output outputs/aisd `
  --split train
```

Each case gets its own `result.json`; `summary.json` aggregates scored, abstained, and errored cases. Batch processing continues after a failed case.

## Validation plan

1. Unit-test HU symmetry and score arithmetic on synthetic volumes.
2. Manually review registration and overlays on 5-10 AISD cases.
3. Tune thresholds only on the training split, then lock them.
4. Report lesion Dice, region-level sensitivity/specificity, score MAE, agreement with expert ASPECTS, and failure/abstention rate.
5. Evaluate APIS only as a held-out external test set if access arrives.

## Clinical safety

The output is decision support research only. It must expose uncertainty and abstain when registration, midline, or coverage checks fail. A numeric ASPECTS score without its overlay and quality flags is not an acceptable final output.
