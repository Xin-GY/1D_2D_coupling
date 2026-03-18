from __future__ import annotations

from pathlib import Path

from scripts._plot_common import (
    axis_limits_with_padding,
    chapter_fixed_interval_rows,
    ensure_plot_dir,
    fixed_interval_rows,
    interval_label,
    load_chapter_summary_rows,
    load_summary_rows,
    save_figure,
)

import matplotlib.pyplot as plt


def _chapter_family(rows: list[dict[str, str]]) -> str:
    for row in rows:
        if 'test7' in row['scenario_family']:
            return row['scenario_family']
    return rows[0]['scenario_family']


def main(root: Path | str = Path('artifacts') / 'coupling_sweep') -> None:
    root = Path(root)
    if (root / 'summaries' / 'summary_table.csv').exists():
        summary_rows = load_chapter_summary_rows(root)
        rows = chapter_fixed_interval_rows(summary_rows, _chapter_family(summary_rows))
        values = [float(row['arrival_time_error']) for row in rows]
    else:
        rows = fixed_interval_rows(load_summary_rows(root))
        values = [float(row['arrival_time_diff_vs_reference']) for row in rows]
    labels = [interval_label(row['case_name']) for row in rows]
    x = list(range(len(labels)))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(
        x,
        values,
        color='#e15759',
        marker='o',
        linewidth=2.0,
        markersize=6.5,
        markerfacecolor='white',
        markeredgewidth=1.8,
    )
    ax.axhline(0.0, color='0.55', linewidth=1.0, linestyle='--', zorder=0)
    ax.set_xticks(x, labels)
    ax.set_ylim(*axis_limits_with_padding(values, min_pad=0.25))
    ax.set_title('Arrival Time Error vs Exchange Interval')
    ax.set_xlabel('Interval')
    ax.set_ylabel('Arrival Time Difference (s)')
    if max(values) - min(values) <= 1.0e-12:
        ax.annotate(
            f'benchmark series collapses to {values[0]:.3f} s',
            xy=(x[-1] if x else 0, values[-1] if values else 0.0),
            xytext=(-8, 12),
            textcoords='offset points',
            ha='right',
            fontsize=9,
            color='#444444',
        )
    ax.grid(True, alpha=0.3, axis='y')
    save_figure(fig, ensure_plot_dir(root) / 'arrival_time_error_vs_interval.png')


if __name__ == '__main__':
    main()
