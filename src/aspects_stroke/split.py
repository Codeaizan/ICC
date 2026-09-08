from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path


def create_split_manifest(
    input_manifest: str | Path,
    output_manifest: str | Path,
    *,
    seed: int = 20260908,
    train_fraction: float = 0.70,
    validation_fraction: float = 0.15,
) -> Path:
    source = Path(input_manifest)
    output = Path(output_manifest)
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("age_group") not in {"10_29", "30_49", "50_69", "70_89"}:
            continue
        if not Path(row["ct_path"]).exists() or not Path(row["lesion_path"]).exists():
            continue
        groups[row["age_group"]].append(row)

    rng = random.Random(seed)
    selected: list[dict[str, str]] = []
    for group_rows in groups.values():
        rng.shuffle(group_rows)
        selected.extend(group_rows)
    rng.shuffle(selected)
    train_end = int(len(selected) * train_fraction)
    validation_end = train_end + int(len(selected) * validation_fraction)
    for index, row in enumerate(selected):
        row["split"] = "train" if index < train_end else "validation" if index < validation_end else "test"

    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["case_id", "ct_path", "lesion_path", "split", "age", "age_group"]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(selected)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a reproducible stratified AISD split manifest")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=20260908)
    args = parser.parse_args()
    output = create_split_manifest(args.input, args.output, seed=args.seed)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()