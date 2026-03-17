from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from experiments.io import ensure_dir, read_csv, write_csv, write_json
from scripts._plot_common import (
    audit_plot_directory,
    chapter_case_rows,
    export_plot_geometry_cache,
    load_chapter_summary_rows,
)


_MESH_GEOMETRY_MODULES = {
    'scripts.plot_test7_geometry_and_mesh',
    'scripts.plot_2d_snapshots_depth',
    'scripts.plot_2d_snapshots_velocity',
    'scripts.plot_2d_max_depth_map',
    'scripts.plot_2d_arrival_time_map',
    'scripts.plot_2d_difference_map',
    'scripts.plot_flood_front_overlay',
}


def _chapter_dirs(root: Path) -> dict[str, Path]:
    return {
        'root': root,
        'cases': ensure_dir(root / 'cases'),
        'mesh_sensitivity': ensure_dir(root / 'mesh_sensitivity'),
        'plots': ensure_dir(root / 'plots'),
        'summaries': ensure_dir(root / 'summaries'),
        'logs': ensure_dir(root / 'logs'),
    }


def _iter_case_dirs(root: Path) -> list[Path]:
    directories: list[Path] = []
    for base in (root / 'cases', root / 'mesh_sensitivity'):
        if not base.exists():
            continue
        directories.extend(sorted(path for path in base.iterdir() if path.is_dir()))
    return directories


def export_all_plot_geometry_caches(root: Path) -> list[dict[str, Any]]:
    exported: list[dict[str, Any]] = []
    for case_dir in _iter_case_dirs(root):
        try:
            geometry = export_plot_geometry_cache(case_dir)
        except FileNotFoundError:
            continue
        exported.append(
            {
                'case_name': case_dir.name,
                'cache_path': str((case_dir / 'plot_cache' / 'mesh_geometry.npz').relative_to(root)),
                'num_triangles': int(geometry['triangles'].shape[0]),
                'num_vertices': int(geometry['vertices'].shape[0]),
            }
        )
    return exported


def _geometry_source(module_name: str) -> str:
    if module_name in _MESH_GEOMETRY_MODULES:
        return 'cases/<case_name>/plot_cache/mesh_geometry.npz'
    return 'n/a'


def _render_mode(module_name: str) -> str:
    if module_name == 'scripts.plot_flood_front_overlay':
        return 'mesh_faces_with_gray_edges + flood_front_boundaries'
    if module_name == 'scripts.plot_test7_geometry_and_mesh':
        return 'mesh_outline_with_gray_edges + vector overlays'
    if module_name in _MESH_GEOMETRY_MODULES:
        return 'mesh_faces_with_gray_edges'
    return 'non-2d-plot'


def _is_benchmark_family(row: dict[str, str]) -> bool:
    return 'test7' in row.get('scenario_family', '')


def _benchmark_family(root: Path) -> str:
    rows = load_chapter_summary_rows(root)
    for row in rows:
        if _is_benchmark_family(row):
            return row['scenario_family']
    raise KeyError('No benchmark family found in chapter summaries')


def _suspected_blank_reason(root: Path, file_name: str, is_blank: bool) -> str:
    if not is_blank:
        return 'ok'
    benchmark_family = _benchmark_family(root)
    if file_name == '2d_arrival_time_map.png':
        rows = chapter_case_rows(root, f'{benchmark_family}_strict_global_min_dt', 'two_d_field_summary.csv')
        values = {row.get('arrival_time', '') for row in rows}
        if len(values) <= 1:
            return 'constant_scalar_field_plus_sparse_rendering'
    if file_name == 'flood_front_overlay.png':
        return 'point_overlay_only'
    if file_name == 'test7_geometry_and_mesh.png':
        return 'mesh_visualized_as_centroids_only'
    if file_name.startswith('2d_'):
        return 'centroid_scatter_rendering'
    return 'other'


def _figure_rows_from_specs(
    root: Path,
    plot_specs: list[dict[str, str]],
    audit_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    audit_map = {row['file_name']: row for row in audit_rows}
    rows: list[dict[str, Any]] = []
    now_iso = __import__('datetime').datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
    for spec in plot_specs:
        file_name = Path(spec['output_png_path']).name
        audit = audit_map.get(file_name, {})
        is_blank = bool(audit.get('is_approximately_blank', False))
        rows.append(
            {
                'figure_id': spec['figure_id'],
                'script_path': spec['module_name'].replace('.', '/') + '.py',
                'input_data_paths': spec['input_data_paths'],
                'output_png_path': spec['output_png_path'],
                'caption_draft_cn': spec['caption_draft_cn'],
                'caption_draft_en': spec['caption_draft_en'],
                'chapter_section': spec['chapter_section'],
                'geometry_source': _geometry_source(spec['module_name']),
                'render_mode': _render_mode(spec['module_name']),
                'blank_check_status': 'fail' if is_blank else 'pass',
                'regenerated_at': now_iso,
            }
        )
    return rows


def refresh_chapter_plot_outputs(root: Path | str, plot_specs: list[dict[str, str]]) -> dict[str, Any]:
    outputs = _chapter_dirs(Path(root))
    existing_manifest = read_csv(outputs['summaries'] / 'figure_manifest.csv')
    before_audit = audit_plot_directory(outputs['plots'], manifest_rows=existing_manifest)
    for row in before_audit:
        row['suspected_root_cause'] = _suspected_blank_reason(outputs['root'], row['file_name'], bool(row['is_approximately_blank']))
    write_csv(outputs['logs'] / 'blank_plot_audit_before.csv', before_audit)
    write_json(outputs['logs'] / 'blank_plot_audit_before.json', before_audit)

    cache_rows = export_all_plot_geometry_caches(outputs['root'])
    write_csv(outputs['logs'] / 'plot_geometry_cache_index.csv', cache_rows)
    write_json(outputs['logs'] / 'plot_geometry_cache_index.json', cache_rows)

    for spec in plot_specs:
        module = importlib.import_module(spec['module_name'])
        module.main(outputs['root'])

    after_audit = audit_plot_directory(outputs['plots'], manifest_rows=existing_manifest)
    for row in after_audit:
        row['suspected_root_cause'] = _suspected_blank_reason(outputs['root'], row['file_name'], bool(row['is_approximately_blank']))
    write_csv(outputs['logs'] / 'blank_plot_audit.csv', after_audit)
    write_json(outputs['logs'] / 'blank_plot_audit.json', after_audit)

    figure_rows = _figure_rows_from_specs(outputs['root'], plot_specs, after_audit)
    write_csv(outputs['summaries'] / 'figure_manifest.csv', figure_rows)
    if any(bool(row['is_approximately_blank']) for row in after_audit):
        failing = [row['file_name'] for row in after_audit if bool(row['is_approximately_blank'])]
        raise RuntimeError(f'Blank or near-blank figures remain after refresh: {failing}')
    return {
        'figure_rows': figure_rows,
        'before_audit': before_audit,
        'after_audit': after_audit,
        'cache_rows': cache_rows,
    }
