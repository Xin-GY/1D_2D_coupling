from __future__ import annotations

from pathlib import Path

from scripts._plot_common import ensure_plot_dir, load_mesh_summary_rows, save_figure

import matplotlib.pyplot as plt


def main(root: Path | str = Path('artifacts') / 'coupling_sweep') -> None:
    root = Path(root)
    rows = load_mesh_summary_rows(root)
    labels = [row['case_name'] for row in rows]
    values = [float(row['wall_clock_seconds']) for row in rows]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(labels, values, color='#76b7b2')
    ax.set_title('Mesh Sensitivity: Runtime')
    ax.set_ylabel('Wall Clock (s)')
    ax.tick_params(axis='x', rotation=25)
    ax.grid(True, alpha=0.3, axis='y')
    save_figure(fig, ensure_plot_dir(root) / 'mesh_sensitivity_runtime.png')


if __name__ == '__main__':
    main()
