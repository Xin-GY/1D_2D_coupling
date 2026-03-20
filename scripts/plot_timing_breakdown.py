from __future__ import annotations

from pathlib import Path

from scripts._plot_common import ensure_plot_dir, load_csv_rows, save_figure

import matplotlib.pyplot as plt


def main(root: Path | str = Path('artifacts') / 'coupling_sweep') -> None:
    root = Path(root)
    rows = load_csv_rows(root / 'timing_breakdown.csv')
    labels = [row['case_label'] for row in rows]
    categories = [
        ('one_d_advance_time', '#4e79a7', '一维推进'),
        ('two_d_gpu_kernel_time', '#f28e2b', '二维 GPU 核函数'),
        ('boundary_update_time', '#e15759', '边界更新'),
        ('gpu_inlets_apply_time', '#76b7b2', 'GPU inlet 应用'),
        ('scheduler_manager_overhead', '#59a14f', '调度与管理开销'),
    ]
    fig, ax = plt.subplots(figsize=(10, 5))
    bottoms = [0.0] * len(labels)
    for key, color, display_name in categories:
        values = [float(row[key]) for row in rows]
        ax.bar(labels, values, bottom=bottoms, label=display_name, color=color)
        bottoms = [bottom + value for bottom, value in zip(bottoms, values)]
    ax.set_title('耗时分解')
    ax.set_ylabel('耗时 (s)')
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend(fontsize=8)
    save_figure(fig, ensure_plot_dir(root) / 'timing_breakdown.png')


if __name__ == '__main__':
    main()
