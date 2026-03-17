from __future__ import annotations

from pathlib import Path

from experiments.io import read_csv
from scripts._plot_common import load_chapter_summary_rows, load_mesh_geometry_for_case


def _benchmark_case_name(root: Path) -> str:
    rows = load_chapter_summary_rows(root)
    return next(
        row['case_name']
        for row in rows
        if 'test7' in row['scenario_family'] and row['scheduler_mode'] == 'strict_global_min_dt'
    )


def test_plot_geometry_cache_supports_rendering_without_msh(chapter_analysis_artifacts: Path):
    assert not any(chapter_analysis_artifacts.rglob('*.msh')), 'test fixture should not depend on .msh files'
    case_name = _benchmark_case_name(chapter_analysis_artifacts)
    geometry = load_mesh_geometry_for_case(chapter_analysis_artifacts, case_name)
    assert geometry['triangles'].shape[0] > 0
    assert geometry['vertices'].shape[0] > 0
    cache_dir = chapter_analysis_artifacts / 'cases' / case_name / 'plot_cache'
    assert (cache_dir / 'mesh_geometry.npz').exists()
    assert (cache_dir / 'mesh_geometry.json').exists()


def test_plot_geometry_cache_index_covers_chapter_cases(chapter_analysis_artifacts: Path):
    rows = read_csv(chapter_analysis_artifacts / 'logs' / 'plot_geometry_cache_index.csv')
    assert rows
    benchmark_case = _benchmark_case_name(chapter_analysis_artifacts)
    assert any(row['case_name'] == benchmark_case for row in rows)
