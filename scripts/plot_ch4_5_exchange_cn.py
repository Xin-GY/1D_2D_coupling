from __future__ import annotations

# Inputs:
# - artifacts/chapter_coupling_analysis_fastest_exact/cases/<benchmark>/exchange_link_timeseries.csv

from pathlib import Path
import numpy as np

from scripts._plot_ch4_5_common import (
    BENCHMARK_EXCHANGE_SUFFIXES,
    benchmark_case_name,
    link_label_cn,
    output_roots,
    parse_cli,
    print_input_files,
    save_png_pdf,
    scheme_label,
    scheme_style,
)
from scripts._plot_common import chapter_case_rows, ensure_plot_dir, plt

ROOT = Path('artifacts/chapter_coupling_analysis_fastest_exact')
LINKS = ['fp1_overtop', 'fp2_return', 'front_main']


def _render_for_root(output_root: Path) -> None:
    plot_dir = ensure_plot_dir(output_root)
    rows_by_suffix = {}
    input_paths = []
    for suffix in BENCHMARK_EXCHANGE_SUFFIXES:
        case_name = benchmark_case_name(ROOT, suffix)
        input_paths.append(ROOT / 'cases' / case_name / 'exchange_link_timeseries.csv')
        rows_by_suffix[suffix] = chapter_case_rows(ROOT, case_name, 'exchange_link_timeseries.csv')

    fig, axes = plt.subplots(len(LINKS), 1, figsize=(9.2, 7.8), sharex=True)
    for ax, link_id in zip(axes, LINKS):
        for suffix in BENCHMARK_EXCHANGE_SUFFIXES:
            rows = [row for row in rows_by_suffix[suffix] if row['link_id'] == link_id]
            pairs = sorted((float(r['time']), float(r['Q_exchange'])) for r in rows)
            ax.plot([x for x, _ in pairs], [y for _, y in pairs], label=scheme_label(suffix), **scheme_style(suffix))
        ax.set_ylabel(f'{link_label_cn(link_id)}\n交换流量 / m^3/s')
    axes[0].set_title('河道—三分区洪泛平原综合算例代表性链路交换流量时序图')
    axes[0].legend(ncol=2, fontsize=7.2)
    axes[-1].set_xlabel('时间 / s')
    save_png_pdf(fig, plot_dir, 'exchange_q_timeseries_cn')
    print_input_files('exchange_q_timeseries_cn', input_paths, provenance=f'source_root={ROOT}')

    fig, axes = plt.subplots(len(LINKS), 1, figsize=(9.2, 7.8), sharex=True)
    for ax, link_id in zip(axes, LINKS):
        for suffix in BENCHMARK_EXCHANGE_SUFFIXES:
            rows = [row for row in rows_by_suffix[suffix] if row['link_id'] == link_id]
            pairs = sorted((float(r['time']), float(r['deta'])) for r in rows)
            ax.plot([x for x, _ in pairs], [y for _, y in pairs], label=scheme_label(suffix), **scheme_style(suffix))
        ax.axhline(0.0, color='0.7', linewidth=1.0)
        ax.set_ylabel(f'{link_label_cn(link_id)}\n界面水位差 / m')
    axes[0].set_title('河道—三分区洪泛平原综合算例代表性链路界面水位差时序图')
    axes[0].legend(ncol=2, fontsize=7.2)
    axes[-1].set_xlabel('时间 / s')
    save_png_pdf(fig, plot_dir, 'exchange_deta_timeseries_cn')
    print_input_files('exchange_deta_timeseries_cn', input_paths, provenance=f'source_root={ROOT}')

    fig, axes = plt.subplots(len(LINKS), 1, figsize=(9.2, 7.8), sharex=True)
    for ax, link_id in zip(axes, LINKS):
        for suffix in BENCHMARK_EXCHANGE_SUFFIXES:
            rows = [row for row in rows_by_suffix[suffix] if row['link_id'] == link_id]
            pairs = sorted((float(r['time']), float(r['dV_exchange'])) for r in rows)
            times = [x for x, _ in pairs]
            cumulative = np.cumsum([y for _, y in pairs])
            ax.plot(times, cumulative, label=scheme_label(suffix), **scheme_style(suffix))
        ax.set_ylabel(f'{link_label_cn(link_id)}\n累计交换体积 / m^3')
    axes[0].set_title('河道—三分区洪泛平原综合算例代表性链路累计交换体积图')
    axes[0].legend(ncol=2, fontsize=7.2)
    axes[-1].set_xlabel('时间 / s')
    save_png_pdf(fig, plot_dir, 'exchange_volume_cumulative_cn')
    print_input_files('exchange_volume_cumulative_cn', input_paths, provenance='各方案均保持质量闭合，差异主要来自交换事件时间分配方式')


def main(root: Path | str | None = None) -> None:
    for output_root in output_roots(root):
        _render_for_root(Path(output_root))


if __name__ == '__main__':
    cli_roots = parse_cli()
    if len(cli_roots) == 1:
        main(cli_roots[0])
    else:
        main()
