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
    ref_rows = chapter_case_rows(root, f'{family}_strict_global_min_dt', 'two_d_field_summary.csv')
    case_rows = chapter_case_rows(root, f'{family}_fixed_interval_015s', 'two_d_field_summary.csv')
    ref_map = {int(row['cell_id']): row for row in ref_rows}
    case_map = {int(row['cell_id']): row for row in case_rows}
    shared = sorted(set(ref_map).intersection(case_map))
    fig, ax = plt.subplots(figsize=(10, 4.5))
    sc = ax.scatter(
        [float(case_map[cell_id]['x']) for cell_id in shared],
        [float(case_map[cell_id]['y']) for cell_id in shared],
        c=[float(case_map[cell_id]['max_depth']) - float(ref_map[cell_id]['max_depth']) for cell_id in shared],
        s=14,
        cmap='coolwarm',
    )
    fig.colorbar(sc, ax=ax, label='max depth difference')
    save_figure(fig, plot_dir / '2d_difference_map.png')


if __name__ == '__main__':
    main()
