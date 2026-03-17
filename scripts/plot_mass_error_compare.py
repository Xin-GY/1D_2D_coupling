from __future__ import annotations

from pathlib import Path

from scripts._plot_common import case_rows, ensure_plot_dir, load_summary_rows, save_figure, scheduler_case_names, series_from_rows

import matplotlib.pyplot as plt


def main(root: Path | str = Path('artifacts') / 'coupling_sweep') -> None:
    root = Path(root)
    summary_rows = load_summary_rows(root)
    fig, ax = plt.subplots(figsize=(10, 5))
    for case_name in scheduler_case_names(summary_rows):
        rows = case_rows(root, case_name, 'mass_balance.csv')
        x, y = series_from_rows(rows, 'time', 'system_mass_error')
        ax.plot(x, y, label=case_name.split('_', 3)[-1])
    ax.set_title('Mass Error Comparison')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('System Mass Error (m^3)')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    save_figure(fig, ensure_plot_dir(root) / 'mass_error_compare.png')


if __name__ == '__main__':
    main()
