from __future__ import annotations

from pathlib import Path

from scripts._plot_common import chapter_fixed_interval_rows, ensure_plot_dir, interval_label, load_chapter_summary_rows, plt, save_figure


def _benchmark_family(rows):
    for row in rows:
        if 'test7' in row['scenario_family']:
            return row['scenario_family']
    raise KeyError('No benchmark family found')


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    rows = load_chapter_summary_rows(root)
    interval_rows = chapter_fixed_interval_rows(rows, _benchmark_family(rows))
    labels = [interval_label(row['case_name']) for row in interval_rows]
    stage_values = [float(row['peak_stage_error']) for row in interval_rows]
    discharge_values = [float(row['peak_discharge_error']) for row in interval_rows]
    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(labels))
    ax.bar([idx - 0.18 for idx in x], stage_values, width=0.36, label='peak stage error')
    ax.bar([idx + 0.18 for idx in x], discharge_values, width=0.36, label='peak discharge error', color='#e76f51')
    ax.set_xticks(list(x), labels, rotation=45)
    ax.legend()
    save_figure(fig, ensure_plot_dir(root) / 'peak_error_vs_interval.png')


if __name__ == '__main__':
    main()
