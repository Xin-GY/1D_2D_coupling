from __future__ import annotations

# Inputs:
# - artifacts/chapter_coupling_analysis/summaries/summary_table_small_cases.csv
# - artifacts/chapter_coupling_analysis/cases/frontal_basin_fill_*/geometry.json
# - artifacts/chapter_coupling_analysis/cases/frontal_basin_fill_*/stage_timeseries_1d.csv
# - artifacts/chapter_coupling_analysis/cases/frontal_basin_fill_*/stage_timeseries_2d.csv

from pathlib import Path

from scripts._plot_ch4_5_common import (
    SMALL_PROBE_CONFIG,
    SMALL_SWEEP_SUFFIXES,
    choose_small_source_root,
    draw_case_schematic,
    load_case_json_with_inputs,
    output_roots,
    parse_cli,
    plot_process_compare,
    plot_small_rmse,
    save_png_pdf,
    small_case_name,
    small_family_label,
)
from scripts._plot_common import ensure_plot_dir, plt

FAMILY = 'frontal_basin_fill'


def _render_for_root(root: Path) -> None:
    plot_dir = ensure_plot_dir(root)
    source_root, provenance = choose_small_source_root(root)
    case_name = small_case_name(FAMILY, 'fixed_interval_015s')
    geometry, inputs = load_case_json_with_inputs(source_root, case_name, 'geometry.json')
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    draw_case_schematic(ax, geometry, title='正向耦合案例构型及边界条件示意图')
    save_png_pdf(fig, plot_dir, 'front_fill_case_schematic_cn')
    print_inputs = __import__('scripts._plot_ch4_5_common', fromlist=['print_input_files']).print_input_files
    print_inputs('front_fill_case_schematic_cn', inputs, provenance=provenance)

    suffixes = [suffix for suffix in SMALL_SWEEP_SUFFIXES if suffix in {'strict_global_min_dt', 'fixed_interval_002s', 'fixed_interval_005s', 'fixed_interval_015s', 'fixed_interval_060s', 'fixed_interval_300s'}]
    probe_1d, probe_2d = SMALL_PROBE_CONFIG[FAMILY]
    plot_process_compare(
        root,
        source_root,
        FAMILY,
        probe_1d,
        probe_2d,
        suffixes,
        title='不同耦合时间步长下正向耦合案例水位过程线对比图',
        stem='front_fill_stage_compare_cn',
        reference_underlay=True,
        resample_dt=15.0,
    )
    plot_small_rmse(root, FAMILY, stem='front_fill_rmse_vs_interval_cn', title='正向耦合案例水位 RMSE 随耦合时间步长变化图')


def main(root: Path | str | None = None) -> None:
    for output_root in output_roots(root):
        _render_for_root(Path(output_root))


if __name__ == '__main__':
    cli_roots = parse_cli()
    if len(cli_roots) == 1:
        main(cli_roots[0])
    else:
        main()
