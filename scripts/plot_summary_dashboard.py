from __future__ import annotations

from pathlib import Path

from scripts._plot_common import ensure_plot_dir, fixed_interval_rows, interval_label, load_summary_rows, save_figure

import matplotlib.pyplot as plt


def main(root: Path | str = Path('artifacts') / 'coupling_sweep') -> None:
    root = Path(root)
    summary_rows = load_summary_rows(root)
    interval_rows = fixed_interval_rows(summary_rows)
    labels = [interval_label(row['case_name']) for row in interval_rows]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    axes = axes.ravel()

    axes[0].bar(labels, [float(row['RMSE_stage_vs_reference']) for row in interval_rows])
    axes[0].set_title('RMSE')

    axes[1].bar(labels, [float(row['wall_clock_seconds']) for row in interval_rows], color='#76b7b2')
    axes[1].set_title('Runtime')

    axes[2].bar(labels, [abs(float(row['final_total_mass_error'])) for row in interval_rows], color='#e15759')
    axes[2].set_title('Final Mass Error')

    axes[3].bar(labels, [float(row['phase_lag_seconds']) for row in interval_rows], color='#59a14f')
    axes[3].set_title('Phase Lag')

    for ax in axes:
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3, axis='y')

    save_figure(fig, ensure_plot_dir(root) / 'summary_dashboard.png')


if __name__ == '__main__':
    main()
