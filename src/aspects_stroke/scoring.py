from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

REGION_NAMES: dict[int, str] = {
    1: "caudate",
    2: "lentiform",
    3: "insula",
    4: "internal_capsule",
    5: "M1",
    6: "M2",
    7: "M3",
    8: "M4",
    9: "M5",
    10: "M6",
}


@dataclass(frozen=True)
class RegionDecision:
    label: int
    name: str
    affected: bool
    lesion_fraction: float
    median_hu: float
    contralateral_median_hu: float
    relative_drop: float


@dataclass(frozen=True)
class AspectsResult:
    score: int
    regions: tuple[RegionDecision, ...]


def score_regions(
    atlas_labels: np.ndarray,
    ct_hu: np.ndarray,
    mirrored_ct_hu: np.ndarray,
    lesion_heatmap: np.ndarray,
    *,
    drop_threshold: float = 0.08,
    lesion_fraction_threshold: float = 0.05,
) -> AspectsResult:
    """Score registered labels using explainable HU asymmetry and heatmap evidence.

    All arrays must share the same voxel grid. The mirror image must already be
    aligned to the native image's midline; registration quality is checked upstream.
    """
    if not (atlas_labels.shape == ct_hu.shape == mirrored_ct_hu.shape == lesion_heatmap.shape):
        raise ValueError("atlas, CT, mirrored CT, and heatmap must have identical shapes")

    decisions: list[RegionDecision] = []
    for label, name in REGION_NAMES.items():
        region = atlas_labels == label
        if not np.any(region):
            raise ValueError(f"atlas region {label} ({name}) is missing")
        values = ct_hu[region]
        opposite = mirrored_ct_hu[region]
        median_hu = float(np.median(values))
        opposite_median = float(np.median(opposite))
        relative_drop = float((opposite_median - median_hu) / max(abs(opposite_median), 1.0))
        lesion_fraction = float(np.mean(lesion_heatmap[region] > 0))
        affected = relative_drop >= drop_threshold and lesion_fraction >= lesion_fraction_threshold
        decisions.append(RegionDecision(label, name, affected, lesion_fraction, median_hu, opposite_median, relative_drop))

    return AspectsResult(score=10 - sum(item.affected for item in decisions), regions=tuple(decisions))


def result_to_dict(result: AspectsResult) -> Mapping[str, object]:
    return {
        "aspects": result.score,
        "regions": [item.__dict__ for item in result.regions],
    }
