from __future__ import annotations

from experiments.io import read_csv, read_json


REQUIRED_METRIC_KEYS = {
    'case_name',
    'wall_clock_seconds',
    'simulated_duration',
    'exchange_count',
    'cumulative_exchange_volume',
    'final_total_mass_error',
    'max_abs_mass_error',
    'cumulative_mass_error',
    'normalized_mass_error',
    'peak_stage_1d',
    'peak_stage_2d',
    'peak_Q_exchange',
    'triangle_count',
    'RMSE_stage_vs_reference',
    'max_abs_stage_diff_vs_reference',
    'arrival_time_diff_vs_reference',
    'phase_lag_seconds',
    'peak_stage_error',
    'peak_time_error',
    'hydrograph_NSE',
}


def test_summary_tables_include_required_metrics(coupling_sweep_artifacts):
    csv_rows = read_csv(coupling_sweep_artifacts / 'summary_table.csv')
    json_rows = read_json(coupling_sweep_artifacts / 'summary_table.json')
    assert csv_rows
    assert len(json_rows) == len(csv_rows)

    for row in csv_rows:
        assert REQUIRED_METRIC_KEYS.issubset(row.keys())

    strict_row = next(row for row in csv_rows if row['case_name'] == 'mixed_bidirectional_pulse_strict_global_min_dt')
    assert float(strict_row['RMSE_stage_vs_reference']) == 0.0
    assert float(strict_row['max_abs_stage_diff_vs_reference']) == 0.0
    assert float(strict_row['arrival_time_diff_vs_reference']) == 0.0
    assert float(strict_row['phase_lag_seconds']) == 0.0
    assert float(strict_row['peak_stage_error']) == 0.0
    assert float(strict_row['peak_time_error']) == 0.0
