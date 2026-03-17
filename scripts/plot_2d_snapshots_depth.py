from __future__ import annotations

from pathlib import Path

from scripts._plot_common import chapter_case_rows, ensure_plot_dir, load_chapter_summary_rows, plt, save_figure


COMPARE_SUFFIXES = ['strict_global_min_dt', 'yield_schedule', 'fixed_interval_015s', 'fixed_interval_060s']


def _benchmark_family(rows):
    for row in rows:
        if 'test7' in row['scenario_family']:
            return row['scenario_family']
    raise KeyError('No benchmark family found')


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    plot_dir = ensure_plot_dir(root)
    family = _benchmark_family(load_chapter_summary_rows(root))
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True, sharey=True)
    for ax, suffix in zip(axes.flat, COMPARE_SUFFIXES):
        rows = chapter_case_rows(root, f'{family}_{suffix}', 'two_d_snapshots.csv')
        snap = [row for row in rows if row['snapshot_id'] == 'snapshot_3']
        sc = ax.scatter([float(row['x']) for row in snap], [float(row['y']) for row in snap], c=[float(row['depth']) for row in snap], s=12, cmap='Blues')
        ax.set_title(suffix.replace('fixed_interval_', ''))
    fig.colorbar(sc, ax=axes.ravel().tolist(), label='depth')
    save_figure(fig, plot_dir / '2d_snapshots_depth.png')


if __name__ == '__main__':
    main()
