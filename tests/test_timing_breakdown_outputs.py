from __future__ import annotations

from experiments.io import read_csv


def test_timing_breakdown_contains_expected_cases_and_columns(coupling_sweep_artifacts):
    rows = read_csv(coupling_sweep_artifacts / 'timing_breakdown.csv')
    assert rows
    assert {row['case_label'] for row in rows} == {'strict', 'yield', '3s', '5s', '10s'}

    required_columns = {
        'case_label',
        'case_name',
        'wall_clock_seconds',
        'one_d_advance_time',
        'two_d_gpu_kernel_time',
        'boundary_update_time',
        'gpu_inlets_apply_time',
        'scheduler_manager_overhead',
    }
    for row in rows:
        assert required_columns.issubset(row.keys())
        wall_clock = float(row['wall_clock_seconds'])
        subtotal = (
            float(row['one_d_advance_time'])
            + float(row['two_d_gpu_kernel_time'])
            + float(row['boundary_update_time'])
            + float(row['gpu_inlets_apply_time'])
            + float(row['scheduler_manager_overhead'])
        )
        assert wall_clock >= 0.0
        assert subtotal >= 0.0
        assert abs(subtotal - wall_clock) < 5.0e-3
