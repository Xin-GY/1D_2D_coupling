from __future__ import annotations

from pathlib import Path

from scripts._plot_common import chapter_case_rows, ensure_plot_dir, load_chapter_summary_rows, plt, save_figure, series_from_rows


CASE_SUFFIXES = ['strict_global_min_dt', 'yield_schedule', 'fixed_interval_002s', 'fixed_interval_003s', 'fixed_interval_005s', 'fixed_interval_010s', 'fixed_interval_015s', 'fixed_interval_030s', 'fixed_interval_060s', 'fixed_interval_300s']


def _benchmark_family(rows: list[dict[str, str]]) -> str:
    for row in rows:
        if 'test7' in row['scenario_family']:
            return row['scenario_family']
    raise KeyError('No Test7 family found')


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    plot_dir = ensure_plot_dir(root)
    summary_rows = load_chapter_summary_rows(root)
    family = _benchmark_family(summary_rows)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for suffix in CASE_SUFFIXES:
        case_name = f'{family}_{suffix}'
        rows = chapter_case_rows(root, case_name, 'discharge_timeseries.csv')
        x, y = series_from_rows(rows, 'time', 'discharge', filter_key='series_id', filter_value='mainstem_right_q')
        ax.plot(x, y, label=suffix.replace('fixed_interval_', ''))
    ax.set_xlabel('time')
    ax.set_ylabel('Q')
    ax.legend(ncol=5, fontsize=7)
    save_figure(fig, plot_dir / 'discharge_hydrographs_1d.png')


if __name__ == '__main__':
    main()
