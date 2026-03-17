from __future__ import annotations

from pathlib import Path

from scripts._plot_common import ensure_plot_dir, load_summary_rows, save_figure

import matplotlib.pyplot as plt


def main(root: Path | str = Path('artifacts') / 'coupling_sweep') -> None:
    root = Path(root)
    rows = [
        row
        for row in load_summary_rows(root)
        if row['case_name'].endswith('river_to_floodplain_quasi_steady_strict_global_min_dt')
    ]
    rows = sorted(rows, key=lambda row: row['case_name'])
    labels = [row['case_name'].split('_river_to_floodplain')[0] for row in rows]
    peak_1d = [float(row['peak_stage_1d']) for row in rows]
    peak_2d = [float(row['peak_stage_2d']) for row in rows]
    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar([idx - 0.15 for idx in x], peak_1d, width=0.3, label='Peak 1D Stage')
    ax.bar([idx + 0.15 for idx in x], peak_2d, width=0.3, label='Peak 2D Stage')
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_title('Coupling Type Comparison')
    ax.set_ylabel('Peak Stage (m)')
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend()
    save_figure(fig, ensure_plot_dir(root) / 'coupling_type_compare.png')


if __name__ == '__main__':
    main()
