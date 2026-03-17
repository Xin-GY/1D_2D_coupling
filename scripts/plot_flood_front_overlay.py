from __future__ import annotations

from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import unary_union

from scripts._plot_common import (
    assert_nonempty_dataframe,
    assert_required_columns,
    build_snapshot_value_array,
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


def _wet_union(geometry, values, depth_threshold: float = 0.02):
    polygons = [Polygon(poly) for poly, value in zip(geometry['polygons'], values) if value >= depth_threshold]
    if not polygons:
        return None
    return unary_union(polygons)


def _plot_union_boundary(ax, union_geometry, *, color: str, linestyle: str, linewidth: float, label: str):
    if union_geometry is None or union_geometry.is_empty:
        return
    geometries = [union_geometry] if union_geometry.geom_type == 'Polygon' else list(union_geometry.geoms)
    label_pending = label
    for polygon in geometries:
        x, y = polygon.exterior.xy
        ax.plot(x, y, color=color, linestyle=linestyle, linewidth=linewidth, label=label_pending)
        label_pending = ''


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    plot_dir = ensure_plot_dir(root)
    family = _benchmark_family(load_chapter_summary_rows(root))
    ref_case = f'{family}_strict_global_min_dt'
    case_name = f'{family}_fixed_interval_015s'
    ref_rows = chapter_case_rows(root, ref_case, 'two_d_snapshots.csv')
    case_rows = chapter_case_rows(root, case_name, 'two_d_snapshots.csv')
    assert_nonempty_dataframe(ref_rows, f'two_d_snapshots for {ref_case}')
    assert_nonempty_dataframe(case_rows, f'two_d_snapshots for {case_name}')
    assert_required_columns(ref_rows, ('snapshot_id', 'cell_id', 'depth'), f'two_d_snapshots for {ref_case}')
    assert_required_columns(case_rows, ('snapshot_id', 'cell_id', 'depth'), f'two_d_snapshots for {case_name}')
    geometry = load_mesh_geometry_for_case(root, ref_case)
    background_values = build_snapshot_value_array(
        ref_rows,
        'snapshot_3',
        'depth',
        expected_cells=int(geometry['triangles'].shape[0]),
    )
    fig, ax = plt.subplots(figsize=(10, 4.5))
    render_scalar_field_on_mesh(
        ax,
        geometry,
        background_values,
        cmap='Blues',
        label='Flood-front overlay on reference depth background',
    )
    for snapshot_id, color in [('snapshot_1', '#355070'), ('snapshot_2', '#6d597a'), ('snapshot_3', '#b56576')]:
        ref_values = build_snapshot_value_array(
            ref_rows,
            snapshot_id,
            'depth',
            expected_cells=int(geometry['triangles'].shape[0]),
        )
        case_values = build_snapshot_value_array(
            case_rows,
            snapshot_id,
            'depth',
            expected_cells=int(geometry['triangles'].shape[0]),
        )
        _plot_union_boundary(
            ax,
            _wet_union(geometry, ref_values),
            color=color,
            linestyle='-',
            linewidth=1.1,
            label=f'{snapshot_id} ref',
        )
        _plot_union_boundary(
            ax,
            _wet_union(geometry, case_values),
            color=color,
            linestyle='--',
            linewidth=1.1,
            label=f'{snapshot_id} 15s',
        )
    ax.legend(ncol=3, fontsize=7)
    save_figure(fig, plot_dir / 'flood_front_overlay.png')


if __name__ == '__main__':
    main()
