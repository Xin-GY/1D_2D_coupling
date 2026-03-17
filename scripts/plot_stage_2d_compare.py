from __future__ import annotations

from pathlib import Path

from scripts._plot_common import case_rows, ensure_plot_dir, load_summary_rows, save_figure, scheduler_case_names, series_from_rows

import matplotlib.pyplot as plt


def main(root: Path | str = Path('artifacts') / 'coupling_sweep') -> None:
    root = Path(root)
    summary_rows = load_summary_rows(root)
    fig, ax = plt.subplots(figsize=(10, 5))
    for case_name in scheduler_case_names(summary_rows):
        rows = case_rows(root, case_name, 'stage_timeseries_2d.csv')
        x, y = series_from_rows(rows, 'time', 'stage', filter_key='control_id', filter_value='floodplain_probe')
        ax.plot(x, y, label=case_name.split('_', 3)[-1])
    ax.set_title('2D Stage Comparison')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Stage (m)')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    save_figure(fig, ensure_plot_dir(root) / 'stage_2d_compare.png')


if __name__ == '__main__':
    main()
