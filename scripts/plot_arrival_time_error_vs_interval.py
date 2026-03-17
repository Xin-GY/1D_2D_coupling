from __future__ import annotations

from pathlib import Path

from scripts._plot_common import ensure_plot_dir, fixed_interval_rows, load_summary_rows, save_figure

import matplotlib.pyplot as plt


def main(root: Path | str = Path('artifacts') / 'coupling_sweep') -> None:
    root = Path(root)
    rows = fixed_interval_rows(load_summary_rows(root))
    labels = [row['case_name'].split('fixed_interval_')[1] for row in rows]
    values = [float(row['arrival_time_diff_vs_reference']) for row in rows]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(labels, values, color='#e15759')
    ax.set_title('Arrival Time Error vs Exchange Interval')
    ax.set_xlabel('Interval')
    ax.set_ylabel('Arrival Time Difference (s)')
    ax.grid(True, alpha=0.3, axis='y')
    save_figure(fig, ensure_plot_dir(root) / 'arrival_time_error_vs_interval.png')


if __name__ == '__main__':
    main()
