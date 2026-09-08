from __future__ import annotations

import numpy as np


def mirror_volume(volume: np.ndarray, axis: int = 0, midline: float | None = None) -> np.ndarray:
    """Return a left-right mirror, optionally around an estimated midline."""
    if volume.ndim != 3:
        raise ValueError("expected a 3D volume")
    if midline is None:
        return np.flip(volume, axis=axis).copy()
    coordinates = np.arange(volume.shape[axis])
    mirrored_coordinates = np.rint(2.0 * midline - coordinates).astype(int)
    mirrored_coordinates = np.clip(mirrored_coordinates, 0, volume.shape[axis] - 1)
    return np.take(volume, mirrored_coordinates, axis=axis)


def asymmetry_heatmap(ct_hu: np.ndarray, mirrored_ct_hu: np.ndarray) -> np.ndarray:
    """Positive relative density loss, clipped to reduce outlier influence."""
    if ct_hu.shape != mirrored_ct_hu.shape:
        raise ValueError("CT and mirrored CT must have identical shapes")
    denominator = np.maximum(np.abs(mirrored_ct_hu), 1.0)
    return np.clip((mirrored_ct_hu - ct_hu) / denominator, 0.0, 1.0)
