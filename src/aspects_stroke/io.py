from __future__ import annotations

from pathlib import Path

import nibabel as nib
import numpy as np


def load_nifti(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    image = nib.load(str(path))
    data = np.asarray(image.get_fdata(dtype=np.float32))
    if data.ndim != 3:
        raise ValueError(f"expected a 3D NIfTI volume, got shape {data.shape}")
    return data, image.affine


def save_nifti(data: np.ndarray, affine: np.ndarray, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(data.astype(np.float32), affine), str(output))
