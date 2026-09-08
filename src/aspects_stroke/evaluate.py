from __future__ import annotations

import argparse
import json
from pathlib import Path

import nibabel as nib
import numpy as np

from .manifest import read_manifest


def dice_score(prediction: np.ndarray, target: np.ndarray) -> float:
    prediction = prediction.astype(bool)
    target = target.astype(bool)
    denominator = int(prediction.sum() + target.sum())
    if denominator == 0:
        return 1.0
    return float(2 * np.logical_and(prediction, target).sum() / denominator)


def evaluate_case(case, output_dir: Path, heat_threshold: float = 0.08) -> dict[str, object]:
    result_path = output_dir / "result.json"
    if not result_path.exists():
        return {"case_id": case.case_id, "status": "missing_output"}
    report = json.loads(result_path.read_text(encoding="utf-8"))
    if report.get("status") != "scored":
        return {"case_id": case.case_id, "status": "abstain", "reason": report.get("reason")}
    if case.lesion_path is None:
        return {"case_id": case.case_id, "status": "missing_mask"}
    required = [output_dir / "ischemia_heatmap.nii.gz", output_dir / "registered_regions.nii.gz"]
    if not all(path.exists() for path in required):
        return {"case_id": case.case_id, "status": "missing_output_artifact"}
    heatmap = nib.load(str(output_dir / "ischemia_heatmap.nii.gz")).get_fdata()
    regions = nib.load(str(output_dir / "registered_regions.nii.gz")).get_fdata()
    target = nib.load(str(case.lesion_path)).get_fdata()
    if not (heatmap.shape == regions.shape == target.shape):
        return {"case_id": case.case_id, "status": "shape_mismatch"}
    target_lesion = np.isin(target, [1, 2, 3, 5])
    predicted_lesion = heatmap >= heat_threshold
    region_rows = []
    for region in report.get("regions", []):
        label = int(region["label"])
        region_mask = regions == label
        target_affected = bool(np.any(target_lesion & region_mask))
        region_rows.append({
            "label": label,
            "name": region["name"],
            "predicted_affected": bool(region["affected"]),
            "target_affected": target_affected,
            "match": bool(region["affected"]) == target_affected,
        })
    return {
        "case_id": case.case_id,
        "status": "evaluated",
        "aspects": report.get("aspects"),
        "lesion_dice": dice_score(predicted_lesion, target_lesion),
        "regions": region_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate ASPECTS heatmaps against AISD masks")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", action="append", required=True, help="output root; repeat for main and retry results")
    parser.add_argument("--heat-threshold", type=float, default=0.08)
    parser.add_argument("--report", default="outputs/evaluation.json")
    args = parser.parse_args()
    cases = {case.case_id: case for case in read_manifest(args.manifest, root=Path.cwd())}
    evaluated = []
    for case_id, case in cases.items():
        output_dir = next((Path(root) / case_id for root in args.output if (Path(root) / case_id / "result.json").exists()), None)
        if output_dir is None:
            continue
        evaluated.append(evaluate_case(case, output_dir, args.heat_threshold))
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(evaluated, indent=2), encoding="utf-8")
    print(f"Wrote {report_path} for {len(evaluated)} cases")


if __name__ == "__main__":
    main()