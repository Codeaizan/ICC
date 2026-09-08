from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import SimpleITK as sitk


@dataclass(frozen=True)
class RegistrationResult:
    labels: sitk.Image
    transform: sitk.Transform
    metric_value: float
    iterations: int


@dataclass(frozen=True)
class RegistrationQuality:
    passed: bool
    regions_present: int
    atlas_brain_overlap: float
    translation_mm: float | None
    rotation_degrees: float | None
    flags: tuple[str, ...]


@dataclass(frozen=True)
class TwoLevelRegistrationResult:
    labels: np.ndarray
    levels: dict[str, dict[str, object]]


def register_atlas_labels(
    ct_path: str | Path,
    atlas_image_path: str | Path,
    atlas_labels_path: str | Path,
) -> RegistrationResult:
    """Affine-register an atlas image to CT and resample labels safely.

    The atlas intensity image and label image must share geometry. Labels use
    nearest-neighbor interpolation so region ids cannot be blended.
    """
    ct = sitk.ReadImage(str(ct_path), sitk.sitkFloat32)
    atlas = sitk.ReadImage(str(atlas_image_path), sitk.sitkFloat32)
    labels = sitk.ReadImage(str(atlas_labels_path), sitk.sitkUInt16)
    if atlas.GetSize() != labels.GetSize() or atlas.GetSpacing() != labels.GetSpacing():
        raise ValueError("atlas intensity and labels must have identical geometry")

    initial = sitk.CenteredTransformInitializer(
        ct,
        atlas,
        sitk.AffineTransform(3),
        sitk.CenteredTransformInitializerFilter.GEOMETRY,
    )
    registration = sitk.ImageRegistrationMethod()
    registration.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
    registration.SetMetricSamplingStrategy(registration.RANDOM)
    registration.SetMetricSamplingPercentage(0.2, seed=17)
    registration.SetInterpolator(sitk.sitkLinear)
    registration.SetOptimizerAsRegularStepGradientDescent(
        learningRate=2.0,
        minStep=1e-4,
        numberOfIterations=100,
        relaxationFactor=0.5,
    )
    registration.SetOptimizerScalesFromPhysicalShift()
    registration.SetInitialTransform(initial, inPlace=False)
    transform = registration.Execute(ct, atlas)
    registered_labels = sitk.Resample(
        labels,
        ct,
        transform,
        sitk.sitkNearestNeighbor,
        0,
        sitk.sitkUInt16,
    )
    return RegistrationResult(
        labels=registered_labels,
        transform=transform,
        metric_value=float(registration.GetMetricValue()),
        iterations=registration.GetOptimizerIteration(),
    )


def transform_to_dict(result: RegistrationResult) -> dict[str, object]:
    return {
        "metric_value": result.metric_value,
        "optimizer_iterations": result.iterations,
        "transform": result.transform.GetParameters(),
        "fixed_parameters": result.transform.GetFixedParameters(),
    }


def assess_registration_quality(
    labels: np.ndarray,
    brain_mask: np.ndarray,
    transform: sitk.Transform | None = None,
    *,
    minimum_overlap: float = 0.50,
    maximum_translation_mm: float = 30.0,
    maximum_rotation_degrees: float = 20.0,
) -> RegistrationQuality:
    """Check whether registered labels are safe to use for regional scoring."""
    if labels.shape != brain_mask.shape:
        raise ValueError("labels and brain mask must have identical shapes")
    flags: list[str] = []
    present = int(sum(np.any(labels == label) for label in range(1, 11)))
    if present != 10:
        flags.append("missing_aspects_region")
    atlas_voxels = labels > 0
    overlap = float(np.mean(brain_mask[atlas_voxels])) if np.any(atlas_voxels) else 0.0
    if overlap < minimum_overlap:
        flags.append("low_atlas_brain_overlap")

    translation_mm: float | None = None
    rotation_degrees: float | None = None
    if transform is not None:
        parameters = np.asarray(transform.GetParameters(), dtype=float)
        if parameters.size >= 12:
            translation_mm = float(np.linalg.norm(parameters[9:12]))
            matrix = parameters[:9].reshape(3, 3)
            cosine = np.clip((np.trace(matrix) - 1.0) / 2.0, -1.0, 1.0)
            rotation_degrees = float(np.degrees(np.arccos(cosine)))
            if translation_mm > maximum_translation_mm:
                flags.append("excessive_translation")
            if rotation_degrees > maximum_rotation_degrees:
                flags.append("excessive_rotation")

    return RegistrationQuality(
        passed=not flags,
        regions_present=present,
        atlas_brain_overlap=overlap,
        translation_mm=translation_mm,
        rotation_degrees=rotation_degrees,
        flags=tuple(flags),
    )


def quality_to_dict(quality: RegistrationQuality) -> dict[str, object]:
    return {
        "passed": quality.passed,
        "regions_present": quality.regions_present,
        "atlas_brain_overlap": quality.atlas_brain_overlap,
        "translation_mm": quality.translation_mm,
        "rotation_degrees": quality.rotation_degrees,
        "flags": list(quality.flags),
    }


def _register_level_to_slice(
    fixed_array: np.ndarray,
    fixed_spacing: tuple[float, float],
    atlas_image_path: str | Path,
    atlas_labels_path: str | Path,
) -> tuple[np.ndarray, float, sitk.Transform]:
    fixed = sitk.GetImageFromArray(fixed_array.astype(np.float32))
    fixed.SetSpacing(fixed_spacing)
    atlas = sitk.ReadImage(str(atlas_image_path), sitk.sitkFloat32)
    labels = sitk.ReadImage(str(atlas_labels_path), sitk.sitkUInt16)
    if atlas.GetSize() != labels.GetSize():
        raise ValueError("2D atlas intensity and labels must have identical dimensions")
    fixed_mask = sitk.Cast(fixed > -100.0, sitk.sitkUInt8)
    moving_mask = sitk.Cast(atlas > 0.0, sitk.sitkUInt8)
    fixed = sitk.RescaleIntensity(fixed, 0.0, 1.0)
    atlas = sitk.RescaleIntensity(atlas, 0.0, 1.0)
    initial = sitk.CenteredTransformInitializer(
        fixed,
        atlas,
        sitk.Similarity2DTransform(),
        sitk.CenteredTransformInitializerFilter.GEOMETRY,
    )
    registration = sitk.ImageRegistrationMethod()
    registration.SetMetricAsMattesMutualInformation(numberOfHistogramBins=32)
    registration.SetMetricSamplingStrategy(registration.RANDOM)
    registration.SetMetricSamplingPercentage(0.2, seed=17)
    registration.SetMetricFixedMask(fixed_mask)
    registration.SetMetricMovingMask(moving_mask)
    registration.SetInterpolator(sitk.sitkLinear)
    registration.SetOptimizerAsRegularStepGradientDescent(
        learningRate=0.5,
        minStep=1e-3,
        numberOfIterations=60,
        relaxationFactor=0.5,
    )
    registration.SetOptimizerScalesFromPhysicalShift()
    registration.SetInitialTransform(initial, inPlace=False)
    transform = registration.Execute(fixed, atlas)
    registered_labels = sitk.Resample(labels, fixed, transform, sitk.sitkNearestNeighbor, 0, sitk.sitkUInt16)
    return sitk.GetArrayFromImage(registered_labels), float(registration.GetMetricValue()), transform


def register_two_level_atlas(
    ct: np.ndarray,
    ct_spacing: tuple[float, float],
    levels: dict[str, tuple[str | Path, str | Path]],
) -> TwoLevelRegistrationResult:
    """Register BGL/SGL 2D atlases to the best matching CT axial slices."""
    if ct.ndim != 3:
        raise ValueError("expected a 3D CT array")
    combined = np.zeros_like(ct, dtype=np.uint16)
    metadata: dict[str, dict[str, object]] = {}
    used_slices: set[int] = set()
    for level_name, (image_path, labels_path) in levels.items():
        best: tuple[float, float, int, np.ndarray, sitk.Transform] | None = None
        start = 0 if level_name == "BGL" else max(0, int(ct.shape[2] * 0.65))
        stop = int(ct.shape[2] * 0.55) if level_name == "BGL" else ct.shape[2]
        for slice_index in range(start, max(start + 1, stop)):
            if slice_index in used_slices:
                continue
            try:
                registered, metric, transform = _register_level_to_slice(
                    ct[:, :, slice_index].T,
                    ct_spacing,
                    image_path,
                    labels_path,
                )
            except RuntimeError:
                continue
            registered_xy = registered.T
            brain_slice = ct[:, :, slice_index] > -100.0
            registered_overlap = float(np.mean(brain_slice[registered_xy > 0])) if np.any(registered_xy > 0) else 0.0
            candidate = (registered_overlap, metric, slice_index, registered_xy, transform)
            if best is None or (registered_overlap, -metric) > (best[0], -best[1]):
                best = candidate
        if best is None:
            raise ValueError(f"registration_failed_{level_name}")
        overlap, metric, slice_index, registered, transform = best
        used_slices.add(slice_index)
        if level_name == "BGL" and not set(np.unique(registered)) - {0} <= set(range(1, 8)):
            raise ValueError("BGL labels must be 1..7")
        if level_name == "SGL" and not set(np.unique(registered)) - {0} <= set(range(8, 11)):
            raise ValueError("SGL labels must be 8..10")
        combined[:, :, slice_index] = registered
        metadata[level_name] = {
            "slice_index": slice_index,
            "metric_value": metric,
            "slice_brain_overlap": overlap,
            "transform": transform.GetParameters(),
            "fixed_parameters": transform.GetFixedParameters(),
        }
    return TwoLevelRegistrationResult(combined, metadata)