from __future__ import annotations

from experiments.chapter_cases import generate_small_mechanism_cases
from experiments.io import read_csv


EXPECTED_FAMILIES = {
    'frontal_basin_fill',
    'lateral_overtopping_return',
    'early_arrival_pulse',
    'regime_switch_backwater_or_mixed',
}


def test_small_mechanism_case_builder_covers_all_required_families():
    cases = generate_small_mechanism_cases(profile='paper')
    families = {case.scenario_family for case in cases}
    assert EXPECTED_FAMILIES == families
    for family in EXPECTED_FAMILIES:
        family_cases = [case for case in cases if case.scenario_family == family]
        assert any(case.scheduler_mode == 'strict_global_min_dt' for case in family_cases)
        assert any(case.scheduler_mode == 'yield_schedule' for case in family_cases)
        assert any(case.exchange_interval == 0.5 for case in family_cases)
        assert any(case.exchange_interval == 300.0 for case in family_cases)


def test_small_mechanism_chapter_outputs_exist(chapter_analysis_artifacts):
    summary_rows = read_csv(chapter_analysis_artifacts / 'summaries' / 'summary_table_small_cases.csv')
    families = {row['scenario_family'] for row in summary_rows}
    assert EXPECTED_FAMILIES.issubset(families)

    for family in EXPECTED_FAMILIES:
        strict_case = next(row['case_name'] for row in summary_rows if row['scenario_family'] == family and row['scheduler_mode'] == 'strict_global_min_dt')
        case_dir = chapter_analysis_artifacts / 'cases' / strict_case
        assert (case_dir / 'stage_timeseries_1d.csv').exists()
        assert (case_dir / 'stage_timeseries_2d.csv').exists()
        assert (case_dir / 'exchange_link_timeseries.csv').exists()
