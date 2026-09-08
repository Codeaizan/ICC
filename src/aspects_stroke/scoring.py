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
    ml_lesion_fraction: float = 0.0
    evidence: str = "rule_based"


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
    ml_prob: np.ndarray | None = None,
    ml_fraction_threshold: float = 0.10,
    ml_prob_threshold: float = 0.07,
) -> AspectsResult:
    """Score registered labels using explainable HU asymmetry and heatmap evidence.

    All arrays must share the same voxel grid. The mirror image must already be
    aligned to the native image's midline; registration quality is checked upstream.

    When *ml_prob* is provided, a region can additionally be flagged as affected
    if the ML-predicted lesion fraction exceeds *ml_fraction_threshold* **and**
    there is a positive HU drop (relative_drop > 0). This prevents the noisy ML
    signal from creating false positives in regions with zero density evidence.

    The *evidence* field records which signal triggered the decision:
    ``"rule_based"``, ``"ml_assisted"``, ``"both"``, or ``"none"``.
    """
    arrays = [atlas_labels, ct_hu, mirrored_ct_hu, lesion_heatmap]
    if ml_prob is not None:
        arrays.append(ml_prob)
    shapes = {a.shape for a in arrays}
    if len(shapes) != 1:
        raise ValueError("atlas, CT, mirrored CT, heatmap, and ml_prob (if given) must have identical shapes")

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

        # Rule-based decision (unchanged from original)
        rule_affected = relative_drop >= drop_threshold and lesion_fraction >= lesion_fraction_threshold

        # ML-assisted decision (only when ml_prob is provided)
        ml_fraction = 0.0
        ml_affected = False
        if ml_prob is not None:
            ml_fraction = float(np.mean(ml_prob[region] > ml_prob_threshold))
            # Require at least some HU drop to avoid pure-ML false positives
            ml_affected = ml_fraction >= ml_fraction_threshold and relative_drop > 0

        # Combined decision and evidence tracking
        affected = rule_affected or ml_affected
        if rule_affected and ml_affected:
            evidence = "both"
        elif rule_affected:
            evidence = "rule_based"
        elif ml_affected:
            evidence = "ml_assisted"
        else:
            evidence = "none"

        decisions.append(RegionDecision(
            label, name, affected, lesion_fraction, median_hu,
            opposite_median, relative_drop, ml_fraction, evidence,
        ))

    return AspectsResult(score=10 - sum(item.affected for item in decisions), regions=tuple(decisions))


def result_to_dict(result: AspectsResult) -> Mapping[str, object]:
    return {
        "aspects": result.score,
        "regions": [item.__dict__ for item in result.regions],
    }
