from __future__ import annotations

from pathlib import Path

from scripts._plot_common import aggregate_exchange_series, case_rows, ensure_plot_dir, load_summary_rows, save_figure, scheduler_case_names

import matplotlib.pyplot as plt


def main(root: Path | str = Path('artifacts') / 'coupling_sweep') -> None:
    root = Path(root)
    summary_rows = load_summary_rows(root)
    fig, ax = plt.subplots(figsize=(10, 5))
    for case_name in scheduler_case_names(summary_rows):
        rows = case_rows(root, case_name, 'exchange_history.csv')
        x, y = aggregate_exchange_series(rows)
        ax.plot(x, y, label=case_name.split('_', 3)[-1])
    ax.set_title('Exchange Discharge Comparison')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Q_exchange (m^3/s)')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    save_figure(fig, ensure_plot_dir(root) / 'q_exchange_compare.png')


if __name__ == '__main__':
    main()
