from __future__ import annotations

# Inputs:
# - artifacts/chapter_coupling_analysis/summaries/summary_table_small_cases.csv
# - artifacts/chapter_coupling_analysis/cases/lateral_overtopping_return_*/geometry.json
# - artifacts/chapter_coupling_analysis/cases/lateral_overtopping_return_*/stage_timeseries_1d.csv
# - artifacts/chapter_coupling_analysis/cases/lateral_overtopping_return_*/stage_timeseries_2d.csv
# - artifacts/chapter_coupling_analysis/cases/lateral_overtopping_return_*/exchange_link_timeseries.csv

from pathlib import Path

from scripts._plot_ch4_5_common import (
    SMALL_PROBE_CONFIG,
    choose_small_source_root,
    float_series,
    link_label_cn,
    load_case_json_with_inputs,
    load_case_rows_with_inputs,
    output_roots,
    parse_cli,
    plot_process_compare,
    scheme_label,
    scheme_style,
    save_png_pdf,
    small_case_name,
)
from scripts._plot_common import ensure_plot_dir, plt

FAMILY = 'lateral_overtopping_return'
SUFFIXES = ['strict_global_min_dt', 'fixed_interval_002s', 'fixed_interval_005s', 'fixed_interval_015s', 'fixed_interval_060s', 'fixed_interval_300s']
LINK_ID = 'return_link'


def _render_for_root(root: Path) -> None:
    plot_dir = ensure_plot_dir(root)
    source_root, provenance = choose_small_source_root(root)
    case_name = small_case_name(FAMILY, 'fixed_interval_015s')
    geometry, inputs = load_case_json_with_inputs(source_root, case_name, 'geometry.json')
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    from scripts._plot_ch4_5_common import draw_case_schematic, print_input_files
    draw_case_schematic(ax, geometry, title='侧向耦合漫顶—回流算例构型及交换路径示意图')
    save_png_pdf(fig, plot_dir, 'lateral_overtop_return_schematic_cn')
    print_input_files('lateral_overtop_return_schematic_cn', inputs, provenance=provenance)

    probe_1d, probe_2d = SMALL_PROBE_CONFIG[FAMILY]
    plot_process_compare(
        root,
        source_root,
        FAMILY,
        probe_1d,
        probe_2d,
        SUFFIXES,
        title='不同耦合时间间隔下侧向耦合案例水位过程线对比图',
        stem='lateral_overtop_return_stage_compare_cn',
    )

    fig, axes = plt.subplots(2, 1, figsize=(9.0, 6.8), sharex=True)
    input_paths = []
    for suffix in SUFFIXES:
        case_name = small_case_name(FAMILY, suffix)
        rows, paths = load_case_rows_with_inputs(source_root, case_name, 'exchange_link_timeseries.csv')
        input_paths.extend(paths)
        x_q, y_q = float_series(rows, 'time', 'Q_exchange', filter_key='link_id', filter_value=LINK_ID)
        x_d, y_d = float_series(rows, 'time', 'deta', filter_key='link_id', filter_value=LINK_ID)
        axes[0].plot(x_q, y_q, label=scheme_label(suffix), **scheme_style(suffix))
        axes[1].plot(x_d, y_d, label=scheme_label(suffix), **scheme_style(suffix))
    axes[0].set_title('不同耦合时间间隔下侧向耦合案例代表性交换流量与界面水位差时序图')
    axes[0].set_ylabel('交换流量 / m^3/s')
    axes[1].set_ylabel('界面水位差 / m')
    axes[1].set_xlabel('时间 / s')
    axes[0].legend(ncol=3, fontsize=7.5)
    save_png_pdf(fig, plot_dir, 'lateral_overtop_return_exchange_diag_cn')
    print_input_files('lateral_overtop_return_exchange_diag_cn', input_paths, provenance=f'{provenance}; representative_link={link_label_cn(LINK_ID)}')


def main(root: Path | str | None = None) -> None:
    for output_root in output_roots(root):
        _render_for_root(Path(output_root))


if __name__ == '__main__':
    cli_roots = parse_cli()
    if len(cli_roots) == 1:
        main(cli_roots[0])
    else:
        main()
