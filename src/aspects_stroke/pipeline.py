from __future__ import annotations

import json
from pathlib import Path

import SimpleITK as sitk

from .io import load_nifti, save_nifti
from .preprocess import preprocess_ct, preprocess_to_dict
from .registration import (
    assess_registration_quality,
    quality_to_dict,
    register_atlas_labels,
    register_two_level_atlas,
    transform_to_dict,
)
from .scoring import result_to_dict, score_regions
from .symmetry import asymmetry_heatmap, mirror_volume
from .visualize import save_overlay


def run_case(
    ct_path: str | Path,
    atlas_labels_path: str | Path,
    output_path: str | Path,
    atlas_image_path: str | Path | None = None,
    bgl_image_path: str | Path | None = None,
    bgl_labels_path: str | Path | None = None,
    sgl_image_path: str | Path | None = None,
    sgl_labels_path: str | Path | None = None,
    *,
    drop_threshold: float = 0.08,
    lesion_fraction_threshold: float = 0.05,
) -> dict[str, object]:
    ct, affine = load_nifti(ct_path)
    output = Path(output_path)
    output.mkdir(parents=True, exist_ok=True)
    try:
        preprocessing = preprocess_ct(ct)
    except ValueError as error:
        report = {"status": "abstain", "aspects": None, "reason": "preprocessing_failed", "error": str(error)}
        (output / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
    base_report: dict[str, object] = {"preprocessing": preprocess_to_dict(preprocessing)}

    try:
        if all((bgl_image_path, bgl_labels_path, sgl_image_path, sgl_labels_path)):
            spacing = (float(abs(affine[0, 0])), float(abs(affine[1, 1])))
            two_level = register_two_level_atlas(
                ct,
                spacing,
                {
                    "BGL": (bgl_image_path, bgl_labels_path),
                    "SGL": (sgl_image_path, sgl_labels_path),
                },
            )
            atlas = two_level.labels
            transform = None
            registration_metadata = {"mode": "two_level_2d", "levels": two_level.levels}
        elif atlas_image_path:
            registration = register_atlas_labels(ct_path, atlas_image_path, atlas_labels_path)
            atlas = sitk.GetArrayFromImage(registration.labels).transpose(2, 1, 0)
            transform = registration.transform
            registration_metadata = transform_to_dict(registration)
        elif not any((bgl_image_path, bgl_labels_path, sgl_image_path, sgl_labels_path)):
            atlas, atlas_affine = load_nifti(atlas_labels_path)
            if not (abs(affine - atlas_affine) < 1e-3).all():
                raise ValueError("CT and atlas affine matrices differ; register/resample atlas before scoring")
            transform = None
            registration_metadata = {"mode": "pre_registered"}
        else:
            raise ValueError("provide either 3D atlas files or all four BGL/SGL atlas files")
    except (OSError, RuntimeError, ValueError) as error:
        report = {**base_report, "status": "abstain", "aspects": None, "reason": "registration_failed", "error": str(error)}
        (output / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    if ct.shape != atlas.shape:
        raise ValueError("registered atlas labels must match the CT grid")
    quality = assess_registration_quality(atlas, preprocessing.brain_mask, transform)
    report = {**base_report, "registration": {**registration_metadata, **quality_to_dict(quality)}}
    if preprocessing.quality_flags or not quality.passed:
        report.update({"status": "abstain", "aspects": None, "reason": "quality_checks_failed"})
        (output / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    mirrored = mirror_volume(ct, midline=preprocessing.midline_x)
    heatmap = asymmetry_heatmap(ct, mirrored) * preprocessing.brain_mask
    result = score_regions(
        atlas,
        ct,
        mirrored,
        heatmap,
        drop_threshold=drop_threshold,
        lesion_fraction_threshold=lesion_fraction_threshold,
    )
    save_nifti(heatmap, affine, output / "ischemia_heatmap.nii.gz")
    save_nifti(atlas, affine, output / "registered_regions.nii.gz")
    save_overlay(ct, heatmap, atlas, result, output / "overlay.png")
    report.update({"status": "scored", **result_to_dict(result)})
    (output / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report