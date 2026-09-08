from __future__ import annotations

import argparse
import json
from pathlib import Path

import nibabel as nib
import numpy as np

from .evaluate import dice_score
from .manifest import read_manifest


def tune_heat_threshold(
    manifest_path: str | Path,
    output_roots: list[str | Path],
    thresholds: list[float],
    max_cases: int | None = None,
) -> dict[str, object]:
    cases = {case.case_id: case for case in read_manifest(manifest_path, root=Path.cwd())}
    if max_cases is not None:
        cases = dict(list(cases.items())[:max_cases])
    samples: list[tuple[np.ndarray, np.ndarray]] = []
    skipped = 0
    for case in cases.values():
        output = next((Path(root) / case.case_id for root in output_roots if (Path(root) / case.case_id / "ischemia_heatmap.nii.gz").exists()), None)
        if output is None or case.lesion_path is None:
            skipped += 1
            continue
        heatmap = nib.load(str(output / "ischemia_heatmap.nii.gz")).get_fdata()
        target = nib.load(str(case.lesion_path)).get_fdata()
        if heatmap.shape != target.shape:
            skipped += 1
            continue
        samples.append((heatmap, np.isin(target, [1, 2, 3, 5])))
        print(f"Loaded {len(samples)}/{len(cases)} cases", flush=True)

    scores = []
    for threshold in thresholds:
        scores.append({
            "threshold": threshold,
            "mean_dice": float(np.mean([dice_score(heatmap >= threshold, target) for heatmap, target in samples])) if samples else 0.0,
        })
    best = max(scores, key=lambda item: item["mean_dice"]) if scores else None
    return {"cases_used": len(samples), "cases_skipped": skipped, "scores": scores, "best": best}


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune the exploratory symmetry heatmap threshold on AISD masks")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", action="append", required=True)
    parser.add_argument("--report", default="outputs/threshold_tuning.json")
    parser.add_argument("--start", type=float, default=0.02)
    parser.add_argument("--stop", type=float, default=0.30)
    parser.add_argument("--step", type=float, default=0.01)
    parser.add_argument("--max-cases", type=int, default=50)
    args = parser.parse_args()
    thresholds = np.arange(args.start, args.stop + args.step / 2, args.step).round(4).tolist()
    report = tune_heat_threshold(args.manifest, args.output, thresholds, args.max_cases)
    report["warning"] = "Exploratory calibration only: manifest splits are unassigned; do not report this as held-out performance."
    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"cases_used": report["cases_used"], "best": report["best"], "report": str(path)}, indent=2))


if __name__ == "__main__":
    main()