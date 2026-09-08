import csv

from aspects_stroke.split import create_split_manifest


def test_create_split_manifest_is_reproducible(tmp_path):
    ct = tmp_path / "ct.nii.gz"
    mask = tmp_path / "mask.nii.gz"
    ct.write_bytes(b"ct")
    mask.write_bytes(b"mask")
    source = tmp_path / "manifest.csv"
    rows = [
        {"case_id": f"case_{index}", "ct_path": str(ct), "lesion_path": str(mask), "split": "unassigned", "age": "55", "age_group": "50_69"}
        for index in range(10)
    ]
    with source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    create_split_manifest(source, first)
    create_split_manifest(source, second)

    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")