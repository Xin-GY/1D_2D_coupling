from __future__ import annotations

from experiments.io import read_csv, read_json


def test_fastest_exact_smoke_covers_frontal_lateral_and_mixed(fastest_exact_smoke_artifacts):
    expected_cases = {
        'frontal_basin_fill_strict_global_min_dt',
        'lateral_overtopping_return_strict_global_min_dt',
        'regime_switch_backwater_or_mixed_strict_global_min_dt',
    }
    cases_root = fastest_exact_smoke_artifacts / 'cases'
    assert expected_cases.issubset({path.name for path in cases_root.iterdir() if path.is_dir()})

    for case_name in expected_cases:
        case_dir = cases_root / case_name
        config = read_json(case_dir / 'config.json')
        timing = read_json(case_dir / 'timing_breakdown.json')
        mass_rows = read_csv(case_dir / 'mass_balance.csv')
        assert config['one_d_backend'] == 'fastest_exact'
        assert timing['wall_clock_seconds'] >= 0.0
        assert mass_rows
        assert (case_dir / 'stage_timeseries_1d.csv').exists()
        assert (case_dir / 'stage_timeseries_2d.csv').exists()
        assert (case_dir / 'exchange_link_timeseries.csv').exists()
