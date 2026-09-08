import numpy as np

from aspects_stroke.preprocess import preprocess_ct
from aspects_stroke.registration import assess_registration_quality
from aspects_stroke.scoring import score_regions
from aspects_stroke.symmetry import asymmetry_heatmap, mirror_volume


def test_mirror_and_heatmap_detect_one_side_drop():
    ct = np.full((4, 4, 2), 50.0, dtype=np.float32)
    ct[0, 0, 0] = 40.0
    mirrored = mirror_volume(ct)
    heatmap = asymmetry_heatmap(ct, mirrored)

    assert mirrored[3, 0, 0] == 40.0
    assert heatmap[0, 0, 0] > 0.0
    assert heatmap[3, 0, 0] == 0.0


def test_score_flags_region_from_density_drop_and_heatmap():
    shape = (4, 4, 2)
    ct = np.full(shape, 50.0, dtype=np.float32)
    mirrored = np.full(shape, 50.0, dtype=np.float32)
    labels = np.zeros(shape, dtype=np.float32)
    heatmap = np.zeros(shape, dtype=np.float32)

    for label in range(1, 11):
        labels.flat[label - 1] = label
    ct.flat[0] = 45.0
    mirrored.flat[0] = 50.0
    heatmap.flat[0] = 0.2

    result = score_regions(labels, ct, mirrored, heatmap)

    assert result.score == 9
    assert result.regions[0].affected is True
    assert result.regions[1].affected is False


def test_preprocessing_estimates_shifted_midline():
    ct = np.full((8, 4, 2), -100.0, dtype=np.float32)
    ct[2:7, 1:3, :] = 50.0

    result = preprocess_ct(ct)

    assert result.midline_x == 4.0
    assert result.mask_fraction > 0.0
    assert result.quality_flags == ()


def test_preprocessing_rejects_empty_mask():
    ct = np.full((8, 4, 2), -100.0, dtype=np.float32)

    try:
        preprocess_ct(ct)
    except ValueError as error:
        assert "empty brain mask" in str(error)
    else:
        raise AssertionError("empty brain mask should fail preprocessing")


def test_registration_quality_rejects_missing_region():
    labels = np.zeros((4, 4, 2), dtype=np.uint16)
    brain_mask = np.ones_like(labels, dtype=bool)
    for label in range(1, 10):
        labels.flat[label - 1] = label

    quality = assess_registration_quality(labels, brain_mask)

    assert quality.passed is False
    assert "missing_aspects_region" in quality.flags


def test_registration_quality_accepts_complete_in_brain_labels():
    labels = np.zeros((4, 4, 3), dtype=np.uint16)
    brain_mask = np.ones_like(labels, dtype=bool)
    for label in range(1, 11):
        labels.flat[label - 1] = label

    quality = assess_registration_quality(labels, brain_mask)

    assert quality.passed is True
    assert quality.regions_present == 10


def test_hybrid_ml_can_flag_region_with_some_hu_drop():
    """ML evidence alone flags a region when there is at least some HU drop."""
    shape = (4, 4, 2)
    ct = np.full(shape, 50.0, dtype=np.float32)
    mirrored = np.full(shape, 50.0, dtype=np.float32)
    labels = np.zeros(shape, dtype=np.float32)
    heatmap = np.zeros(shape, dtype=np.float32)
    ml_prob = np.zeros(shape, dtype=np.float32)

    for label in range(1, 11):
        labels.flat[label - 1] = label

    # Region 1: small HU drop (below rule threshold) but ML fires
    ct.flat[0] = 49.0
    mirrored.flat[0] = 50.0
    ml_prob.flat[0] = 0.9  # ML confident

    result = score_regions(labels, ct, mirrored, heatmap, ml_prob=ml_prob, ml_fraction_threshold=0.10)

    assert result.regions[0].affected is True
    assert result.regions[0].evidence == "ml_assisted"
    assert result.regions[1].affected is False


def test_hybrid_ml_does_not_flag_without_hu_drop():
    """ML alone cannot flag a region when there is zero HU drop."""
    shape = (4, 4, 2)
    ct = np.full(shape, 50.0, dtype=np.float32)
    mirrored = np.full(shape, 50.0, dtype=np.float32)
    labels = np.zeros(shape, dtype=np.float32)
    heatmap = np.zeros(shape, dtype=np.float32)
    ml_prob = np.zeros(shape, dtype=np.float32)

    for label in range(1, 11):
        labels.flat[label - 1] = label

    # Region 1: ML fires but no HU drop at all
    ml_prob.flat[0] = 0.9

    result = score_regions(labels, ct, mirrored, heatmap, ml_prob=ml_prob, ml_fraction_threshold=0.10)

    assert result.regions[0].affected is False
    assert result.regions[0].evidence == "none"


def test_scoring_without_ml_prob_is_backward_compatible():
    """When ml_prob is None, behaviour is identical to the original."""
    shape = (4, 4, 2)
    ct = np.full(shape, 50.0, dtype=np.float32)
    mirrored = np.full(shape, 50.0, dtype=np.float32)
    labels = np.zeros(shape, dtype=np.float32)
    heatmap = np.zeros(shape, dtype=np.float32)

    for label in range(1, 11):
        labels.flat[label - 1] = label

    result = score_regions(labels, ct, mirrored, heatmap)

    assert result.score == 10
    for region in result.regions:
        assert region.ml_lesion_fraction == 0.0
        assert region.evidence == "none"

