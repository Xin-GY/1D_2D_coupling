from __future__ import annotations

# Inputs:
# - artifacts/chapter_coupling_analysis/summaries/summary_table_small_cases.csv
# - artifacts/chapter_coupling_analysis/cases/regime_switch_backwater_or_mixed_*/geometry.json
# - artifacts/chapter_coupling_analysis/cases/regime_switch_backwater_or_mixed_*/stage_timeseries_1d.csv
# - artifacts/chapter_coupling_analysis/cases/regime_switch_backwater_or_mixed_*/stage_timeseries_2d.csv

from pathlib import Path

from scripts._plot_ch4_5_common import (
    SMALL_PROBE_CONFIG,
    choose_small_source_root,
    fixed_interval_rows,
    load_case_json_with_inputs,
    output_roots,
    parse_cli,
    plot_process_compare,
    save_png_pdf,
    small_case_name,
)
from scripts._plot_common import ensure_plot_dir, load_chapter_small_summary_rows, plt

FAMILY = 'regime_switch_backwater_or_mixed'
SUFFIXES = ['strict_global_min_dt', 'fixed_interval_005s', 'fixed_interval_015s', 'fixed_interval_060s', 'fixed_interval_300s']


def _render_for_root(root: Path) -> None:
    plot_dir = ensure_plot_dir(root)
    source_root, provenance = choose_small_source_root(root)
    case_name = small_case_name(FAMILY, 'fixed_interval_015s')
    geometry, inputs = load_case_json_with_inputs(source_root, case_name, 'geometry.json')
    from scripts._plot_ch4_5_common import draw_case_schematic, print_input_files
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    draw_case_schematic(ax, geometry, title='混合耦合回水—流态切换算例构型示意图')
    save_png_pdf(fig, plot_dir, 'mixed_backwater_switch_schematic_cn')
    print_input_files('mixed_backwater_switch_schematic_cn', inputs, provenance=provenance)

    probe_1d, probe_2d = SMALL_PROBE_CONFIG[FAMILY]
    plot_process_compare(
        root,
        source_root,
        FAMILY,
        probe_1d,
        probe_2d,
        SUFFIXES,
        title='不同耦合时间步长下混合耦合回水—流态切换算例水位过程线对比图',
        stem='mixed_backwater_switch_stage_compare_cn',
    )

    summary_rows = load_chapter_small_summary_rows(source_root)
    rows = fixed_interval_rows(summary_rows, FAMILY)
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    x = [float(row['exchange_interval']) for row in rows]
    y = [float(row['phase_lag']) for row in rows]
    ax.plot(x, y, color='#7b2cbf', marker='o', linewidth=2.1)
    ax.set_xscale('log')
    ax.set_xlabel('耦合时间步长 / s')
    ax.set_ylabel('相位差 / s')
    ax.set_title('混合耦合回水—流态切换算例相位差随耦合时间步长变化图')
    ax.grid(True, alpha=0.3)
    save_png_pdf(fig, plot_dir, 'mixed_backwater_switch_phase_lag_vs_interval_cn')
    print_input_files('mixed_backwater_switch_phase_lag_vs_interval_cn', [source_root / 'summaries' / 'summary_table_small_cases.csv'], provenance=provenance)


def main(root: Path | str | None = None) -> None:
    for output_root in output_roots(root):
        _render_for_root(Path(output_root))


if __name__ == '__main__':
    cli_roots = parse_cli()
    if len(cli_roots) == 1:
        main(cli_roots[0])
    else:
        main()
