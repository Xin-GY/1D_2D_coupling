from __future__ import annotations

from pathlib import Path

from scripts._plot_common import (
    chapter_fixed_interval_rows,
    ensure_plot_dir,
    fixed_interval_rows,
    interval_label,
    load_chapter_summary_rows,
    load_summary_rows,
    save_figure,
)

import matplotlib.pyplot as plt


def _chapter_family(rows: list[dict[str, str]]) -> str:
    for row in rows:
        if 'test7' in row['scenario_family']:
            return row['scenario_family']
    return rows[0]['scenario_family']


def main(root: Path | str = Path('artifacts') / 'coupling_sweep') -> None:
    root = Path(root)
    if (root / 'summaries' / 'summary_table.csv').exists():
        summary_rows = load_chapter_summary_rows(root)
        rows = chapter_fixed_interval_rows(summary_rows, _chapter_family(summary_rows))
        values = [float(row['phase_lag']) for row in rows]
    else:
        rows = fixed_interval_rows(load_summary_rows(root))
        values = [float(row['phase_lag_seconds']) for row in rows]
    labels = [interval_label(row['case_name']) for row in rows]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(labels, values, color='#59a14f')
    ax.set_title('Phase Lag vs Exchange Interval')
    ax.set_xlabel('Interval')
    ax.set_ylabel('Phase Lag (s)')
    ax.grid(True, alpha=0.3, axis='y')
    save_figure(fig, ensure_plot_dir(root) / 'phase_lag_vs_interval.png')


if __name__ == '__main__':
    main()
