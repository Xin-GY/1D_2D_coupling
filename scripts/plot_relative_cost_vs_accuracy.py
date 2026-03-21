from __future__ import annotations

import argparse
from pathlib import Path

from scripts._benchmark_1200_cost_common import write_benchmark_1200_cost_summary
from scripts._plot_common import ensure_plot_dir, load_chapter_summary_rows, plt, save_figure

CASE_LABELS = {
    'strict_global_min_dt': '严格同步方案',
    'fixed_interval_002s': '固定步长 2 s',
    'fixed_interval_005s': '固定步长 5 s',
    'fixed_interval_015s': '固定步长 15 s',
    'fixed_interval_060s': '固定步长 60 s',
    'fixed_interval_300s': '固定步长 300 s',
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Render relative cost vs accuracy figure.')
    parser.add_argument('--output-root', default='artifacts/chapter_coupling_analysis')
    parser.add_argument('--rerun-root', default='')
    return parser.parse_args()


def _load_rows(output_root: Path, rerun_root: str):
    if rerun_root:
        csv_path, _, rows = write_benchmark_1200_cost_summary(Path(rerun_root))
        print('cost-accuracy summary source:', csv_path)
        return rows
    rows = load_chapter_summary_rows(output_root)
    benchmark_rows = [row for row in rows if row.get('scenario_family') == 'surrogate_test7_overtopping_only_variant' and 'fixed_interval_' in row['case_name']]
    benchmark_rows.sort(key=lambda row: float(row['exchange_interval']))
    return benchmark_rows


def _suffix(row: dict[str, str]) -> str:
    return row.get('case_suffix') or row['case_name'].split('_')[-1]


def _label(row: dict[str, str]) -> str:
    return CASE_LABELS.get(_suffix(row), row['case_name'])


def main(root: Path | str | None = None, rerun_root: str = '') -> None:
    if root is None:
        args = parse_args()
        output_root = Path(args.output_root)
        rerun_root = args.rerun_root
    else:
        output_root = Path(root)
    rows = _load_rows(output_root, rerun_root)

    fig, ax = plt.subplots(figsize=(7.4, 5.2))
    if rerun_root:
        strict_row = next(row for row in rows if _suffix(row) == 'strict_global_min_dt')
        interval_rows = [row for row in rows if _suffix(row) != 'strict_global_min_dt']
        sc = ax.scatter(
            [float(row['relative_cost_ratio']) for row in interval_rows],
            [float(row['stage_rmse']) for row in interval_rows],
            c=[float(row['exchange_interval']) for row in interval_rows],
            cmap='viridis',
            s=85,
            zorder=3,
            edgecolors='white',
            linewidths=0.8,
        )
        ax.scatter([1.0], [0.0], marker='*', s=190, color='#d62828', edgecolors='white', linewidths=0.9, zorder=4)
        ax.annotate('严格同步方案', (1.0, 0.0), xytext=(8, 8), textcoords='offset points', fontsize=9)
        for row in interval_rows:
            ax.annotate(_label(row), (float(row['relative_cost_ratio']), float(row['stage_rmse'])), xytext=(6, 6), textcoords='offset points', fontsize=8)
        cbar = fig.colorbar(sc, ax=ax)
        cbar.set_label('耦合时间间隔 / s')
    else:
        ax.scatter(
            [float(row['relative_cost_ratio']) for row in rows],
            [float(row['stage_rmse']) for row in rows],
            c=[float(row['exchange_interval']) for row in rows],
            cmap='viridis',
            s=70,
        )
    ax.set_title('综合测试案例相对时间成本与精度关系')
    ax.set_xlabel('相对时间成本比')
    ax.set_ylabel('河道水位 RMSE / m')
    ax.grid(True, linestyle='--', linewidth=0.5, alpha=0.35)
    save_figure(fig, ensure_plot_dir(output_root) / 'relative_cost_vs_accuracy.png')


if __name__ == '__main__':
    main()
