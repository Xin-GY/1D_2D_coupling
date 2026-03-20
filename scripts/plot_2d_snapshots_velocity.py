from __future__ import annotations

from pathlib import Path

from scripts._plot_common import (
    assert_nonempty_dataframe,
    assert_required_columns,
    build_snapshot_value_array,
    case_label,
    chapter_case_rows,
    ensure_plot_dir,
    load_chapter_summary_rows,
    load_mesh_geometry_for_case,
    plt,
    render_scalar_field_on_mesh,
    save_figure,
    shared_color_limits,
)


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
    case_names = [f'{family}_{suffix}' for suffix in COMPARE_SUFFIXES]
    geometry_by_case = {case_name: load_mesh_geometry_for_case(root, case_name) for case_name in case_names}
    rows_by_case = {case_name: chapter_case_rows(root, case_name, 'two_d_snapshots.csv') for case_name in case_names}
    arrays = []
    for case_name, rows in rows_by_case.items():
        assert_nonempty_dataframe(rows, f'two_d_snapshots for {case_name}')
        assert_required_columns(rows, ('snapshot_id', 'cell_id', 'velocity'), f'two_d_snapshots for {case_name}')
        arrays.append(
            build_snapshot_value_array(
                rows,
                'snapshot_3',
                'velocity',
                expected_cells=int(geometry_by_case[case_name]['triangles'].shape[0]),
            )
        )
    limits = shared_color_limits(arrays)
    sc = None
    for ax, suffix, case_name, values in zip(axes.flat, COMPARE_SUFFIXES, case_names, arrays):
        rows = rows_by_case[case_name]
        snapshot_rows = [row for row in rows if row['snapshot_id'] == 'snapshot_3']
        snapshot_time = float(snapshot_rows[0]['time'])
        sc = render_scalar_field_on_mesh(
            ax,
            geometry_by_case[case_name],
            values,
            cmap='viridis',
            limits=limits,
            label=f"{case_label(suffix)} | t={snapshot_time:.1f} s",
        )
    fig.suptitle('典型时刻二维流速分布对比', fontsize=14)
    fig.colorbar(sc, ax=axes.ravel().tolist(), label='流速 (m/s)')
    save_figure(fig, plot_dir / '2d_snapshots_velocity.png')


if __name__ == '__main__':
    main()
