"""ML inference and evaluation for the trained 2D U-Net lesion detector.

Workflow:
  1. Run on validation split with ``--sweep-threshold`` to find optimal
     probability threshold.
  2. Run once on the test split with ``--threshold <value>`` to get final
     held-out metrics.

This is a research prototype; do not use for clinical decisions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import nibabel as nib
import numpy as np
import torch
import torch.nn.functional as F

from .manifest import read_manifest
from .train import SmallUNet, normalize_ct

# ------------------------------------------------------------------
# Prediction helpers
# ------------------------------------------------------------------

def predict_volume(
    model: SmallUNet,
    ct_path: str | Path,
    device: torch.device,
    image_size: int = 256,
) -> np.ndarray:
    """Return a 3-D probability volume (same shape as the input CT)."""
    ct_nii = nib.load(str(ct_path))
    ct_data = ct_nii.get_fdata(dtype=np.float32)
    height, width, num_slices = ct_data.shape
    prob_volume = np.zeros_like(ct_data, dtype=np.float32)

    model.eval()
    with torch.no_grad():
        for z in range(num_slices):
            image = normalize_ct(ct_data[:, :, z])
            mirrored = np.flip(image, axis=0).copy()
            difference = np.clip(
                (mirrored - image) / np.maximum(mirrored, 0.05), 0.0, 1.0
            )
            channels = np.stack((image, mirrored, difference))  # (3, H, W)
            tensor = torch.from_numpy(channels).unsqueeze(0).to(device)
            tensor = F.interpolate(
                tensor, size=(image_size, image_size),
                mode="bilinear", align_corners=False,
            )
            logits = model(tensor)
            prob = torch.sigmoid(logits)
            # Resize back to original slice dimensions
            prob = F.interpolate(
                prob, size=(height, width),
                mode="bilinear", align_corners=False,
            )
            prob_volume[:, :, z] = prob.squeeze().cpu().numpy()

    return prob_volume


def save_prediction_nifti(
    prob_volume: np.ndarray,
    reference_path: str | Path,
    output_path: str | Path,
    threshold: float | None = None,
) -> None:
    """Save probability (or binary) prediction as NIfTI."""
    ref = nib.load(str(reference_path))
    data = prob_volume if threshold is None else (prob_volume >= threshold).astype(np.float32)
    out = nib.Nifti1Image(data, ref.affine, ref.header)
    nib.save(out, str(output_path))


# ------------------------------------------------------------------
# Metrics
# ------------------------------------------------------------------

def _compute_metrics(
    prediction: np.ndarray,
    target: np.ndarray,
) -> dict[str, float]:
    pred_bool = prediction.astype(bool)
    tgt_bool = target.astype(bool)
    tp = int(np.logical_and(pred_bool, tgt_bool).sum())
    fp = int(np.logical_and(pred_bool, ~tgt_bool).sum())
    fn = int(np.logical_and(~pred_bool, tgt_bool).sum())
    denom = int(pred_bool.sum() + tgt_bool.sum())
    dice = 1.0 if denom == 0 else float(2 * tp / denom)
    precision = 1.0 if (tp + fp) == 0 else float(tp / (tp + fp))
    recall = 1.0 if (tp + fn) == 0 else float(tp / (tp + fn))
    f1 = 0.0 if (precision + recall) == 0 else float(
        2 * precision * recall / (precision + recall)
    )
    return {"dice": dice, "precision": precision, "recall": recall, "f1": f1}


# ------------------------------------------------------------------
# Evaluation drivers
# ------------------------------------------------------------------

def evaluate_split(
    model: SmallUNet,
    cases: list,
    device: torch.device,
    threshold: float,
    image_size: int = 256,
    output_dir: Path | None = None,
) -> list[dict]:
    """Predict every case, compare to ground-truth mask, return per-case metrics."""
    results: list[dict] = []
    for i, case in enumerate(cases):
        print(f"  [{i + 1}/{len(cases)}] {case.case_id}", flush=True)
        if case.lesion_path is None or not Path(case.ct_path).exists():
            results.append({"case_id": case.case_id, "status": "skipped"})
            continue
        if not Path(case.lesion_path).exists():
            results.append({"case_id": case.case_id, "status": "missing_mask"})
            continue

        prob = predict_volume(model, case.ct_path, device, image_size)
        binary = (prob >= threshold).astype(np.float32)

        target = nib.load(str(case.lesion_path)).get_fdata(dtype=np.float32)
        target_lesion = np.isin(target, [1, 2, 3, 5]).astype(np.float32)

        if binary.shape != target_lesion.shape:
            results.append({"case_id": case.case_id, "status": "shape_mismatch"})
            continue

        metrics = _compute_metrics(binary, target_lesion)

        if output_dir is not None:
            case_dir = output_dir / case.case_id
            case_dir.mkdir(parents=True, exist_ok=True)
            save_prediction_nifti(prob, case.ct_path, case_dir / "ml_prob.nii.gz")
            save_prediction_nifti(
                prob, case.ct_path, case_dir / "ml_pred.nii.gz", threshold
            )

        results.append({
            "case_id": case.case_id,
            "status": "evaluated",
            **metrics,
        })
    return results


def sweep_thresholds(
    model: SmallUNet,
    cases: list,
    device: torch.device,
    image_size: int = 256,
    thresholds: list[float] | None = None,
) -> tuple[float, dict]:
    """Find the probability threshold that maximises mean Dice on *cases*.

    Returns ``(best_threshold, {threshold: mean_dice, ...})``.
    """
    if thresholds is None:
        thresholds = [round(t * 0.05, 2) for t in range(1, 19)]  # 0.05 .. 0.90

    # Pre-compute all probability volumes to avoid repeated forward passes
    print("Computing probability volumes for threshold sweep …", flush=True)
    volumes: list[tuple[np.ndarray, np.ndarray]] = []
    for i, case in enumerate(cases):
        print(f"  [{i + 1}/{len(cases)}] {case.case_id}", flush=True)
        if case.lesion_path is None or not Path(case.ct_path).exists():
            continue
        if not Path(case.lesion_path).exists():
            continue
        prob = predict_volume(model, case.ct_path, device, image_size)
        target = nib.load(str(case.lesion_path)).get_fdata(dtype=np.float32)
        target_lesion = np.isin(target, [1, 2, 3, 5]).astype(np.float32)
        if prob.shape != target_lesion.shape:
            continue
        volumes.append((prob, target_lesion))

    print(f"Sweeping {len(thresholds)} thresholds over {len(volumes)} cases …", flush=True)
    sweep: dict[str, float] = {}
    best_thresh = thresholds[0]
    best_dice = -1.0
    for thr in thresholds:
        dices = [
            _compute_metrics((p >= thr).astype(np.float32), t)["dice"]
            for p, t in volumes
        ]
        mean_dice = float(np.mean(dices)) if dices else 0.0
        sweep[str(thr)] = mean_dice
        tag = ""
        if mean_dice > best_dice:
            best_dice = mean_dice
            best_thresh = thr
            tag = "  ← best"
        print(f"  threshold={thr:.2f}  mean_dice={mean_dice:.4f}{tag}", flush=True)

    return best_thresh, sweep


def _aggregate(results: list[dict]) -> dict:
    evaluated = [r for r in results if r.get("status") == "evaluated"]
    if not evaluated:
        return {"count": 0}
    dices = [r["dice"] for r in evaluated]
    precisions = [r["precision"] for r in evaluated]
    recalls = [r["recall"] for r in evaluated]
    f1s = [r["f1"] for r in evaluated]
    return {
        "count": len(evaluated),
        "mean_dice": float(np.mean(dices)),
        "median_dice": float(np.median(dices)),
        "std_dice": float(np.std(dices)),
        "mean_precision": float(np.mean(precisions)),
        "mean_recall": float(np.mean(recalls)),
        "mean_f1": float(np.mean(f1s)),
    }


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="ML inference and evaluation for the trained lesion U-Net"
    )
    parser.add_argument("--manifest", required=True, help="model_manifest.csv path")
    parser.add_argument("--checkpoint", required=True, help="path to best_small_unet.pt")
    parser.add_argument("--split", default="test", help="manifest split to evaluate")
    parser.add_argument("--threshold", type=float, default=None,
                        help="probability threshold (required for test evaluation)")
    parser.add_argument("--sweep-threshold", action="store_true",
                        help="sweep thresholds and report best (use on validation only)")
    parser.add_argument("--output", default=None,
                        help="output directory for prediction NIfTIs")
    parser.add_argument("--report", default=None, help="path for JSON report")
    parser.add_argument("--device", choices=("auto", "cuda", "cpu"), default="auto")
    parser.add_argument("--size", type=int, default=256, help="image size used during training")
    args = parser.parse_args()

    # Resolve device
    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but not available")
    device = torch.device(
        "cuda" if args.device == "auto" and torch.cuda.is_available()
        else args.device if args.device != "auto" else "cpu"
    )
    print(f"Device: {device}", flush=True)

    # Load model
    model = SmallUNet()
    state = torch.load(args.checkpoint, map_location=device, weights_only=True)
    model.load_state_dict(state)
    model.to(device)
    model.eval()
    print("Checkpoint loaded.", flush=True)

    # Read manifest
    cases = [c for c in read_manifest(args.manifest, root=Path(args.manifest).parent)
             if c.split == args.split]
    print(f"Split '{args.split}': {len(cases)} cases", flush=True)

    if args.sweep_threshold:
        best_thresh, sweep = sweep_thresholds(model, cases, device, args.size)
        print(f"\nBest threshold: {best_thresh:.2f}", flush=True)
        report = {"mode": "sweep", "split": args.split, "best_threshold": best_thresh, "sweep": sweep}
    else:
        threshold = args.threshold
        if threshold is None:
            parser.error("--threshold is required when not using --sweep-threshold")
        out_dir = Path(args.output) if args.output else None
        results = evaluate_split(model, cases, device, threshold, args.size, out_dir)
        agg = _aggregate(results)
        print(f"\n=== {args.split} evaluation (threshold={threshold:.2f}) ===", flush=True)
        for key, val in agg.items():
            print(f"  {key}: {val}", flush=True)
        report = {
            "mode": "evaluate",
            "split": args.split,
            "threshold": threshold,
            "aggregate": agg,
            "cases": results,
        }

    # Write report
    report_path = Path(args.report) if args.report else Path(
        f"outputs/ml_{args.split}_{'sweep' if args.sweep_threshold else 'eval'}.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report written to {report_path}", flush=True)


if __name__ == "__main__":
    main()
