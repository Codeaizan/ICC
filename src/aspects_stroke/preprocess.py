from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PreprocessResult:
    ct_hu: np.ndarray
    brain_mask: np.ndarray
    midline_x: float
    mask_fraction: float
    quality_flags: tuple[str, ...]


def estimate_brain_mask(ct_hu: np.ndarray) -> np.ndarray:
    """Create a conservative brain-tissue mask from calibrated HU values.

    This is a prototype mask, not a skull-stripper. It intentionally favors
    abstention and must be replaced or benchmarked against a clinical tool.
    """
    if ct_hu.ndim != 3:
        raise ValueError("expected a 3D CT volume")
    finite = np.isfinite(ct_hu)
    return finite & (ct_hu > -20.0) & (ct_hu < 150.0)


def estimate_midline_x(brain_mask: np.ndarray) -> float:
    coordinates = np.argwhere(brain_mask)
    if coordinates.size == 0:
        raise ValueError("cannot estimate a midline from an empty brain mask")
    return float((coordinates[:, 0].min() + coordinates[:, 0].max()) / 2.0)


def preprocess_ct(ct_hu: np.ndarray) -> PreprocessResult:
    mask = estimate_brain_mask(ct_hu)
    midline_x = estimate_midline_x(mask)
    mask_fraction = float(np.mean(mask))
    flags: list[str] = []
    if mask_fraction < 0.01:
        flags.append("low_brain_mask_coverage")
    if mask_fraction > 0.8:
        flags.append("unusually_large_brain_mask")
    if mask.shape[0] < 4:
        flags.append("insufficient_left_right_resolution")
    return PreprocessResult(ct_hu, mask, midline_x, mask_fraction, tuple(flags))


def preprocess_to_dict(result: PreprocessResult) -> dict[str, object]:
    return {
        "midline_x": result.midline_x,
        "brain_mask_fraction": result.mask_fraction,
        "quality_flags": list(result.quality_flags),
    }