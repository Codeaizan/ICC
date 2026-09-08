import numpy as np

from aspects_stroke.evaluate import dice_score


def test_dice_score_handles_overlap_and_empty_masks():
    assert dice_score(np.array([1, 0, 1]), np.array([1, 1, 0])) == 0.5
    assert dice_score(np.zeros(3), np.zeros(3)) == 1.0