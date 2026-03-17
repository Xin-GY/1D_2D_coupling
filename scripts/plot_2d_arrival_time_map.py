from __future__ import annotations

from pathlib import Path

from scripts._plot_common import chapter_case_rows, ensure_plot_dir, load_chapter_summary_rows, plt, save_figure


def _benchmark_family(rows):
    for row in rows:
        if 'test7' in row['scenario_family']:
            return row['scenario_family']
    raise KeyError('No benchmark family found')


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    plot_dir = ensure_plot_dir(root)
    family = _benchmark_family(load_chapter_summary_rows(root))
    rows = chapter_case_rows(root, f'{family}_strict_global_min_dt', 'two_d_field_summary.csv')
    fig, ax = plt.subplots(figsize=(10, 4.5))
    sc = ax.scatter([float(row['x']) for row in rows], [float(row['y']) for row in rows], c=[float(row['arrival_time']) if row['arrival_time'] != '' else float('nan') for row in rows], s=14, cmap='plasma')
    fig.colorbar(sc, ax=ax, label='arrival time')
    save_figure(fig, plot_dir / '2d_arrival_time_map.png')


if __name__ == '__main__':
    main()
