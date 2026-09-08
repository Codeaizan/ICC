from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Case:
    case_id: str
    ct_path: Path
    lesion_path: Path | None
    split: str
    age: str = ""
    age_group: str = "unknown"


def read_manifest(path: str | Path, root: str | Path | None = None) -> list[Case]:
    manifest_path = Path(path)
    base = Path(root) if root else manifest_path.parent.parent.parent
    required = {"case_id", "ct_path", "split"}
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not required.issubset(reader.fieldnames or set()):
            raise ValueError(f"manifest must contain columns: {', '.join(sorted(required))}")
        cases = []
        for row in reader:
            if not row.get("case_id", "").strip() or row["case_id"].lstrip().startswith("#"):
                continue
            ct_path = base / row["ct_path"]
            lesion = row.get("lesion_path") or None
            cases.append(Case(
                row["case_id"],
                ct_path,
                base / lesion if lesion else None,
                row["split"],
                row.get("age", ""),
                row.get("age_group", "unknown"),
            ))
    return cases