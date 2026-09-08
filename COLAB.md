# Colab T4 training

Use Colab for the ML stage only. Do not upload the raw DICOM archives. Put the converted project data and source tree in Google Drive:

```text
MyDrive/addy-project/
  src/
  pyproject.toml
  data/processed/aisd/
  data/atlas/downloaded/ASPECTS-281/
```

In Colab, select Runtime > Change runtime type > T4 GPU, then run:

```python
from google.colab import drive
drive.mount('/content/drive')
```

```python
%cd /content/drive/MyDrive/addy-project
!pip install -e ".[ml]"
!nvidia-smi
```

Start with a five-case smoke training run:

```python
!aspects-train \
  --manifest data/processed/aisd/model_manifest.csv \
  --output outputs/t4_smoke \
  --epochs 2 \
  --max-cases 5 \
  --batch-size 8 \
  --workers 2 \
  --size 256 \
  --device cuda
```

Then train the full baseline:

```python
!aspects-train \
  --manifest data/processed/aisd/model_manifest.csv \
  --output outputs/t4_baseline \
  --epochs 30 \
  --batch-size 8 \
  --workers 2 \
  --size 256 \
  --device cuda
```

Outputs:

- `best_small_unet.pt`: checkpoint with best validation Dice
- `small_unet.pt`: final checkpoint
- `history.json`: device, AMP, and epoch metrics

Use the validation curve to choose epochs and thresholds. Do not evaluate on the test split during training. The current trainer is a baseline and does not yet export ML heatmaps into the ASPECTS scoring pipeline.
