from __future__ import annotations

from experiments.io import read_csv


def test_chapter_exchange_link_diagnostics_are_present_and_conservative(chapter_analysis_artifacts):
    summary_rows = read_csv(chapter_analysis_artifacts / 'summaries' / 'exchange_link_summary.csv')
    assert summary_rows
    required_columns = {
        'case_name',
        'scenario_family',
        'link_id',
        'link_type',
        'exchange_event_count',
        'peak_Q_exchange',
        'cumulative_exchange_volume',
        'sign_flip_count',
        'mean_deta',
        'first_exchange_time',
        'link_mass_closure_error',
    }
    for row in summary_rows:
        assert required_columns.issubset(row.keys())
        assert float(row['exchange_event_count']) >= 0.0
        assert float(row['cumulative_exchange_volume']) >= 0.0
        assert float(row['link_mass_closure_error']) >= 0.0

    benchmark_fixed = next(
        row['case_name']
        for row in read_csv(chapter_analysis_artifacts / 'summaries' / 'summary_table.csv')
        if 'test7' in row['scenario_family'] and row['case_name'].endswith('fixed_interval_015s')
    )
    link_rows = read_csv(chapter_analysis_artifacts / 'cases' / benchmark_fixed / 'exchange_link_timeseries.csv')
    assert link_rows
    assert {'time', 'link_id', 'Q_exchange', 'deta', 'dV_exchange', 'cumulative_dV', 'eta_1d', 'eta_2d', 'mode', 'iteration_count'}.issubset(link_rows[0].keys())
    assert any('front' in row['link_id'] for row in link_rows)
    assert any('fp' in row['link_id'] for row in link_rows)
