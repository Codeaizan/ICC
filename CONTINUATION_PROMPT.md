# Continuation Prompt: Automated ASPECTS Scoring Project

You are taking over the repository at `https://github.com/Codeaizan/ICC` and the local Windows workspace `D:\Addy project`. Read this entire file before changing code.

## User and objective

The user is building an explainable automated ASPECTS system for acute ischemic stroke from non-contrast CT. The required outputs are:

1. ischemic-change segmentation or heatmap;
2. per-region flags for the ten ASPECTS regions;
3. an overall 0-10 ASPECTS score;
4. an overlay showing CT, ischemic change, and region boundaries.

This is a research prototype only. Do not describe it as clinically validated or safe for patient care.

The ten ASPECTS regions are:

1. caudate
2. lentiform nucleus
3. insula
4. internal capsule
5. M1
6. M2
7. M3
8. M4
9. M5
10. M6

Final scoring is intended to remain rule-based and explainable even if the ML lesion detector improves.

## Workspace and Git

Local workspace: `D:\Addy project`

Git remote:

```text
https://github.com/Codeaizan/ICC.git
```

Branch: `main`

The project was initialized and pushed. Recent commits:

```text
fb264cd  Add explainable ASPECTS pipeline and Colab training handoff
b39a87e  Load training slices lazily to reduce RAM usage
d56684c  Cache volumes within training workers
645a6ee  Bound training worker volume cache
a4c252e  Add fast 256 pixel training mode
9caafe5  Keep slices grouped for faster training IO
```

Git author configured locally as:

```text
Faizanur Rahman <faizanrahman51@gmail.com>
```

Before any push, run tests and lint, then commit and push. Do not commit patient data, CT volumes, masks, atlas binaries, or generated model outputs.

## Important repository files

```text
README.md                         Main setup and workflow documentation
HANDOFF.md                        Technical and plain-language project handoff
COLAB.md                          Google Colab T4 training instructions
pyproject.toml                    Dependencies and CLI entry points
src/aspects_stroke/               Main package
tests/                            Unit tests
data/README.md                   Dataset record instructions
data/atlas/README.md              Atlas label contract
data/manifests/aisd.example.csv   Example manifest
```

Main source modules:

```text
convert.py          DICOM CT series -> HU-preserving NIfTI
mask_convert.py    AISD numbered PNG mask stack -> CT-aligned NIfTI
dataset_convert.py Convert full AISD dataset and generate manifest
manifest.py        Read case manifest
split.py           Reproducible train/validation/test split
preprocess.py      Conservative HU brain mask and midline estimate
symmetry.py        Mirror volume and positive asymmetry heatmap
registration.py    3D registration and 2D BGL/SGL atlas registration
pipeline.py        Reusable one-case scoring pipeline
scoring.py         Explainable regional scoring and ASPECTS arithmetic
visualize.py       CT/heatmap/region overlay generation
batch.py           Parallel batch scoring
 evaluate.py       Lesion Dice and per-region agreement evaluation
tune.py            Exploratory heatmap-threshold tuning
train.py           2D U-Net ML baseline
cli.py             Single-case aspects-score CLI
```

There is a cosmetic filename spacing issue in this list only; the actual file is `src/aspects_stroke/evaluate.py`.

## Data that the user downloaded locally

The user downloaded AISD from the official author repository `GriffinLiang/AISD`:

```text
image.zip
mask.zip
dicom-0.tar.gz
dicom-1.tar.gz
dicom-2.tar.gz
dicom-3.zip
```

Original local AISD layout:

```text
D:\Addy project\data\raw\aisd\image\image\<case_id>\000.png ...
D:\Addy project\data\raw\aisd\mask\mask\<case_id>\000.png ...
D:\Addy project\data\raw\aisd\dicom\dicom-0\<case_id>\CT\*.dcm
D:\Addy project\data\raw\aisd\dicom\dicom-1\<case_id>\CT\*.dcm
D:\Addy project\data\raw\aisd\dicom\dicom-2\<case_id>\CT\*.dcm
D:\Addy project\data\raw\aisd\dicom\dicom-3\<case_id>\CT\*.dcm
```

The DICOM case folders also contain DWI, but only CT is used for this project.

AISD facts from the official README/paper:

- 397 NCCT cases;
- 345 train/validation and 52 test cases in the published dataset description;
- CT slice thickness commonly around 5 mm, but actual converted geometry varies;
- masks use labels 1, 2, 3, 4, 5;
- labels `{1, 2, 3, 5}` are treated as visible/usable infarct target;
- label 4 is invisible acute infarct and is not included in the current target mask.

## Converted local data state

The full converter was run. It wrote 397 usable case rows and two conversion errors. There are 398 CT files in the processed directory because case `0019983` had already been converted manually before the full conversion.

Processed layout:

```text
D:\Addy project\data\processed\aisd\<case_id>_ct.nii.gz
D:\Addy project\data\processed\aisd\<case_id>_ct.nii.json
D:\Addy project\data\processed\aisd\<case_id>_mask.nii.gz
D:\Addy project\data\processed\aisd\manifest.csv
D:\Addy project\data\processed\aisd\conversion_errors.csv
D:\Addy project\data\processed\aisd\model_manifest.csv
```

Conversion errors:

```text
0073366: CT directory empty / no DICOM series
0226134: mask shape 512x512x26 does not match CT shape 512x512x16
```

Age groups found in the generated manifest:

```text
70_89: 105
50_69: 168
unknown: 71
10_29: 8
30_49: 45
```

`model_manifest.csv` was generated with seed `20260908` and excludes unknown-age and invalid/missing-file cases:

```text
train:      228
validation: 48
test:       50
total:      326
```

The model split is patient-level/case-level and reproducible, but verify no accidental leakage before publishing results.

## Atlas state

The downloaded atlas archive was:

```text
data/atlas/26819290.zip
```

Extracted directory:

```text
data/atlas/downloaded/ASPECTS-281/
```

It contains age-specific 2D atlas images and labels:

```text
BGL_image_10_29.nii.gz
BGL_label_10_29.nii.gz
SGL_image_10_29.nii.gz
SGL_label_10_29.nii.gz
... same for 30_49, 50_69, 70_89
```

Atlas geometry is 2D. Typical size is 500x500 at 0.5x0.5 mm, though other age groups have different pixel sizes. Label semantics confirmed from the authors' code:

```text
BGL labels 1..7: caudate, lentiform, insula, internal capsule, M1, M2, M3
SGL labels 8..10: M4, M5, M6
```

The sample case `0019983` had DICOM age `084Y`, so `70_89` atlas was copied to `data/atlas/` for manual testing. Do not assume every case uses 70_89; batch mode uses `--atlas-dir` and selects by manifest age group.

## Rule-based pipeline behavior

The pipeline:

1. loads CT HU values;
2. estimates a conservative mask using `-20 < HU < 150`;
3. estimates midline from the mask bounds;
4. computes left-right mirror and positive relative density drop;
5. registers BGL and SGL independently using 2D similarity registration;
6. searches separate CT slice bands for BGL and SGL;
7. prevents BGL/SGL from using the same CT slice;
8. selects candidates primarily by overlap with the brain mask;
9. resamples labels with nearest-neighbor interpolation;
10. checks all ten labels and brain overlap;
11. abstains on quality failure;
12. computes regional median HU asymmetry and heatmap fraction;
13. saves JSON, heatmap NIfTI, registered region NIfTI, and overlay PNG.

The current registration threshold checks include all ten labels and atlas/brain overlap >= 0.50. Two cases in the retry remained abstained because overlap was low:

```text
0226304 overlap ~0.433
0073521 overlap ~0.443
```

That abstention is intentional and should not be bypassed casually.

## Existing rule-based results

The first full known-age scoring run produced:

```text
326 total
312 scored
2 abstained
12 errors
```

A retry after robust registration changes recovered 12 cases. Combined usable result was effectively 324 scored and 2 abstained.

Initial evaluation against AISD masks:

```text
324 evaluated
2 abstained
Mean lesion Dice ~0.057
Median lesion Dice ~0.024
Region flag agreement ~73.1%
```

Exploratory tuning on 50 cases found:

```text
best heat threshold: 0.14
mean Dice: ~0.0501 on the tuning sample
```

This threshold selection is exploratory only. The initial manifest had `unassigned` splits when that evaluation was performed, so do not claim this as held-out performance.

## Colab/T4 state

The user created a fresh Colab notebook. The current Colab flow is:

1. Mount Google Drive.
2. Clone latest repo to `/content/icc-code`.
3. Install `.[ml]`.
4. Copy uploaded data from Drive to local `/content/aisd`.
5. Rewrite manifest to absolute local paths as `colab_manifest_local.csv`.
6. Run `aspects-train` with CUDA.

The user confirmed Colab showed:

```text
Tesla T4
15 GB GPU memory
CUDA available
```

Drive data layout used by the user:

```text
/content/drive/MyDrive/addy-project/aisd/
/content/drive/MyDrive/addy-project/ASPECTS-281/
/content/drive/MyDrive/addy-project/src/
/content/drive/MyDrive/addy-project/pyproject.toml
```

The user created `/content/aisd/colab_manifest_local.csv` with 326 valid cases. The original Windows-relative manifest failed because paths like `aisd/0537927_ct.nii.gz` were resolved relative to `/content/icc-code`; the absolute/local manifest fixed this.

## ML trainer state

`src/aspects_stroke/train.py` implements a small 2D U-Net with 3 channels:

```text
channel 0: normalized CT
channel 1: mirrored normalized CT
channel 2: positive mirror-difference map
```

Training features added over time:

- CUDA device selection;
- AMP mixed precision on CUDA;
- configurable `--workers`;
- configurable `--device auto/cuda/cpu`;
- configurable `--size`;
- best validation checkpoint `best_small_unet.pt`;
- final checkpoint `small_unet.pt`;
- `history.json`;
- lazy volume loading;
- bounded two-case per-worker cache;
- slice order changed to `shuffle=False` so grouped slices reuse cache.

The user completed a 2-epoch smoke run and then a full 30-epoch run at `256x256` on a T4. Smoke outputs were confirmed:

```text
best_small_unet.pt
small_unet.pt
history.json
```

Full output path:

```text
/content/drive/MyDrive/addy-project/outputs/t4_baseline_256/
```

The user reported all 30 epochs completed. The next action is to inspect `history.json` and select `best_small_unet.pt` by validation Dice.

Important: training had severe I/O delays. Before fixes, one epoch took roughly 16 minutes. Fixes were pushed:

```text
b39a87e lazy loading
 d56684c worker cache
645a6ee bounded cache
 a4c252e 256x256
9caafe5 grouped slices
```

The latest training run completed, but do not assume performance improved until reading validation history.

## Current exact next step in Colab

Run this in a Python notebook cell:

```python
import json
from pathlib import Path

history_path = Path('/content/drive/MyDrive/addy-project/outputs/t4_baseline_256/history.json')
history = json.loads(history_path.read_text())
best = max(history['history'], key=lambda row: row['validation_dice'])
print('device:', history['device'])
print('amp:', history['amp'])
print('best epoch:', best['epoch'])
print('best train dice:', best['train_dice'])
print('best validation dice:', best['validation_dice'])
```

Then verify checkpoint files:

```python
output = Path('/content/drive/MyDrive/addy-project/outputs/t4_baseline_256')
print(list(output.iterdir()))
```

## Next engineering work after reading history

Priority 1: Build model inference/evaluation on the locked 50-case test split.

The current repository has evaluation for rule-based heatmaps but does not yet have an ML inference command that:

- loads `best_small_unet.pt`;
- applies exactly the same 256x256 preprocessing;
- predicts slice heatmaps for test cases;
- reconstructs a 3D probability map;
- computes test Dice/precision/recall/F1;
- saves prediction NIfTI files and overlays.

Implement this next. Do not use test cases for threshold tuning. Use validation to choose the probability threshold, then evaluate once on test.

Priority 2: Integrate ML probability map into the rule-based ASPECTS scoring contract. The final region flag can combine:

```text
ML probability evidence
+ regional HU asymmetry
+ registration quality
```

Keep region decision logic explainable and preserve abstention.

Priority 3: Add a hybrid evaluation report comparing:

- rule-based detector;
- ML detector;
- hybrid detector.

Report:

- lesion Dice;
- lesion precision, recall, F1;
- per-region sensitivity/specificity/agreement;
- ASPECTS score MAE if expert score is available;
- registration failure rate;
- abstention rate.

Priority 4: APIS external validation after all thresholds and model choices are locked.

Priority 5: clinician-facing viewer with CT, heatmap, ten boundaries, per-region flags, total ASPECTS, registration metadata, and abstention warnings.

## Commands and environment

Local Windows Python used:

```text
C:\Users\lusif\AppData\Local\Programs\Python\Python314\python.exe
```

Local validation commands:

```powershell
C:\Users\lusif\AppData\Local\Programs\Python\Python314\python.exe -m pytest -q
C:\Users\lusif\AppData\Local\Programs\Python\Python314\Scripts\ruff.exe check src tests
```

Colab clone/install:

```python
from google.colab import drive
drive.mount('/content/drive')
!rm -rf /content/icc-code
!git clone https://github.com/Codeaizan/ICC.git /content/icc-code
%cd /content/icc-code
!pip install -e ".[ml]"
!nvidia-smi
```

The user prefers step-by-step instructions: give exactly one next action at a time, wait for the user to reply `finished`, then give the next action. If the user asks a direct question, answer briefly without changing files unless requested.

## Safety and communication constraints

- Never claim clinical validity.
- Never recommend using the score for patient treatment.
- Explain abstentions and quality flags.
- Do not upload patient data to GitHub.
- Do not commit local datasets or model outputs.
- Keep technical and layman explanations available in `HANDOFF.md`.
- When modifying code, run focused tests immediately after the first edit, then lint and full tests before pushing.
- When pushing, mention the commit hash.
