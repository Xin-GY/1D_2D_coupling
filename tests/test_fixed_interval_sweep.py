from __future__ import annotations

from experiments.io import read_csv, read_json


REQUIRED_CASE_FILES = [
    'config.json',
    'exchange_history.csv',
    'mass_balance.csv',
    'stage_timeseries_1d.csv',
    'stage_timeseries_2d.csv',
    'discharge_timeseries.csv',
    'summary_metrics.json',
]


def test_fixed_interval_sweep_outputs_are_complete(coupling_sweep_artifacts):
    interval_case_names = [
        'mixed_bidirectional_pulse_fixed_interval_001s',
        'mixed_bidirectional_pulse_fixed_interval_003s',
        'mixed_bidirectional_pulse_fixed_interval_005s',
        'mixed_bidirectional_pulse_fixed_interval_010s',
        'mixed_bidirectional_pulse_fixed_interval_015s',
        'mixed_bidirectional_pulse_fixed_interval_030s',
        'mixed_bidirectional_pulse_fixed_interval_060s',
        'mixed_bidirectional_pulse_fixed_interval_300s',
    ]
    for case_name in interval_case_names:
        case_dir = coupling_sweep_artifacts / case_name
        assert case_dir.is_dir(), f'missing case directory: {case_name}'
        for filename in REQUIRED_CASE_FILES:
            path = case_dir / filename
            assert path.exists(), f'missing artifact for {case_name}: {filename}'

    summary_rows = read_csv(coupling_sweep_artifacts / 'summary_table.csv')
    summary_json = read_json(coupling_sweep_artifacts / 'summary_table.json')
    summary_case_names = {row['case_name'] for row in summary_rows}
    for case_name in interval_case_names:
        assert case_name in summary_case_names
    assert isinstance(summary_json, list)
    assert len(summary_json) == len(summary_rows)
