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
