from aspects_stroke.tune import tune_heat_threshold


def test_tune_heat_threshold_selects_best_threshold(tmp_path):
    manifest = tmp_path / "manifest.csv"
    manifest.write_text("case_id,ct_path,lesion_path,split\n", encoding="utf-8")
    assert tune_heat_threshold(manifest, [], [0.1, 0.2])["cases_used"] == 0