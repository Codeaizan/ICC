from __future__ import annotations

import argparse

from .pipeline import run_case


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Research baseline for explainable ASPECTS scoring")
    parser.add_argument("--ct", required=True, help="3D NCCT NIfTI in a consistent left-right orientation")
    parser.add_argument("--atlas-labels", help="3D ASPECTS label volume")
    parser.add_argument("--atlas-image", help="atlas intensity image; enables affine registration")
    parser.add_argument("--bgl-image")
    parser.add_argument("--bgl-labels")
    parser.add_argument("--sgl-image")
    parser.add_argument("--sgl-labels")
    parser.add_argument("--output", required=True, help="output directory")
    parser.add_argument("--drop-threshold", type=float, default=0.08)
    parser.add_argument("--lesion-fraction-threshold", type=float, default=0.05)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    import json

    print(json.dumps(run_case(
        args.ct,
        args.atlas_labels,
        args.output,
        args.atlas_image,
        args.bgl_image,
        args.bgl_labels,
        args.sgl_image,
        args.sgl_labels,
        drop_threshold=args.drop_threshold,
        lesion_fraction_threshold=args.lesion_fraction_threshold,
    ), indent=2))


if __name__ == "__main__":
    main()
