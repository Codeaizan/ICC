from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import SimpleITK as sitk

from .manifest import read_manifest
from .pipeline import run_case


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ASPECTS scoring over an AISD manifest")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--atlas-labels")
    parser.add_argument("--atlas-image")
    parser.add_argument("--bgl-image")
    parser.add_argument("--bgl-labels")
    parser.add_argument("--sgl-image")
    parser.add_argument("--sgl-labels")
    parser.add_argument("--atlas-dir", help="directory containing age-specific BGL/SGL atlas files")
    parser.add_argument("--output", required=True)
    parser.add_argument("--split", default=None)
    parser.add_argument("--workers", type=int, default=6, help="parallel case processes; use 4-6 on an i5-12450H")
    return parser


def atlas_for_case(atlas_dir: str | Path, age_group: str) -> tuple[Path, Path, Path, Path]:
    if age_group not in {"10_29", "30_49", "50_69", "70_89"}:
        raise ValueError("unknown_age_group")
    root = Path(atlas_dir)
    paths = tuple(root / f"{level}_{kind}_{age_group}.nii.gz" for level in ("BGL", "SGL") for kind in ("image", "label"))
    if not all(path.exists() for path in paths):
        missing = [str(path) for path in paths if not path.exists()]
        raise FileNotFoundError("missing atlas files: " + ", ".join(missing))
    return paths[0], paths[1], paths[2], paths[3]


def run_batch_case(case, args):
    sitk.ProcessObject.SetGlobalDefaultNumberOfThreads(1)
    bgl_image = args.bgl_image
    bgl_labels = args.bgl_labels
    sgl_image = args.sgl_image
    sgl_labels = args.sgl_labels
    if args.atlas_dir:
        bgl_image, bgl_labels, sgl_image, sgl_labels = atlas_for_case(args.atlas_dir, case.age_group)
    try:
        report = run_case(
            case.ct_path,
            args.atlas_labels,
            Path(args.output) / case.case_id,
            args.atlas_image,
            bgl_image,
            bgl_labels,
            sgl_image,
            sgl_labels,
        )
    except (OSError, RuntimeError, ValueError) as error:
        status = "abstain" if str(error) == "unknown_age_group" else "error"
        report = {"status": status, "case_id": case.case_id, "aspects": None, "reason": str(error)}
        case_output = Path(args.output) / case.case_id
        case_output.mkdir(parents=True, exist_ok=True)
        (case_output / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"case_id": case.case_id, **report}


def main() -> None:
    args = build_parser().parse_args()
    root = Path.cwd()
    cases = read_manifest(args.manifest, root=root)
    if args.split:
        cases = [case for case in cases if case.split == args.split]
    summary = []
    workers = max(1, min(args.workers, len(cases) or 1))
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_batch_case, case, args): case.case_id for case in cases}
        for completed, future in enumerate(as_completed(futures), start=1):
            summary.append(future.result())
            print(f"Completed {completed}/{len(cases)}: {futures[future]}", flush=True)
    Path(args.output).mkdir(parents=True, exist_ok=True)
    (Path(args.output) / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"cases": len(summary), "output": args.output}, indent=2))


if __name__ == "__main__":
    main()