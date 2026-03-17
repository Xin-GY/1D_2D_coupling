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


def test_chapter_timing_breakdown_contains_expected_columns(chapter_analysis_artifacts):
    rows = read_csv(chapter_analysis_artifacts / 'summaries' / 'timing_breakdown.csv')
    assert rows
    required_columns = {
        'case_name',
        'scenario_family',
        'wall_clock_seconds',
        'one_d_advance_time',
        'two_d_gpu_kernel_time',
        'boundary_update_time',
        'exchange_manager_time',
        'misc_io_time',
        'one_d_share',
        'two_d_share',
        'boundary_share',
        'exchange_manager_share',
        'misc_io_share',
    }
    for row in rows:
        assert required_columns.issubset(row.keys())
        wall_clock = float(row['wall_clock_seconds'])
        subtotal = (
            float(row['one_d_advance_time'])
            + float(row['two_d_gpu_kernel_time'])
            + float(row['boundary_update_time'])
            + float(row['exchange_manager_time'])
            + float(row['misc_io_time'])
        )
        assert wall_clock >= 0.0
        assert subtotal >= 0.0
        assert abs(subtotal - wall_clock) < 5.0e-3

    benchmark_rows = [row for row in rows if 'test7' in row['scenario_family']]
    assert any(row['scheduler_mode'] == 'strict_global_min_dt' for row in read_csv(chapter_analysis_artifacts / 'summaries' / 'summary_table.csv') if 'test7' in row['scenario_family'])
    assert benchmark_rows


def test_fastest_exact_chapter_outputs_include_backend_timing_comparison(fastest_exact_chapter_artifacts):
    timing_rows = read_csv(fastest_exact_chapter_artifacts / 'summaries' / 'timing_breakdown.csv')
    assert timing_rows
    assert all({'one_d_backend', 'mesh_variant'}.issubset(row.keys()) for row in timing_rows)

    backend_rows = read_csv(fastest_exact_chapter_artifacts / 'summaries' / 'one_d_backend_timing.csv')
    assert {row['backend'] for row in backend_rows} == {'legacy', 'fastest_exact'}
    for row in backend_rows:
        assert float(row['wall_clock_seconds']) >= 0.0
        assert float(row['final_time']) > 0.0
        assert float(row['relative_to_legacy']) >= 0.0
