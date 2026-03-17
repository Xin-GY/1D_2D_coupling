from __future__ import annotations

from pathlib import Path

from scripts._plot_common import ensure_plot_dir, fixed_interval_rows, interval_label, load_summary_rows, save_figure

import matplotlib.pyplot as plt


def main(root: Path | str = Path('artifacts') / 'coupling_sweep') -> None:
    root = Path(root)
    summary_rows = load_summary_rows(root)
    rows = fixed_interval_rows(summary_rows)
    labels = [interval_label(row['case_name']) for row in rows]
    values = [abs(float(row['peak_stage_error'])) for row in rows]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(labels, values, color='#f28e2b')
    ax.set_title('Peak 1D Stage Error vs Exchange Interval')
    ax.set_xlabel('Interval')
    ax.set_ylabel('Peak Stage Error (m)')
    ax.grid(True, alpha=0.3, axis='y')
    save_figure(fig, ensure_plot_dir(root) / 'peak_stage_error_vs_interval.png')


if __name__ == '__main__':
    main()
