# ASPECTS Stroke Automated Scoring: Project Summary

This document summarizes the work completed during the recent development sessions, provides a comprehensive guide on how to install dependencies and run the project, and outlines the system architecture.

## 1. What We Did

During the development sprint, we expanded the baseline rule-based ASPECTS scoring pipeline into a hybrid system incorporating Machine Learning, and built a clinician-facing offline viewer.

### A. Machine Learning Inference & Evaluation
- **ML Inference Module (`aspects-infer`)**: Built a complete inference pipeline that loads a trained 2D U-Net checkpoint, predicts slice-by-slice probability maps, reconstructs 3D probability volumes, and evaluates them against ground-truth masks.
- **Validation Threshold Sweep**: Implemented threshold sweeping to find the optimal ML probability cutoff. Evaluated thresholds from 0.01 to 0.90, locking in **0.07** as the optimal threshold based on validation data.
- **Test Evaluation**: Evaluated the ML model on a 50-case held-out test split. The model demonstrated useful recall (44.5%) but low precision (2.7%) due to the high class imbalance and dataset size limitations.

### B. Hybrid Scoring Integration
- **Hybrid Detector (`scoring.py`)**: Integrated the ML probability maps into the region scoring logic. A region is now flagged as affected if it meets the original rule-based criteria (HU drop & symmetry heatmap) **OR** if the ML lesion fraction is sufficiently high alongside a positive HU drop.
- **Explainability**: Added an `evidence` tracking field (`rule_based`, `ml_assisted`, `both`, `none`) to ensure the hybrid system remains fully explainable.
- **Three-Way Comparison (`aspects-compare`)**: Created a tool to evaluate and compare the rule-based, ML-only, and Hybrid detectors side-by-side on the same cases. The Hybrid approach successfully boosted recall by 3.3% without degrading precision.

### C. Clinician-Facing Viewer
- **Offline Web App (`aspects-viewer`)**: Built a fully offline, premium, dark-mode clinician viewer to explore the outputs (CT, heatmaps, Region flags, total ASPECTS score, and metadata).
- **Architecture**: It uses a lightweight Python backend (`http.server`) to serve local JSON reports and NIfTI/PNG files to a vanilla HTML/JS/CSS frontend. It uses local system fonts and makes zero external network requests.

---

## 2. Dependencies & Installation

The project uses Python 3.10+ and manages dependencies via `pyproject.toml`. 

**Core Dependencies:**
- `numpy`, `scipy` (Math and arrays)
- `SimpleITK`, `nibabel` (Medical image processing and registration)
- `Pillow`, `matplotlib` (Image overlay generation)

**ML Dependencies (Optional):**
- `torch`, `torchvision`, `monai` (Deep learning)

**Dev Dependencies:**
- `pytest`, `ruff` (Testing and linting)

### Setup Instructions

1. Clone the repository and navigate to the root directory.
2. Create and activate a Python virtual environment:
   ```powershell
   # Windows PowerShell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   *(Note: The `.venv` folder is excluded from GitHub via `.gitignore` to prevent committing dependencies).*
3. Upgrade pip and install the project:
   ```powershell
   python -m pip install --upgrade pip
   
   # Install for Rule-based usage and UI viewing
   python -m pip install -e ".[dev]"
   
   # Install with ML dependencies (if training/inferring)
   python -m pip install -e ".[dev,ml]"
   ```

---

## 3. How to Run the Project

### A. Data Preparation
- Place CT scans (`.nii.gz`) inside `data/raw/aisd/`.
- Place downloaded age-specific atlas files in `data/atlas/`.
- Generate a dataset manifest using `aspects-split` to assign reproducible train/validation/test splits.

### B. Rule-Based Scoring Pipeline
To score a single case, run:
```powershell
aspects-score `
  --ct data/processed/aisd/example_ct.nii.gz `
  --bgl-image data/atlas/BGL_image_70_89.nii.gz `
  --bgl-labels data/atlas/BGL_label_70_89.nii.gz `
  --sgl-image data/atlas/SGL_image_70_89.nii.gz `
  --sgl-labels data/atlas/SGL_label_70_89.nii.gz `
  --output outputs/example_case
```

To run a batch of cases:
```powershell
aspects-batch `
  --manifest data/processed/aisd/manifest.csv `
  --atlas-dir data/atlas/downloaded/ASPECTS-281 `
  --output outputs/aisd `
  --workers 6
```

### C. Machine Learning Pipeline
1. **Train**: `aspects-train` (Requires a GPU, usually run in Google Colab).
2. **Infer**: Generate probability volumes and evaluate against ground truth.
   ```powershell
   aspects-infer --manifest data/manifest.csv --split test --model best_model.pt --output outputs/predictions
   ```
3. **Compare**: Compare the three detection approaches:
   ```powershell
   aspects-compare --manifest data/manifest.csv --split test --ml-predictions outputs/predictions --report outputs/comparison.json
   ```

### D. Clinician-Facing Viewer
To view the generated output folders, start the offline local server:
```powershell
aspects-viewer --output outputs/aisd --port 8000
```
Open `http://localhost:8000` in your web browser. You can click through cases to see the generated overlay, the calculated score, regional breakdown, and registration metadata. Abstained cases will prominently display a warning banner.
