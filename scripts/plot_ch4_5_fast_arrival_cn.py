from __future__ import annotations

# Inputs:
# - artifacts/chapter_coupling_analysis/summaries/summary_table_small_cases.csv
# - artifacts/chapter_coupling_analysis/cases/early_arrival_pulse_*/geometry.json
# - artifacts/chapter_coupling_analysis/cases/early_arrival_pulse_*/stage_timeseries_1d.csv
# - artifacts/chapter_coupling_analysis/cases/early_arrival_pulse_*/stage_timeseries_2d.csv

from pathlib import Path

from scripts._plot_ch4_5_common import (
    SMALL_PROBE_CONFIG,
    choose_small_source_root,
    fixed_interval_rows,
    float_series,
    load_case_json_with_inputs,
    load_case_rows_with_inputs,
    output_roots,
    parse_cli,
    plot_process_compare,
    save_png_pdf,
    scheme_label,
    scheme_style,
    small_case_name,
)
from scripts._plot_common import ensure_plot_dir, load_chapter_small_summary_rows, plt

FAMILY = 'early_arrival_pulse'
ZOOM_SUFFIXES = ['strict_global_min_dt', 'fixed_interval_005s', 'fixed_interval_015s']


def _render_for_root(root: Path) -> None:
    plot_dir = ensure_plot_dir(root)
    source_root, provenance = choose_small_source_root(root)
    case_name = small_case_name(FAMILY, 'fixed_interval_015s')
    geometry, inputs = load_case_json_with_inputs(source_root, case_name, 'geometry.json')
    from scripts._plot_ch4_5_common import draw_case_schematic, print_input_files
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    draw_case_schematic(ax, geometry, title='正向耦合快速首达算例构型及脉冲入流条件示意图')
    save_png_pdf(fig, plot_dir, 'front_fast_arrival_schematic_cn')
    print_input_files('front_fast_arrival_schematic_cn', inputs, provenance=provenance)

    probe_1d, probe_2d = SMALL_PROBE_CONFIG[FAMILY]
    plot_process_compare(
        root,
        source_root,
        FAMILY,
        probe_1d,
        probe_2d,
        ZOOM_SUFFIXES,
        title='正向耦合快速首达算例首达阶段水位过程线局部放大图',
        stem='front_fast_arrival_zoom_cn',
        zoom_xlim=(0.0, 18.0),
    )

    summary_rows = load_chapter_small_summary_rows(source_root)
    rows = fixed_interval_rows(summary_rows, FAMILY)
    fig, axes = plt.subplots(2, 1, figsize=(8.8, 6.8), sharex=True)
    x = [float(row['exchange_interval']) for row in rows]
    y_arr = [float(row['arrival_time_error']) for row in rows]
    y_peak = [float(row['peak_time_error']) for row in rows]
    axes[0].plot(x, y_arr, color='#d62828', marker='o', linewidth=2.0)
    axes[1].plot(x, y_peak, color='#355070', marker='s', linewidth=2.0)
    axes[0].set_xscale('log')
    axes[1].set_xscale('log')
    axes[0].set_ylabel('首达时刻误差 / s')
    axes[1].set_ylabel('峰现时刻误差 / s')
    axes[1].set_xlabel('耦合时间步长 / s')
    axes[0].set_title('首达时刻误差与峰现时刻误差随耦合时间步长变化图')
    axes[0].annotate('该图用于识别首达敏感区间和误差锁定现象', xy=(x[-1], y_arr[-1]), xytext=(-18, 12), textcoords='offset points', ha='right', fontsize=8)
    save_png_pdf(fig, plot_dir, 'front_fast_arrival_timing_error_vs_interval_cn')
    print_input_files('front_fast_arrival_timing_error_vs_interval_cn', [source_root / 'summaries' / 'summary_table_small_cases.csv'], provenance=provenance)


def main(root: Path | str | None = None) -> None:
    for output_root in output_roots(root):
        _render_for_root(Path(output_root))


if __name__ == '__main__':
    cli_roots = parse_cli()
    if len(cli_roots) == 1:
        main(cli_roots[0])
    else:
        main()
