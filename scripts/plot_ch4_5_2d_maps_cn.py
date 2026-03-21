from __future__ import annotations

# Inputs:
# - artifacts/chapter_coupling_analysis_fastest_exact/cases/<benchmark>/plot_cache/mesh_geometry.*
# - artifacts/chapter_coupling_analysis_fastest_exact/cases/<benchmark>/two_d_field_summary.csv
# - artifacts/chapter_coupling_analysis_fastest_exact/cases/<benchmark>/two_d_snapshots.csv

from pathlib import Path
import numpy as np

from scripts._plot_ch4_5_common import (
    BENCHMARK_MAP_SUFFIXES,
    BENCHMARK_TITLE,
    _plot_union_boundary,
    _wet_union,
    benchmark_case_name,
    output_roots,
    parse_cli,
    print_input_files,
    save_png_pdf,
    scheme_label,
)
from scripts._plot_common import (
    assert_nonempty_dataframe,
    assert_required_columns,
    build_cell_value_array,
    build_snapshot_value_array,
    chapter_case_rows,
    ensure_plot_dir,
    load_mesh_geometry_for_case,
    plt,
    render_scalar_field_on_mesh,
    shared_color_limits,
)

MAP_ROOT = Path('artifacts/chapter_coupling_analysis_fastest_exact')


def _render_for_root(output_root: Path) -> None:
    plot_dir = ensure_plot_dir(output_root)
    case_names = [benchmark_case_name(MAP_ROOT, suffix) for suffix in BENCHMARK_MAP_SUFFIXES]

    geometry = load_mesh_geometry_for_case(MAP_ROOT, case_names[0])
    input_paths = [MAP_ROOT / 'cases' / case_names[0] / 'plot_cache' / 'mesh_geometry.npz', MAP_ROOT / 'cases' / case_names[0] / 'plot_cache' / 'mesh_geometry.json']
    arrays = []
    field_rows_map = {}
    for case_name in case_names:
        path = MAP_ROOT / 'cases' / case_name / 'two_d_field_summary.csv'
        rows = chapter_case_rows(MAP_ROOT, case_name, 'two_d_field_summary.csv')
        assert_nonempty_dataframe(rows, f'two_d_field_summary for {case_name}')
        assert_required_columns(rows, ('cell_id', 'max_depth', 'arrival_time'), f'two_d_field_summary for {case_name}')
        field_rows_map[case_name] = rows
        input_paths.append(path)
        arrays.append(build_cell_value_array(rows, 'max_depth', expected_cells=int(geometry['triangles'].shape[0])))
    limits = shared_color_limits(arrays)
    fig, axes = plt.subplots(2, 2, figsize=(12.2, 8.2), sharex=True, sharey=True)
    sc = None
    for ax, suffix, case_name, values in zip(axes.flat, BENCHMARK_MAP_SUFFIXES, case_names, arrays):
        sc = render_scalar_field_on_mesh(ax, geometry, values, cmap='Blues', limits=limits, label=scheme_label(suffix))
        ax.set_title(scheme_label(suffix))
    fig.suptitle(f'{BENCHMARK_TITLE}二维最大水深分布图', fontsize=14)
    fig.colorbar(sc, ax=axes.ravel().tolist(), label='最大水深 / m')
    save_png_pdf(fig, plot_dir, 'max_depth_map_cn')
    print_input_files('max_depth_map_cn', input_paths, provenance=f'source_root={MAP_ROOT}')

    ref_values = arrays[0]
    diff_values = arrays[-1] - ref_values
    fig, ax = plt.subplots(figsize=(10.2, 4.8))
    sc = render_scalar_field_on_mesh(ax, geometry, diff_values, cmap='coolwarm', symmetric=True, label='固定步长 15 s 相对严格同步参考方案')
    ax.set_title(f'{BENCHMARK_TITLE}二维最大水深差异图')
    fig.colorbar(sc, ax=ax, label='最大水深差值 / m')
    save_png_pdf(fig, plot_dir, 'max_depth_difference_map_cn')
    print_input_files('max_depth_difference_map_cn', input_paths, provenance='difference = fixed_interval_015s - strict_global_min_dt')

    ref_case = case_names[0]
    cmp_case = case_names[-1]
    snapshot_paths = [MAP_ROOT / 'cases' / ref_case / 'two_d_snapshots.csv', MAP_ROOT / 'cases' / cmp_case / 'two_d_snapshots.csv']
    ref_rows = chapter_case_rows(MAP_ROOT, ref_case, 'two_d_snapshots.csv')
    cmp_rows = chapter_case_rows(MAP_ROOT, cmp_case, 'two_d_snapshots.csv')
    fig, ax = plt.subplots(figsize=(10.2, 4.8))
    background_values = build_snapshot_value_array(ref_rows, 'snapshot_3', 'depth', expected_cells=int(geometry['triangles'].shape[0]))
    render_scalar_field_on_mesh(ax, geometry, background_values, cmap='Blues', label='严格同步参考方案背景水深')
    for snapshot_id, color in [('snapshot_1', '#355070'), ('snapshot_2', '#6d597a'), ('snapshot_3', '#b56576')]:
        ref_values = build_snapshot_value_array(ref_rows, snapshot_id, 'depth', expected_cells=int(geometry['triangles'].shape[0]))
        cmp_values = build_snapshot_value_array(cmp_rows, snapshot_id, 'depth', expected_cells=int(geometry['triangles'].shape[0]))
        _plot_union_boundary(ax, _wet_union(geometry, ref_values), color=color, linestyle='-', linewidth=1.2, label=f'{snapshot_id} 参考方案')
        _plot_union_boundary(ax, _wet_union(geometry, cmp_values), color=color, linestyle='--', linewidth=1.2, label=f'{snapshot_id} 固定步长 15 s')
    ax.set_title(f'{BENCHMARK_TITLE}洪泛前沿叠置图')
    ax.legend(ncol=3, fontsize=7.2)
    save_png_pdf(fig, plot_dir, 'flood_front_overlay_cn')
    print_input_files('flood_front_overlay_cn', input_paths + snapshot_paths, provenance=f'source_root={MAP_ROOT}; background=strict snapshot_3')


def main(root: Path | str | None = None) -> None:
    for output_root in output_roots(root):
        _render_for_root(Path(output_root))


if __name__ == '__main__':
    cli_roots = parse_cli()
    if len(cli_roots) == 1:
        main(cli_roots[0])
    else:
        main()
