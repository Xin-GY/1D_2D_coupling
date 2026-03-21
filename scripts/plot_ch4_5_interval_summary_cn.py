from __future__ import annotations

# Inputs:
# - artifacts/chapter_coupling_analysis_fastest_exact/summaries/summary_table.csv
# - artifacts/chapter_coupling_analysis/summaries/summary_table_small_cases.csv

from pathlib import Path

from scripts._plot_ch4_5_common import (
    BENCHMARK_LABEL,
    FASTEST_ROOT,
    LEGACY_ROOT,
    SMALL_FAMILY_LABELS,
    fixed_interval_rows,
    output_roots,
    parse_cli,
    print_input_files,
    save_png_pdf,
)
from scripts._plot_common import load_chapter_small_summary_rows, load_chapter_summary_rows, plt

BENCHMARK_FAMILY = 'surrogate_test7_overtopping_only_variant'
COLORS = {
    'frontal_basin_fill': '#1d3557',
    'lateral_overtopping_return': '#2a9d8f',
    'early_arrival_pulse': '#d62828',
    'regime_switch_backwater_or_mixed': '#7b2cbf',
    BENCHMARK_FAMILY: '#111111',
}


def _plot_metric(output_root: Path, metric_key: str, ylabel: str, stem: str, title: str, *, annotate_arrival: bool = False) -> None:
    bench_rows = fixed_interval_rows(load_chapter_summary_rows(FASTEST_ROOT), BENCHMARK_FAMILY)
    small_rows = load_chapter_small_summary_rows(LEGACY_ROOT)
    fig, ax = plt.subplots(figsize=(9.2, 5.2))

    x = [float(row['exchange_interval']) for row in bench_rows]
    y = [float(row[metric_key]) for row in bench_rows]
    ax.plot(x, y, color=COLORS[BENCHMARK_FAMILY], marker='o', linewidth=2.5, label=BENCHMARK_LABEL)

    for family, label in SMALL_FAMILY_LABELS.items():
        rows = fixed_interval_rows(small_rows, family)
        if not rows:
            continue
        x = [float(row['exchange_interval']) for row in rows]
        y = [float(row[metric_key]) for row in rows]
        ax.plot(x, y, color=COLORS[family], marker='o', linewidth=1.9, label=label)

    ax.set_xscale('log')
    ax.set_xlabel('耦合时间步长 / s')
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7.5, ncol=2)
    if metric_key == 'stage_rmse':
        ax.axvspan(3.0, 5.0, color='#fee8c8', alpha=0.35, zorder=0)
        ax.text(3.6, ax.get_ylim()[1] * 0.88, '推荐区间 3–5 s', fontsize=8, color='#8c4f2c')
    if annotate_arrival:
        ax.annotate('综合算例的主要差异不集中在首达时刻', xy=(300.0, 0.0), xytext=(-10, 18), textcoords='offset points', ha='right', fontsize=8)
    save_png_pdf(fig, output_root / 'plots', stem)
    print_input_files(stem, [FASTEST_ROOT / 'summaries' / 'summary_table.csv', LEGACY_ROOT / 'summaries' / 'summary_table_small_cases.csv'], provenance=f'metric={metric_key}')


def _render_for_root(output_root: Path) -> None:
    _plot_metric(output_root, 'stage_rmse', '水位 RMSE / m', 'rmse_vs_interval_cn', '不同测试算例水位 RMSE 随耦合时间步长变化图')
    _plot_metric(output_root, 'phase_lag', '相位差 / s', 'phase_lag_vs_interval_cn', '不同测试算例相位差随耦合时间步长变化图')
    _plot_metric(output_root, 'arrival_time_error', '首达时刻误差 / s', 'arrival_time_error_vs_interval_cn', '不同测试算例首达时刻误差随耦合时间步长变化图', annotate_arrival=True)


def main(root: Path | str | None = None) -> None:
    for output_root in output_roots(root):
        _render_for_root(Path(output_root))


if __name__ == '__main__':
    cli_roots = parse_cli()
    if len(cli_roots) == 1:
        main(cli_roots[0])
    else:
        main()
