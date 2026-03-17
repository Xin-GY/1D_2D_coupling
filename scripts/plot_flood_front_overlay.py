from __future__ import annotations

from pathlib import Path

from scripts._plot_common import chapter_case_rows, ensure_plot_dir, load_chapter_summary_rows, plt, save_figure


def _benchmark_family(rows):
    for row in rows:
        if 'test7' in row['scenario_family']:
            return row['scenario_family']
    raise KeyError('No benchmark family found')


def _wet_points(rows, snapshot_id: str, depth_threshold: float = 0.02):
    snapshot = [row for row in rows if row['snapshot_id'] == snapshot_id and float(row['depth']) >= depth_threshold]
    return [float(row['x']) for row in snapshot], [float(row['y']) for row in snapshot]


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    plot_dir = ensure_plot_dir(root)
    family = _benchmark_family(load_chapter_summary_rows(root))
    ref_rows = chapter_case_rows(root, f'{family}_strict_global_min_dt', 'two_d_snapshots.csv')
    case_rows = chapter_case_rows(root, f'{family}_fixed_interval_015s', 'two_d_snapshots.csv')
    fig, ax = plt.subplots(figsize=(10, 4.5))
    for snapshot_id, color in [('snapshot_1', '#355070'), ('snapshot_2', '#6d597a'), ('snapshot_3', '#b56576')]:
        x_ref, y_ref = _wet_points(ref_rows, snapshot_id)
        x_case, y_case = _wet_points(case_rows, snapshot_id)
        ax.scatter(x_ref, y_ref, s=8, alpha=0.25, color=color, label=f'{snapshot_id} ref')
        ax.scatter(x_case, y_case, s=10, facecolors='none', edgecolors=color, linewidths=0.7, label=f'{snapshot_id} 15s')
    ax.legend(ncol=3, fontsize=7)
    save_figure(fig, plot_dir / 'flood_front_overlay.png')


if __name__ == '__main__':
    main()
