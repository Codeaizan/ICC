# Project Handoff

## Plain-language explanation

This project is a research prototype that estimates the ASPECTS score from a non-contrast head CT. ASPECTS is a 10-point stroke score. A healthy region keeps its point; a region suspected to contain early ischemic change loses a point.

The system does the following:

1. Reads CT scans while preserving their original density values.
2. Finds a conservative brain mask and estimates the brain midline.
3. Compares one side of the brain with its mirrored opposite side.
4. Aligns age-specific ASPECTS maps to two important CT levels.
5. Checks whether the alignment is trustworthy.
6. Produces a heatmap, ten region decisions, an overall score, and an overlay image.
7. Abstains instead of returning a score when the input or alignment is unsafe.

The current rule-based detector is useful for demonstrating the complete workflow, but its measured lesion Dice is low. It should not be used for patient care or presented as a clinically validated tool.

## Technical explanation

### Data and preprocessing

- AISD DICOM CT series are converted to HU-preserving NIfTI with SimpleITK.
- AISD PNG masks are converted to geometry-matched NIfTI masks.
- AISD mask labels `{1, 2, 3, 5}` are treated as visible/usable infarct target labels.
- Unknown-age and malformed cases are excluded from the reproducible model split.
- The split contains 228 training, 48 validation, and 50 test cases with seed `20260908`.

### Registration and scoring

- The downloaded NCCT atlas has two 2D levels: BGL labels `1..7` and SGL labels `8..10`.
- Each level is registered independently to an axial CT slice with SimpleITK similarity registration.
- Label maps use nearest-neighbor resampling.
- Candidate slice selection prioritizes atlas overlap with the detected brain mask.
- Registration quality checks require all ten labels and sufficient brain overlap.
- The scorer uses regional median HU asymmetry plus heatmap fraction and remains rule-based.

### ML baseline

`aspects-train` trains a small 2D U-Net with three channels:

1. normalized CT;
2. mirrored CT;
3. positive mirror-difference map.

The trainer supports CUDA, T4 mixed precision, multiple data-loader workers, validation-best checkpointing, and JSON history. Colab instructions are in [COLAB.md](COLAB.md).

A 30-epoch run on a T4 at 256x256 completed but the model collapsed after epoch 1 (train/validation Dice flatlined from epoch 2 onward). The best checkpoint (epoch 1) achieves validation Dice `0.572` using training-time smoothed Dice. The optimal probability threshold on validation was `0.07`.

### ML inference and evaluation

`aspects-infer` loads the trained checkpoint, predicts per-slice probability maps, reconstructs 3D probability volumes, and evaluates against ground-truth masks. Threshold selection uses validation; test evaluation uses the locked threshold.

### Hybrid scoring

`score_regions` accepts an optional `ml_prob` volume alongside the existing rule-based features. A region is flagged as affected if either:

- the original rule-based criteria are met (HU drop ≥ threshold AND heatmap fraction ≥ threshold); or
- the ML lesion fraction exceeds `ml_fraction_threshold` AND there is a positive HU drop (`relative_drop > 0`).

The `evidence` field records which signal triggered the decision: `"rule_based"`, `"ml_assisted"`, `"both"`, or `"none"`. This keeps scoring fully explainable.

### Evaluation status

Rule-based evaluation (324 scored, 2 abstentions): mean lesion Dice `~0.057`, region agreement `~73.1%`.

Held-out test evaluation (50 cases, threshold selected on validation):

| Approach | Dice | Precision | Recall | F1 |
|----------|------|-----------|--------|-----|
| Rule-based | 0.039 | 0.022 | 0.553 | 0.039 |
| ML-only | 0.046 | 0.027 | 0.445 | 0.046 |
| Hybrid | 0.040 | 0.022 | 0.586 | 0.040 |

The hybrid improves recall by 3.3 percentage points over the rule-based approach without degrading precision. All voxel-level Dice values remain low due to high false-positive rates; region-level scoring with atlas registration provides more useful clinical granularity.

### How a friend reproduces the work

1. Clone this repository.
2. Install `.[dev]` for the rule-based pipeline or `.[ml]` in Colab for training.
3. Obtain AISD and the atlas separately under their usage terms.
4. Convert the data using the commands in [README.md](README.md).
5. Create `model_manifest.csv` with `aspects-split`.
6. Run the five-case smoke test before a full batch.
7. Inspect overlays and quality flags.
8. Train the ML baseline in Colab using [COLAB.md](COLAB.md).
9. Run `aspects-infer --sweep-threshold` on validation to find the optimal threshold.
10. Run `aspects-infer --threshold <value>` on test for held-out evaluation.
11. Run `aspects-compare` for a three-way detector comparison.

## Remaining work

- Improve ML training: address model collapse, add data augmentation, class weighting, or a deeper architecture.
- Improve skull stripping, midline estimation, and 2D/3D registration.
- Investigate missing DICOM case `0073366` and CT/mask mismatch case `0226134`.
- Validate externally on APIS after model and thresholds are locked.
- Build a clinician-facing viewer and complete clinical/regulatory validation.