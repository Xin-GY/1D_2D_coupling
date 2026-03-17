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


CHAPTER_REQUIRED_METRIC_KEYS = {
    'case_name',
    'scenario_family',
    'case_variant',
    'scheduler_mode',
    'reference_policy',
    'source_mode',
    'wall_clock_seconds',
    'simulated_duration',
    'exchange_event_count',
    'first_exchange_time',
    'cumulative_exchange_volume',
    'sign_flip_count',
    'link_mass_closure_error',
    'final_total_mass_error',
    'normalized_mass_error',
    'cumulative_mass_error',
    'relative_cost_ratio',
    'interval_over_t_arr_ref',
    'interval_over_t_rise_ref',
    'stage_rmse',
    'discharge_rmse',
    'peak_stage_error',
    'peak_discharge_error',
    'peak_time_error',
    'arrival_time_error',
    'phase_lag',
    'hydrograph_NSE',
    'max_depth_map_difference',
    'arrival_time_map_difference',
    'inundated_area_difference',
    'wet_area_iou',
    'wet_area_csi',
    'first_exchange_offset_vs_arrival',
}


def test_chapter_summary_tables_include_required_metrics(chapter_analysis_artifacts):
    csv_rows = read_csv(chapter_analysis_artifacts / 'summaries' / 'summary_table.csv')
    json_rows = read_json(chapter_analysis_artifacts / 'summaries' / 'summary_table.json')
    assert csv_rows
    assert len(json_rows) == len(csv_rows)
    for row in csv_rows:
        assert CHAPTER_REQUIRED_METRIC_KEYS.issubset(row.keys())

    strict_row = next(
        row
        for row in csv_rows
        if row['scenario_family'].endswith('test7_overtopping_only_variant')
        and row['scheduler_mode'] == 'strict_global_min_dt'
    )
    assert float(strict_row['stage_rmse']) == 0.0
    assert float(strict_row['discharge_rmse']) == 0.0
    assert float(strict_row['arrival_time_error']) == 0.0
    assert float(strict_row['phase_lag']) == 0.0
    assert float(strict_row['relative_cost_ratio']) == 1.0

    partition_rows = read_csv(chapter_analysis_artifacts / 'summaries' / 'summary_table_test7_partitions.csv')
    assert partition_rows
    assert {'case_name', 'partition', 'max_depth_map_difference', 'arrival_time_map_difference', 'wet_area_iou'}.issubset(partition_rows[0].keys())

    small_rows = read_csv(chapter_analysis_artifacts / 'summaries' / 'summary_table_small_cases.csv')
    families = {row['scenario_family'] for row in small_rows}
    assert {
        'frontal_basin_fill',
        'lateral_overtopping_return',
        'early_arrival_pulse',
        'regime_switch_backwater_or_mixed',
    }.issubset(families)
