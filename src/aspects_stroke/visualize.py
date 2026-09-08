from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .scoring import AspectsResult


def save_overlay(
    ct_hu: np.ndarray,
    heatmap: np.ndarray,
    atlas_labels: np.ndarray,
    result: AspectsResult,
    output_path: str | Path,
) -> None:
    """Save axial mid-volume views with heatmap and ASPECTS region boundaries."""
    if not (ct_hu.shape == heatmap.shape == atlas_labels.shape):
        raise ValueError("CT, heatmap, and labels must have identical shapes")
    registered_slices = np.flatnonzero(np.any(atlas_labels > 0, axis=(0, 1)))
    slice_indices = registered_slices.tolist() or [ct_hu.shape[2] // 2]
    figure, axes_array = plt.subplots(len(slice_indices), 2, figsize=(12, 6 * len(slice_indices)), squeeze=False)
    for row, slice_index in enumerate(slice_indices):
        ct_slice = ct_hu[:, :, slice_index].T
        heat_slice = heatmap[:, :, slice_index].T
        labels_slice = atlas_labels[:, :, slice_index].T
        axes = axes_array[row]
        axes[0].imshow(ct_slice, cmap="gray", vmin=0, vmax=80)
        axes[0].set_title(f"NCCT | slice {slice_index} | ASPECTS {result.score}")
        axes[1].imshow(ct_slice, cmap="gray", vmin=0, vmax=80)
        axes[1].imshow(np.ma.masked_where(heat_slice < 0.08, heat_slice), cmap="Reds", alpha=0.45, vmin=0, vmax=1)
        axes[1].contour(labels_slice, levels=np.arange(0.5, 10.5, 1), colors="cyan", linewidths=0.7)
        axes[1].set_title("Heatmap and ASPECTS regions")
        for axis in axes:
            axis.axis("off")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160)
    plt.close(figure)