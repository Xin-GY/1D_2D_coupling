from __future__ import annotations

from pathlib import Path

from scripts._plot_common import chapter_fixed_interval_rows, ensure_plot_dir, load_chapter_summary_rows, plt, save_figure


def _benchmark_family(rows):
    for row in rows:
        if 'test7' in row['scenario_family']:
            return row['scenario_family']
    raise KeyError('No benchmark family found')


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    rows = load_chapter_summary_rows(root)
    interval_rows = chapter_fixed_interval_rows(rows, _benchmark_family(rows))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    axes[0].plot([float(row['interval_over_t_arr_ref']) for row in interval_rows], [float(row['arrival_time_error']) for row in interval_rows], marker='o')
    axes[0].set_xlabel('Δt_ex / t_arr_ref')
    axes[0].set_ylabel('arrival error')
    axes[1].plot([float(row['interval_over_t_rise_ref']) for row in interval_rows], [float(row['peak_stage_error']) for row in interval_rows], marker='o', color='#b56576')
    axes[1].set_xlabel('Δt_ex / t_rise_ref')
    axes[1].set_ylabel('peak stage error')
    save_figure(fig, ensure_plot_dir(root) / 'interval_normalized_axes.png')


if __name__ == '__main__':
    main()
