from __future__ import annotations

from experiments.io import read_csv, read_json


def test_mesh_sensitivity_outputs_exist_and_vary(coupling_sweep_artifacts):
    mesh_summary_csv = coupling_sweep_artifacts / 'summary_table_mesh.csv'
    mesh_summary_json = coupling_sweep_artifacts / 'summary_table_mesh.json'
    assert mesh_summary_csv.exists()
    assert mesh_summary_json.exists()

    rows = read_csv(mesh_summary_csv)
    payload = read_json(mesh_summary_json)
    expected_case_names = {
        'aligned_mesh_fine',
        'aligned_mesh_coarse',
        'rotated_mesh_fine',
        'rotated_mesh_coarse',
        'narrow_corridor_refine',
        'wide_corridor_refine',
    }
    assert {row['case_name'] for row in rows} == expected_case_names
    assert len(payload) == len(rows)

    for case_name in expected_case_names:
        case_dir = coupling_sweep_artifacts / 'mesh_sensitivity' / case_name
        assert case_dir.is_dir()
        assert (case_dir / 'summary_metrics.json').exists()

    triangle_counts = {int(float(row['triangle_count'])) for row in rows}
    rmse_values = {round(float(row['RMSE_stage_vs_reference']), 8) for row in rows}
    assert len(triangle_counts) > 1 or len(rmse_values) > 1
