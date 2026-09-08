from __future__ import annotations

import argparse
import json
from pathlib import Path

import SimpleITK as sitk


def convert_dicom_series(input_dir: str | Path, output_path: str | Path) -> dict[str, object]:
    """Convert one DICOM CT series to NIfTI without windowing or rescaling."""
    input_path = Path(input_dir)
    series_ids = sitk.ImageSeriesReader.GetGDCMSeriesIDs(str(input_path))
    if not series_ids:
        raise ValueError(f"no DICOM series found in {input_path}")
    if len(series_ids) != 1:
        raise ValueError(f"expected one CT series in {input_path}, found {len(series_ids)}")
    files = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(str(input_path), series_ids[0])
    reader = sitk.ImageSeriesReader()
    reader.SetFileNames(files)
    image = reader.Execute()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(image, str(output))
    metadata = {
        "input": str(input_path),
        "output": str(output),
        "slices": len(files),
        "size": list(image.GetSize()),
        "spacing_mm": list(image.GetSpacing()),
        "origin_mm": list(image.GetOrigin()),
        "direction": list(image.GetDirection()),
        "pixel_type": image.GetPixelIDTypeAsString(),
    }
    output.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert one AISD DICOM CT series to NIfTI")
    parser.add_argument("--input", required=True, help="folder containing one CT DICOM series")
    parser.add_argument("--output", required=True, help="output .nii.gz path")
    args = parser.parse_args()
    print(json.dumps(convert_dicom_series(args.input, args.output), indent=2))


if __name__ == "__main__":
    main()