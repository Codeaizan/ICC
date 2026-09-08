import numpy as np

from aspects_stroke.compare import compare_case


def _make_volumes(shape=(8, 8, 2)):
    """Create minimal CT, mask, and write helpers."""
    ct = np.full(shape, 50.0, dtype=np.float32)
    # Place some brain tissue (HU in [-20, 150])
    ct[2:6, 2:6, :] = 40.0
    mask = np.zeros(shape, dtype=np.float32)
    return ct, mask


def test_compare_case_returns_all_three_approaches(tmp_path):
    import nibabel as nib

    ct, mask = _make_volumes()
    # Put a small lesion on the left side
    mask[2, 3, 0] = 1.0  # label 1 = infarct
    ct[2, 3, 0] = 20.0   # drop HU to simulate ischemia

    ct_path = tmp_path / "ct.nii.gz"
    mask_path = tmp_path / "mask.nii.gz"
    ml_path = tmp_path / "ml_prob.nii.gz"

    affine = np.eye(4)
    nib.save(nib.Nifti1Image(ct, affine), str(ct_path))
    nib.save(nib.Nifti1Image(mask, affine), str(mask_path))

    ml_prob = np.zeros_like(ct)
    ml_prob[2, 3, 0] = 0.8
    nib.save(nib.Nifti1Image(ml_prob, affine), str(ml_path))

    result = compare_case(ct_path, mask_path, ml_path)

    assert result["status"] == "evaluated"
    assert "dice" in result["rule_based"]
    assert "dice" in result["ml"]
    assert "dice" in result["hybrid"]


def test_compare_case_works_without_ml(tmp_path):
    import nibabel as nib

    ct, mask = _make_volumes()
    ct_path = tmp_path / "ct.nii.gz"
    mask_path = tmp_path / "mask.nii.gz"

    nib.save(nib.Nifti1Image(ct, np.eye(4)), str(ct_path))
    nib.save(nib.Nifti1Image(mask, np.eye(4)), str(mask_path))

    result = compare_case(ct_path, mask_path, None)

    assert result["status"] == "evaluated"
    assert "dice" in result["rule_based"]
    assert result["ml"]["status"] == "missing_prediction"
