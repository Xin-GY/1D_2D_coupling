from __future__ import annotations

from pathlib import Path

from scripts._plot_common import ensure_plot_dir, load_csv_rows, save_figure

import matplotlib.pyplot as plt


def main(root: Path | str = Path('artifacts') / 'coupling_sweep') -> None:
    root = Path(root)
    rows = load_csv_rows(root / 'timing_breakdown.csv')
    labels = [row['case_label'] for row in rows]
    categories = [
        ('one_d_advance_time', '#4e79a7'),
        ('two_d_gpu_kernel_time', '#f28e2b'),
        ('boundary_update_time', '#e15759'),
        ('gpu_inlets_apply_time', '#76b7b2'),
        ('scheduler_manager_overhead', '#59a14f'),
    ]
    fig, ax = plt.subplots(figsize=(10, 5))
    bottoms = [0.0] * len(labels)
    for key, color in categories:
        values = [float(row[key]) for row in rows]
        ax.bar(labels, values, bottom=bottoms, label=key, color=color)
        bottoms = [bottom + value for bottom, value in zip(bottoms, values)]
    ax.set_title('Timing Breakdown')
    ax.set_ylabel('Seconds')
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend(fontsize=8)
    save_figure(fig, ensure_plot_dir(root) / 'timing_breakdown.png')


if __name__ == '__main__':
    main()
