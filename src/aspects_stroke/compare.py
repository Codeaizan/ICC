"""Compare rule-based, ML, and hybrid lesion detectors on the same cases.

Computes voxel-level Dice/precision/recall/F1 for each approach and prints a
side-by-side summary table.  Region-level comparison requires atlas registration
outputs; this module operates at the voxel level using only CT + ML predictions.

This is a research prototype; do not use for clinical decisions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import nibabel as nib
import numpy as np

from .infer import _compute_metrics
from .manifest import read_manifest
from .preprocess import preprocess_ct
from .symmetry import asymmetry_heatmap, mirror_volume


def compare_case(
    ct_path: Path,
    mask_path: Path,
    ml_prob_path: Path | None,
    *,
    heat_threshold: float = 0.08,
    ml_threshold: float = 0.07,
) -> dict[str, object]:
    """Evaluate all three detector approaches on a single case."""
    ct = nib.load(str(ct_path)).get_fdata(dtype=np.float32)
    target_raw = nib.load(str(mask_path)).get_fdata(dtype=np.float32)
    target = np.isin(target_raw, [1, 2, 3, 5]).astype(np.float32)

    if ct.shape != target.shape:
        return {"status": "shape_mismatch"}

    # Rule-based: symmetry heatmap
    try:
        prep = preprocess_ct(ct)
    except ValueError:
        return {"status": "preprocessing_failed"}

    mirrored = mirror_volume(ct, midline=prep.midline_x)
    heatmap = asymmetry_heatmap(ct, mirrored) * prep.brain_mask
    rule_pred = (heatmap >= heat_threshold).astype(np.float32)
    rule_metrics = _compute_metrics(rule_pred, target)

    result: dict[str, object] = {
        "status": "evaluated",
        "lesion_voxels": int(target.sum()),
        "rule_based": rule_metrics,
    }

    # ML: probability map
    if ml_prob_path is not None and ml_prob_path.exists():
        ml_prob = nib.load(str(ml_prob_path)).get_fdata(dtype=np.float32)
        if ml_prob.shape == target.shape:
            ml_pred = (ml_prob >= ml_threshold).astype(np.float32)
            result["ml"] = _compute_metrics(ml_pred, target)

            # Hybrid: rule-based OR (ML positive AND some symmetry evidence)
            hybrid_pred = np.maximum(
                rule_pred,
                ((ml_prob >= 0.5) & (heatmap > 0)).astype(np.float32),
            )
            result["hybrid"] = _compute_metrics(hybrid_pred, target)
        else:
            result["ml"] = {"status": "shape_mismatch"}
            result["hybrid"] = {"status": "shape_mismatch"}
    else:
        result["ml"] = {"status": "missing_prediction"}
        result["hybrid"] = {"status": "missing_prediction"}

    return result


def _print_table(aggregate: dict[str, dict]) -> None:
    """Print a formatted comparison table."""
    approaches = ["rule_based", "ml", "hybrid"]
    metrics = ["dice", "precision", "recall", "f1"]
    header = f"{'':>12}" + "".join(f"{m:>12}" for m in metrics)
    print(header)
    print("-" * len(header))
    for approach in approaches:
        agg = aggregate.get(approach, {})
        if not agg or "mean_dice" not in agg:
            print(f"{approach:>12}  (no data)")
            continue
        row = f"{approach:>12}"
        for m in metrics:
            val = agg.get(f"mean_{m}", 0.0)
            row += f"{val:12.4f}"
        print(row)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare rule-based, ML, and hybrid lesion detectors"
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--split", default="test")
    parser.add_argument("--ml-predictions", default=None,
                        help="directory with <case_id>/ml_prob.nii.gz")
    parser.add_argument("--heat-threshold", type=float, default=0.08)
    parser.add_argument("--ml-threshold", type=float, default=0.07)
    parser.add_argument("--report", default="outputs/comparison.json")
    args = parser.parse_args()

    cases = [c for c in read_manifest(args.manifest, root=Path(args.manifest).parent)
             if c.split == args.split]
    print(f"Split '{args.split}': {len(cases)} cases\n", flush=True)

    ml_dir = Path(args.ml_predictions) if args.ml_predictions else None
    results: list[dict] = []

    for i, case in enumerate(cases):
        print(f"  [{i + 1}/{len(cases)}] {case.case_id}", end="", flush=True)
        if case.lesion_path is None or not Path(case.ct_path).exists():
            results.append({"case_id": case.case_id, "status": "skipped"})
            print(" — skipped")
            continue
        if not Path(case.lesion_path).exists():
            results.append({"case_id": case.case_id, "status": "missing_mask"})
            print(" — missing mask")
            continue

        ml_prob_path = ml_dir / case.case_id / "ml_prob.nii.gz" if ml_dir else None
        row = compare_case(
            Path(case.ct_path),
            Path(case.lesion_path),
            ml_prob_path,
            heat_threshold=args.heat_threshold,
            ml_threshold=args.ml_threshold,
        )
        row["case_id"] = case.case_id
        results.append(row)
        # Print inline per-case Dice for each approach
        dices = []
        for approach in ("rule_based", "ml", "hybrid"):
            d = row.get(approach, {})
            if isinstance(d, dict) and "dice" in d:
                dices.append(f"{approach}={d['dice']:.3f}")
        print(f"  {', '.join(dices)}" if dices else "")

    # Aggregate
    evaluated = [r for r in results if r.get("status") == "evaluated"]
    aggregate: dict[str, dict] = {}
    for approach in ("rule_based", "ml", "hybrid"):
        valid = [r[approach] for r in evaluated
                 if isinstance(r.get(approach), dict) and "dice" in r[approach]]
        if not valid:
            continue
        aggregate[approach] = {
            "count": len(valid),
            "mean_dice": float(np.mean([v["dice"] for v in valid])),
            "median_dice": float(np.median([v["dice"] for v in valid])),
            "std_dice": float(np.std([v["dice"] for v in valid])),
            "mean_precision": float(np.mean([v["precision"] for v in valid])),
            "mean_recall": float(np.mean([v["recall"] for v in valid])),
            "mean_f1": float(np.mean([v["f1"] for v in valid])),
        }

    print(f"\n{'=' * 60}")
    print(f"Comparison: {len(evaluated)} evaluated cases (split={args.split})")
    print(f"  heat_threshold={args.heat_threshold}  ml_threshold={args.ml_threshold}")
    print(f"{'=' * 60}\n")
    _print_table(aggregate)

    # Counts
    total = len(results)
    skipped = sum(1 for r in results if r.get("status") in ("skipped", "missing_mask"))
    failed = sum(1 for r in results if r.get("status") in ("shape_mismatch", "preprocessing_failed"))
    print(f"\n  total={total}  evaluated={len(evaluated)}  skipped={skipped}  failed={failed}")

    # Save report
    report = {
        "split": args.split,
        "heat_threshold": args.heat_threshold,
        "ml_threshold": args.ml_threshold,
        "aggregate": aggregate,
        "cases": results,
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport written to {report_path}", flush=True)


if __name__ == "__main__":
    main()
