from __future__ import annotations

from pathlib import Path

from scripts._plot_common import ensure_plot_dir, fixed_interval_rows, load_summary_rows, save_figure

import matplotlib.pyplot as plt


def main(root: Path | str = Path('artifacts') / 'coupling_sweep') -> None:
    root = Path(root)
    summary_rows = load_summary_rows(root)
    reference = next(row for row in summary_rows if row['case_name'] == 'mixed_bidirectional_pulse_strict_global_min_dt')
    rows = fixed_interval_rows(summary_rows)
    labels = [row['case_name'].split('fixed_interval_')[1] for row in rows]
    values = [abs(float(row['peak_stage_1d']) - float(reference['peak_stage_1d'])) for row in rows]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(labels, values, color='#f28e2b')
    ax.set_title('Peak 1D Stage Error vs Exchange Interval')
    ax.set_xlabel('Interval')
    ax.set_ylabel('Peak Stage Error (m)')
    ax.grid(True, alpha=0.3, axis='y')
    save_figure(fig, ensure_plot_dir(root) / 'peak_stage_error_vs_interval.png')


if __name__ == '__main__':
    main()
