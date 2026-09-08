import numpy as np

from aspects_stroke.infer import _compute_metrics


def test_compute_metrics_perfect_overlap():
    pred = np.array([1, 1, 0, 0], dtype=np.float32)
    tgt = np.array([1, 1, 0, 0], dtype=np.float32)
    m = _compute_metrics(pred, tgt)
    assert m["dice"] == 1.0
    assert m["precision"] == 1.0
    assert m["recall"] == 1.0
    assert m["f1"] == 1.0


def test_compute_metrics_no_overlap():
    pred = np.array([1, 1, 0, 0], dtype=np.float32)
    tgt = np.array([0, 0, 1, 1], dtype=np.float32)
    m = _compute_metrics(pred, tgt)
    assert m["dice"] == 0.0
    assert m["precision"] == 0.0
    assert m["recall"] == 0.0


def test_compute_metrics_empty():
    pred = np.zeros(4, dtype=np.float32)
    tgt = np.zeros(4, dtype=np.float32)
    m = _compute_metrics(pred, tgt)
    assert m["dice"] == 1.0


def test_compute_metrics_partial():
    pred = np.array([1, 0, 1, 0], dtype=np.float32)
    tgt = np.array([1, 1, 0, 0], dtype=np.float32)
    m = _compute_metrics(pred, tgt)
    assert m["dice"] == 0.5
    assert m["precision"] == 0.5
    assert m["recall"] == 0.5
