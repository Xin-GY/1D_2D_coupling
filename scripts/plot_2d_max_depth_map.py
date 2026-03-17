from __future__ import annotations

from pathlib import Path

from scripts._plot_common import (
    assert_nonempty_dataframe,
    assert_required_columns,
    build_cell_value_array,
    chapter_case_rows,
    ensure_plot_dir,
    load_chapter_summary_rows,
    load_mesh_geometry_for_case,
    plt,
    render_scalar_field_on_mesh,
    save_figure,
)


def _benchmark_family(rows):
    for row in rows:
        if 'test7' in row['scenario_family']:
            return row['scenario_family']
    raise KeyError('No benchmark family found')


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    plot_dir = ensure_plot_dir(root)
    family = _benchmark_family(load_chapter_summary_rows(root))
    case_name = f'{family}_strict_global_min_dt'
    rows = chapter_case_rows(root, case_name, 'two_d_field_summary.csv')
    assert_nonempty_dataframe(rows, f'two_d_field_summary for {case_name}')
    assert_required_columns(rows, ('cell_id', 'max_depth'), f'two_d_field_summary for {case_name}')
    geometry = load_mesh_geometry_for_case(root, case_name)
    values = build_cell_value_array(rows, 'max_depth', expected_cells=int(geometry['triangles'].shape[0]))
    fig, ax = plt.subplots(figsize=(10, 4.5))
    sc = render_scalar_field_on_mesh(ax, geometry, values, cmap='Blues', label='Reference max depth')
    fig.colorbar(sc, ax=ax, label='max depth (m)')
    save_figure(fig, plot_dir / '2d_max_depth_map.png')


if __name__ == '__main__':
    main()
