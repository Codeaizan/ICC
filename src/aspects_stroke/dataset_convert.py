from __future__ import annotations

import argparse
import csv
from pathlib import Path

import SimpleITK as sitk

from .convert import convert_dicom_series
from .mask_convert import convert_png_mask_stack


def age_group(age_text: str) -> str:
    digits = "".join(character for character in age_text if character.isdigit())
    if not digits:
        return "unknown"
    age = int(digits)
    if age < 30:
        return "10_29"
    if age < 50:
        return "30_49"
    if age < 70:
        return "50_69"
    if age < 90:
        return "70_89"
    return "unknown"


def read_patient_age(ct_dir: Path) -> str:
    files = sitk.ImageSeriesReader.GetGDCMSeriesFileNames(str(ct_dir))
    if not files:
        return ""
    image = sitk.ReadImage(files[0])
    return image.GetMetaData("0010|1010") if image.HasMetaDataKey("0010|1010") else ""


def manifest_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(Path.cwd().resolve())).replace("\\", "/")
    except ValueError:
        return str(resolved).replace("\\", "/")


def convert_dataset(dicom_root: str | Path, mask_root: str | Path, output_root: str | Path) -> Path:
    dicom_path = Path(dicom_root)
    masks_path = Path(mask_root)
    output_path = Path(output_root)
    output_path.mkdir(parents=True, exist_ok=True)
    manifest_file = output_path / "manifest.csv"
    rows: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    ct_dirs = sorted(dicom_path.glob("dicom-*/*/CT"))
    for ct_dir in ct_dirs:
        case_id = ct_dir.parent.name
        mask_dir = masks_path / case_id
        if not mask_dir.is_dir():
            continue
        try:
            ct_output = output_path / f"{case_id}_ct.nii.gz"
            mask_output = output_path / f"{case_id}_mask.nii.gz"
            if not ct_output.exists():
                convert_dicom_series(ct_dir, ct_output)
            if not mask_output.exists():
                convert_png_mask_stack(mask_dir, ct_output, mask_output)
            age = read_patient_age(ct_dir)
            rows.append({
                "case_id": case_id,
                "ct_path": manifest_path(ct_output),
                "lesion_path": manifest_path(mask_output),
                "split": "unassigned",
                "age": age,
                "age_group": age_group(age),
            })
        except (OSError, RuntimeError, ValueError) as error:
            failures.append({"case_id": case_id, "error": str(error)})
    with manifest_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case_id", "ct_path", "lesion_path", "split", "age", "age_group"])
        writer.writeheader()
        writer.writerows(rows)
    with (output_path / "conversion_errors.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case_id", "error"])
        writer.writeheader()
        writer.writerows(failures)
    return manifest_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert all AISD DICOM CT and PNG mask cases")
    parser.add_argument("--dicom-root", default="data/raw/aisd/dicom")
    parser.add_argument("--mask-root", default="data/raw/aisd/mask/mask")
    parser.add_argument("--output", default="data/processed/aisd")
    args = parser.parse_args()
    manifest = convert_dataset(args.dicom_root, args.mask_root, args.output)
    print(f"Wrote {manifest}")


if __name__ == "__main__":
    main()