from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import SimpleITK as sitk
from PIL import Image


def convert_png_mask_stack(
    input_dir: str | Path,
    reference_ct: str | Path,
    output_path: str | Path,
) -> None:
    """Convert an AISD PNG mask stack and copy geometry from its CT NIfTI."""
    input_path = Path(input_dir)
    files = sorted(input_path.glob("*.png"), key=lambda path: int(path.stem))
    if not files:
        raise ValueError(f"no PNG masks found in {input_path}")
    arrays = [np.asarray(Image.open(path), dtype=np.uint8) for path in files]
    if len({array.shape for array in arrays}) != 1:
        raise ValueError("mask PNGs do not have consistent dimensions")
    reference = sitk.ReadImage(str(reference_ct), sitk.sitkInt16)
    volume = sitk.GetImageFromArray(np.stack(arrays, axis=0))
    if volume.GetSize() != reference.GetSize():
        raise ValueError(f"mask shape {volume.GetSize()} does not match CT shape {reference.GetSize()}")
    volume.CopyInformation(reference)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(volume, str(output))


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert AISD PNG masks to a CT-aligned NIfTI")
    parser.add_argument("--input", required=True, help="folder containing numbered PNG masks")
    parser.add_argument("--reference-ct", required=True, help="converted CT NIfTI")
    parser.add_argument("--output", required=True, help="output mask NIfTI")
    args = parser.parse_args()
    convert_png_mask_stack(args.input, args.reference_ct, args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()