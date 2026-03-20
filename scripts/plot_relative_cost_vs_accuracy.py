from __future__ import annotations

from pathlib import Path

from scripts._plot_common import chapter_fixed_interval_rows, ensure_plot_dir, load_chapter_summary_rows, plt, save_figure


def _benchmark_family(rows):
    for row in rows:
        if 'test7' in row['scenario_family']:
            return row['scenario_family']
    raise KeyError('No benchmark family found')


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    rows = load_chapter_summary_rows(root)
    interval_rows = chapter_fixed_interval_rows(rows, _benchmark_family(rows))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(
        [float(row['relative_cost_ratio']) for row in interval_rows],
        [float(row['stage_rmse']) for row in interval_rows],
        c=[float(row['exchange_interval']) for row in interval_rows],
        cmap='viridis',
        s=60,
    )
    ax.set_title('相对成本与精度关系')
    ax.set_xlabel('相对成本比')
    ax.set_ylabel('水位 RMSE')
    save_figure(fig, ensure_plot_dir(root) / 'relative_cost_vs_accuracy.png')


if __name__ == '__main__':
    main()
