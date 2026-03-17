from __future__ import annotations

from pathlib import Path

from scripts._plot_common import ensure_plot_dir, fixed_interval_rows, interval_label, load_summary_rows, save_figure

import matplotlib.pyplot as plt


def main(root: Path | str = Path('artifacts') / 'coupling_sweep') -> None:
    root = Path(root)
    rows = fixed_interval_rows(load_summary_rows(root))
    labels = [interval_label(row['case_name']) for row in rows]
    values = [float(row['wall_clock_seconds']) for row in rows]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(labels, values, color='#76b7b2')
    ax.set_title('Runtime vs Exchange Interval')
    ax.set_xlabel('Interval')
    ax.set_ylabel('Wall Clock (s)')
    ax.grid(True, alpha=0.3, axis='y')
    save_figure(fig, ensure_plot_dir(root) / 'runtime_vs_interval.png')


if __name__ == '__main__':
    main()
