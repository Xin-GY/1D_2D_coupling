from __future__ import annotations

from pathlib import Path

from scripts._plot_common import chapter_case_json, chapter_case_rows, ensure_plot_dir, load_chapter_summary_rows, plt, save_figure


def _benchmark_family(rows: list[dict[str, str]]) -> str:
    for row in rows:
        if 'test7' in row['scenario_family']:
            return row['scenario_family']
    raise KeyError('No Test7 family found')


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    plot_dir = ensure_plot_dir(root)
    family = _benchmark_family(load_chapter_summary_rows(root))
    rows = chapter_case_rows(root, f'{family}_fixed_interval_015s', 'exchange_link_timeseries.csv')
    crossings = chapter_case_rows(root, f'{family}_fixed_interval_015s', 'crossing_diagnostics.csv')
    ref_cross = next(row for row in crossings if row['series_id'].endswith('_reference'))
    candidate_cross = next(row for row in crossings if row['series_id'].endswith('_candidate'))
    times = sorted({float(row['time']) for row in rows})
    fig, ax = plt.subplots(figsize=(9, 3.8))
    for time_value in times:
        ax.axvline(time_value, color='#355070', alpha=0.25)
    ax.axvline(float(ref_cross['crossing_time_interp']), color='#d62828', lw=2, label='reference arrival')
    ax.axvline(float(candidate_cross['crossing_time_interp']), color='#2a9d8f', lw=2, label='candidate arrival')
    ax.set_ylim(0.0, 1.0)
    ax.set_yticks([])
    ax.legend()
    ax.set_xlabel('time')
    save_figure(fig, plot_dir / 'exchange_event_alignment.png')


if __name__ == '__main__':
    main()
