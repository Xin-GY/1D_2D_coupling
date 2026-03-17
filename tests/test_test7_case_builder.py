from __future__ import annotations

from pathlib import Path

from experiments.chapter_cases import FIXED_INTERVALS, generate_test7_cases
from experiments.io import read_json
from experiments.test7_data import resolve_test7_data


def test_test7_provenance_falls_back_explicitly_to_surrogate_when_download_disabled():
    provenance = resolve_test7_data(Path('/tmp/test7_case_builder_cache'), allow_download=False)
    assert provenance.case_variant == 'surrogate_test7_overtopping_only_variant'
    assert provenance.source_mode == 'surrogate'
    assert provenance.fallback_reason == 'official_data_not_found_and_download_disabled'


def test_test7_case_builder_keeps_full_interval_matrix_for_paper_profile():
    provenance = resolve_test7_data(Path('/tmp/test7_case_builder_cache_paper'), allow_download=False)
    cases = generate_test7_cases(provenance, profile='paper')
    fixed_intervals = sorted(float(case.exchange_interval) for case in cases if case.exchange_interval is not None)
    assert fixed_intervals == FIXED_INTERVALS
    assert any(case.scheduler_mode == 'strict_global_min_dt' for case in cases)
    assert any(case.scheduler_mode == 'yield_schedule' for case in cases)
    assert all(case.scenario_family == provenance.case_variant for case in cases)


def test_test7_chapter_outputs_include_provenance_and_partitions(chapter_analysis_artifacts):
    summary_rows = read_json(chapter_analysis_artifacts / 'summaries' / 'summary_table.json')
    benchmark_case = next(
        row['case_name']
        for row in summary_rows
        if row['scenario_family'].endswith('test7_overtopping_only_variant')
        and row['scheduler_mode'] == 'strict_global_min_dt'
    )
    provenance = read_json(chapter_analysis_artifacts / 'cases' / benchmark_case / 'provenance.json')
    geometry = read_json(chapter_analysis_artifacts / 'cases' / benchmark_case / 'geometry.json')
    assert provenance['case_variant'].endswith('test7_overtopping_only_variant')
    assert geometry['partitions'].keys() >= {'Floodplain_1', 'Floodplain_2', 'Floodplain_3'}
    assert geometry['lateral_lines'].keys() >= {'fp1_overtop', 'fp2_return', 'fp3_overtop'}
    assert geometry['direct_connection_lines'].keys() >= {'front_main'}
