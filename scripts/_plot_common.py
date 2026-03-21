from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any
import warnings

import json

from coupling.runtime_env import configure_runtime_environment


configure_runtime_environment(Path('/tmp/1d_2d_coupling_plots'))

import matplotlib

matplotlib.use('Agg')
from matplotlib import colors
from matplotlib.collections import PolyCollection
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np
from PIL import Image
from scipy.io import netcdf_file


matplotlib.rcParams['font.sans-serif'] = [
    'SimHei',
    'Microsoft YaHei',
    'WenQuanYi Zen Hei',
    'Noto Sans CJK SC',
    'DejaVu Sans',
]
matplotlib.rcParams['axes.unicode_minus'] = False


CASE_LABELS = {
    'strict_global_min_dt': '严格全局最小步长',
    'yield_schedule': 'Yield 时刻表',
    'fixed_interval_000p5s': '固定间隔 0.5 s',
    'fixed_interval_001s': '固定间隔 1 s',
    'fixed_interval_002s': '固定间隔 2 s',
    'fixed_interval_003s': '固定间隔 3 s',
    'fixed_interval_005s': '固定间隔 5 s',
    'fixed_interval_007p5s': '固定间隔 7.5 s',
    'fixed_interval_010s': '固定间隔 10 s',
    'fixed_interval_015s': '固定间隔 15 s',
    'fixed_interval_020s': '固定间隔 20 s',
    'fixed_interval_030s': '固定间隔 30 s',
    'fixed_interval_060s': '固定间隔 60 s',
    'fixed_interval_120s': '固定间隔 120 s',
    'fixed_interval_300s': '固定间隔 300 s',
}

PROBE_LABELS = {
    'upstream_1d': '上游断面',
    'mainstem_mid': '中游断面',
    'downstream_1d': '下游断面',
    'fp1_probe': '洪泛区 1 测点',
    'fp2_probe': '洪泛区 2 测点',
    'fp3_probe': '洪泛区 3 测点',
    'mainstem_left_q': '主河道左端流量',
    'mainstem_right_q': '主河道右端流量',
}

LINK_LABELS = {
    'fp1_overtop': '洪泛区 1 漫顶界面',
    'fp2_return': '洪泛区 2 回流界面',
    'fp3_overtop': '洪泛区 3 漫顶界面',
    'front_main': '主河道直连接口',
    'return_link': '回流界面',
    'early_link': '早到达侧向界面',
    'backwater_link': '回水界面',
    'mixed_return_link': '混合回流界面',
}

PARTITION_LABELS = {
    'Floodplain_1': '洪泛区 1',
    'Floodplain_2': '洪泛区 2',
    'Floodplain_3': '洪泛区 3',
}

FAMILY_LABELS = {
    'surrogate_test7_overtopping_only_variant': '替代 Test 7 漫顶交换算例',
    'official_test7_overtopping_only_variant': '官方 Test 7 漫顶交换算例',
    'frontal_basin_fill': '端部直连蓄盆充水算例',
    'lateral_overtopping_return': '侧向漫顶-回流算例',
    'early_arrival_pulse': '早到达脉冲算例',
    'regime_switch_backwater_or_mixed': '回水/流态切换混合算例',
}


def case_label(label: str) -> str:
    return CASE_LABELS.get(label, label.replace('_', ' '))


def probe_label(label: str) -> str:
    return PROBE_LABELS.get(label, label.replace('_', ' '))


def link_label(label: str) -> str:
    return LINK_LABELS.get(label, label.replace('_', ' '))


def partition_label(label: str) -> str:
    return PARTITION_LABELS.get(label, label.replace('_', ' '))


def family_label(label: str) -> str:
    return FAMILY_LABELS.get(label, label.replace('_', ' '))


def case_name_to_display(case_name: str) -> str:
    for suffix in sorted(CASE_LABELS, key=len, reverse=True):
        if case_name.endswith(suffix):
            return CASE_LABELS[suffix]
    return case_name.replace('_', ' ')


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def load_summary_rows(root: Path) -> list[dict[str, str]]:
    return load_csv_rows(root / 'summary_table.csv')


def load_mesh_summary_rows(root: Path) -> list[dict[str, str]]:
    return load_csv_rows(root / 'summary_table_mesh.csv')


def load_chapter_summary_rows(root: Path) -> list[dict[str, str]]:
    return load_csv_rows(root / 'summaries' / 'summary_table.csv')


def load_chapter_small_summary_rows(root: Path) -> list[dict[str, str]]:
    return load_csv_rows(root / 'summaries' / 'summary_table_small_cases.csv')


def load_chapter_partition_rows(root: Path) -> list[dict[str, str]]:
    return load_csv_rows(root / 'summaries' / 'summary_table_test7_partitions.csv')


def load_chapter_timing_rows(root: Path) -> list[dict[str, str]]:
    return load_csv_rows(root / 'summaries' / 'timing_breakdown.csv')


def load_json_payload(path: Path) -> Any:
    with path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def chapter_case_rows(root: Path, case_name: str, filename: str) -> list[dict[str, str]]:
    return load_csv_rows(resolve_case_dir(root, case_name) / filename)


def chapter_case_json(root: Path, case_name: str, filename: str) -> Any:
    return load_json_payload(resolve_case_dir(root, case_name) / filename)


def case_rows(root: Path, case_name: str, filename: str) -> list[dict[str, str]]:
    return load_csv_rows(Path(root) / case_name / filename)


def chapter_figure_manifest_rows(root: Path) -> list[dict[str, str]]:
    return load_csv_rows(root / 'summaries' / 'figure_manifest.csv')


def ensure_plot_dir(root: Path) -> Path:
    plot_dir = root / 'plots'
    plot_dir.mkdir(parents=True, exist_ok=True)
    return plot_dir


def scheduler_case_names(summary_rows: list[dict[str, str]]) -> list[str]:
    return sorted(
        [
            row['case_name']
            for row in summary_rows
            if row['case_name'].startswith('mixed_bidirectional_pulse_')
        ]
    )


def interval_seconds(case_name: str) -> float:
    match = re.search(r'fixed_interval_(\d{3})(?:p(\d+))?s', case_name)
    if not match:
        raise ValueError(f'case name does not encode a fixed interval: {case_name}')
    whole = int(match.group(1))
    frac = match.group(2)
    if frac is None:
        return float(whole)
    return float(f'{whole}.{frac}')


def interval_label(case_name: str) -> str:
    seconds = interval_seconds(case_name)
    if abs(seconds - round(seconds)) <= 1.0e-12:
        return f'{int(round(seconds))} 秒'
    return f'{seconds:g} 秒'


def fixed_interval_rows(summary_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = [row for row in summary_rows if 'fixed_interval_' in row['case_name'] and row['case_name'].startswith('mixed_bidirectional_pulse_')]
    return sorted(rows, key=lambda row: interval_seconds(row['case_name']))


def chapter_fixed_interval_rows(summary_rows: list[dict[str, str]], scenario_family: str) -> list[dict[str, str]]:
    rows = [
        row
        for row in summary_rows
        if row['scenario_family'] == scenario_family and 'fixed_interval_' in row['case_name']
    ]
    return sorted(rows, key=lambda row: interval_seconds(row['case_name']))


def series_from_rows(
    rows: list[dict[str, str]],
    x_key: str,
    y_key: str,
    filter_key: str | None = None,
    filter_value: str | None = None,
) -> tuple[list[float], list[float]]:
    filtered = rows
    if filter_key is not None:
        filtered = [row for row in rows if row.get(filter_key) == filter_value]
    pairs = sorted((float(row[x_key]), float(row[y_key])) for row in filtered)
    return [pair[0] for pair in pairs], [pair[1] for pair in pairs]


def aggregate_exchange_series(rows: list[dict[str, str]]) -> tuple[list[float], list[float]]:
    grouped: dict[float, float] = defaultdict(float)
    for row in rows:
        grouped[float(row['time'])] += float(row['Q_exchange'])
    times = sorted(grouped)
    return times, [grouped[t] for t in times]


def save_figure(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore', message='This figure includes Axes that are not compatible with tight_layout')
        fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor='white')
    plt.close(fig)


def _row_count(payload: Any) -> int:
    if hasattr(payload, 'shape'):
        shape = getattr(payload, 'shape')
        if shape:
            return int(shape[0])
    if hasattr(payload, '__len__'):
        return int(len(payload))
    raise TypeError(f'Unsupported tabular payload type: {type(payload)!r}')


def assert_nonempty_dataframe(payload: Any, label: str) -> None:
    if _row_count(payload) <= 0:
        raise ValueError(f'{label} is empty')


def assert_required_columns(payload: Any, required_columns: Sequence[str], label: str) -> None:
    required = tuple(required_columns)
    if hasattr(payload, 'columns'):
        columns = set(str(column) for column in payload.columns)
    else:
        rows = list(payload)
        assert_nonempty_dataframe(rows, label)
        first = rows[0]
        if not isinstance(first, Mapping):
            raise TypeError(f'{label} does not expose mapping rows')
        columns = set(first.keys())
    missing = [column for column in required if column not in columns]
    if missing:
        raise KeyError(f'{label} is missing required columns: {missing}')


def assert_finite_range(values: Sequence[float] | np.ndarray, label: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    finite = array[np.isfinite(array)]
    if finite.size == 0:
        raise ValueError(f'{label} has no finite values')
    return finite


def resolve_case_dir(root: Path | str, case_name: str) -> Path:
    root_path = Path(root)
    direct = root_path / case_name
    if direct.exists():
        return direct
    chapter_case = root_path / 'cases' / case_name
    if chapter_case.exists():
        return chapter_case
    mesh_case = root_path / 'mesh_sensitivity' / case_name
    if mesh_case.exists():
        return mesh_case
    raise FileNotFoundError(f'Could not resolve case directory for {case_name!r} under {root_path}')


def _decode_char_matrix(raw: np.ndarray | None) -> list[str]:
    if raw is None:
        return []
    matrix = np.asarray(raw)
    strings: list[str] = []
    for row in matrix:
        pieces: list[str] = []
        for item in row:
            if isinstance(item, bytes):
                pieces.append(item.decode('utf-8', errors='ignore'))
            else:
                pieces.append(str(item))
        strings.append(''.join(pieces).replace('\x00', '').strip())
    return strings


def export_plot_geometry_cache(case_root: Path | str, force: bool = False) -> dict[str, Any]:
    case_dir = Path(case_root)
    cache_dir = case_dir / 'plot_cache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / 'mesh_geometry.npz'
    metadata_path = cache_dir / 'mesh_geometry.json'
    if cache_path.exists() and metadata_path.exists() and not force:
        return load_plot_geometry_cache(case_dir)

    msh_files = sorted(case_dir.glob('*.msh'))
    if not msh_files:
        raise FileNotFoundError(
            f'No .msh file is available under {case_dir}. '
            'A plot cache must be exported once while the local mesh file is present.'
        )

    msh_path = msh_files[0]
    with netcdf_file(str(msh_path), 'r', mmap=False) as dataset:
        vertices = np.asarray(dataset.variables['vertices'].data, dtype=float)
        triangles = np.asarray(dataset.variables['triangles'].data, dtype=np.int32)
        segments_var = dataset.variables.get('segments')
        segments = (
            np.asarray(segments_var.data, dtype=np.int32)
            if segments_var is not None
            else np.empty((0, 2), dtype=np.int32)
        )
        triangle_neighbors_var = dataset.variables.get('triangle_neighbors')
        triangle_neighbors = (
            np.asarray(triangle_neighbors_var.data, dtype=np.int32)
            if triangle_neighbors_var is not None
            else np.empty((0, 3), dtype=np.int32)
        )
        segment_tags_var = dataset.variables.get('segment_tags')
        segment_tags = _decode_char_matrix(segment_tags_var.data if segment_tags_var is not None else None)

    polygons = vertices[triangles]
    centroids = polygons.mean(axis=1)
    bounds = np.asarray(
        [
            float(vertices[:, 0].min()),
            float(vertices[:, 0].max()),
            float(vertices[:, 1].min()),
            float(vertices[:, 1].max()),
        ],
        dtype=float,
    )

    np.savez_compressed(
        cache_path,
        vertices=vertices,
        triangles=triangles,
        segments=segments,
        triangle_neighbors=triangle_neighbors,
        centroids=centroids,
        bounds=bounds,
    )
    metadata = {
        'source_msh': msh_path.name,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'num_vertices': int(vertices.shape[0]),
        'num_triangles': int(triangles.shape[0]),
        'num_segments': int(segments.shape[0]),
        'segment_tags': segment_tags,
        'cache_format': 'mesh_geometry.npz',
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    return load_plot_geometry_cache(case_dir)


def load_plot_geometry_cache(case_root: Path | str) -> dict[str, Any]:
    case_dir = Path(case_root)
    cache_dir = case_dir / 'plot_cache'
    cache_path = cache_dir / 'mesh_geometry.npz'
    metadata_path = cache_dir / 'mesh_geometry.json'
    if not cache_path.exists():
        raise FileNotFoundError(f'Missing plot geometry cache: {cache_path}')
    payload = np.load(cache_path, allow_pickle=False)
    metadata = load_json_payload(metadata_path) if metadata_path.exists() else {}
    geometry = {
        'vertices': np.asarray(payload['vertices'], dtype=float),
        'triangles': np.asarray(payload['triangles'], dtype=np.int32),
        'segments': np.asarray(payload['segments'], dtype=np.int32),
        'triangle_neighbors': np.asarray(payload['triangle_neighbors'], dtype=np.int32),
        'centroids': np.asarray(payload['centroids'], dtype=float),
        'bounds': np.asarray(payload['bounds'], dtype=float),
        'metadata': metadata,
        'case_dir': case_dir,
        'cache_dir': cache_dir,
        'polygons': np.asarray(payload['vertices'], dtype=float)[np.asarray(payload['triangles'], dtype=np.int32)],
    }
    return geometry


def validate_plot_geometry_cache(geometry: Mapping[str, Any], expected_cell_count: int | None = None) -> None:
    vertices = np.asarray(geometry['vertices'], dtype=float)
    triangles = np.asarray(geometry['triangles'], dtype=np.int32)
    centroids = np.asarray(geometry['centroids'], dtype=float)
    bounds = np.asarray(geometry['bounds'], dtype=float)
    if vertices.ndim != 2 or vertices.shape[1] != 2:
        raise ValueError('Plot geometry cache vertices must have shape (n, 2)')
    if triangles.ndim != 2 or triangles.shape[1] != 3:
        raise ValueError('Plot geometry cache triangles must have shape (m, 3)')
    if centroids.shape != (triangles.shape[0], 2):
        raise ValueError('Plot geometry cache centroids do not align with triangles')
    if bounds.shape != (4,):
        raise ValueError('Plot geometry cache bounds must contain [xmin, xmax, ymin, ymax]')
    if expected_cell_count is not None and int(triangles.shape[0]) != int(expected_cell_count):
        raise ValueError(
            f'Plot geometry cache triangle count {triangles.shape[0]} '
            f'does not match expected cell count {expected_cell_count}'
        )


def load_mesh_geometry_for_case(root: Path | str, case_name: str) -> dict[str, Any]:
    case_dir = resolve_case_dir(root, case_name)
    cache_path = case_dir / 'plot_cache' / 'mesh_geometry.npz'
    if not cache_path.exists():
        export_plot_geometry_cache(case_dir)
    geometry = load_plot_geometry_cache(case_dir)
    field_summary_path = case_dir / 'two_d_field_summary.csv'
    if field_summary_path.exists():
        expected_cells = _row_count(load_csv_rows(field_summary_path))
        validate_plot_geometry_cache(geometry, expected_cell_count=expected_cells)
    else:
        validate_plot_geometry_cache(geometry)
    return geometry


def build_cell_value_array(
    rows: Sequence[Mapping[str, str]],
    value_key: str,
    *,
    expected_cells: int,
    fill_value: float = np.nan,
) -> np.ndarray:
    assert_nonempty_dataframe(rows, f'rows for {value_key}')
    assert_required_columns(rows, ('cell_id', value_key), f'rows for {value_key}')
    values = np.full(int(expected_cells), float(fill_value), dtype=float)
    for row in rows:
        cell_id = int(row['cell_id'])
        raw_value = row.get(value_key, '')
        values[cell_id] = float(raw_value) if raw_value not in ('', None) else np.nan
    return values


def build_snapshot_value_array(
    rows: Sequence[Mapping[str, str]],
    snapshot_id: str,
    value_key: str,
    *,
    expected_cells: int,
    fill_value: float = np.nan,
) -> np.ndarray:
    filtered = [row for row in rows if row.get('snapshot_id') == snapshot_id]
    assert_nonempty_dataframe(filtered, f'{value_key} rows for {snapshot_id}')
    return build_cell_value_array(filtered, value_key, expected_cells=expected_cells, fill_value=fill_value)


def compute_robust_color_limits(
    values: Sequence[float] | np.ndarray,
    *,
    symmetric: bool = False,
    quantiles: tuple[float, float] = (0.02, 0.98),
) -> tuple[float, float]:
    finite = assert_finite_range(values, 'color values')
    lower = float(np.nanquantile(finite, quantiles[0]))
    upper = float(np.nanquantile(finite, quantiles[1]))
    if symmetric:
        bound = max(abs(lower), abs(upper), abs(float(np.nanmin(finite))), abs(float(np.nanmax(finite))))
        if bound <= 0.0:
            bound = 1.0
        return -bound, bound
    if upper <= lower:
        center = float(finite[0])
        pad = max(abs(center) * 0.05, 1.0e-3)
        return center - pad, center + pad
    return lower, upper


def _collection_cmap(cmap_name: str, nan_color: str) -> colors.Colormap:
    cmap = matplotlib.colormaps.get_cmap(cmap_name).copy()
    cmap.set_bad(color=nan_color)
    return cmap


def render_scalar_field_on_mesh(
    ax,
    geometry: Mapping[str, Any],
    scalar_values: Sequence[float] | np.ndarray,
    *,
    cmap: str = 'viridis',
    label: str | None = None,
    limits: tuple[float, float] | None = None,
    symmetric: bool = False,
    nan_color: str = '#efefef',
    mesh_edgecolor: str = '0.65',
    mesh_linewidth: float = 0.18,
    mesh_alpha: float = 0.8,
):
    values = np.asarray(scalar_values, dtype=float)
    geometry_vertices = np.asarray(geometry['vertices'], dtype=float)
    triangles = np.asarray(geometry['triangles'], dtype=np.int32)
    bounds = np.asarray(geometry['bounds'], dtype=float)
    cmap_obj = _collection_cmap(cmap, nan_color)

    if limits is None:
        limits = compute_robust_color_limits(values, symmetric=symmetric)
    vmin, vmax = limits
    if symmetric:
        norm = colors.TwoSlopeNorm(vcenter=0.0, vmin=vmin, vmax=vmax)
    else:
        norm = colors.Normalize(vmin=vmin, vmax=vmax)

    if values.shape[0] == triangles.shape[0]:
        polygons = geometry_vertices[triangles]
        collection = PolyCollection(
            polygons,
            array=np.ma.masked_invalid(values),
            cmap=cmap_obj,
            norm=norm,
            edgecolors=mesh_edgecolor,
            linewidths=mesh_linewidth,
            alpha=mesh_alpha,
        )
        ax.add_collection(collection)
        mappable = collection
    elif values.shape[0] == geometry_vertices.shape[0]:
        triangulation = mtri.Triangulation(geometry_vertices[:, 0], geometry_vertices[:, 1], triangles=triangles)
        mappable = ax.tripcolor(triangulation, values, shading='gouraud', cmap=cmap_obj, norm=norm)
        ax.triplot(
            triangulation,
            color=mesh_edgecolor,
            linewidth=mesh_linewidth,
            alpha=mesh_alpha,
        )
    else:
        raise ValueError(
            f'Scalar field length {values.shape[0]} does not match either '
            f'cell count {triangles.shape[0]} or vertex count {geometry_vertices.shape[0]}'
        )

    ax.set_xlim(float(bounds[0]), float(bounds[1]))
    ax.set_ylim(float(bounds[2]), float(bounds[3]))
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlabel('x 坐标')
    ax.set_ylabel('y 坐标')
    if label is not None:
        ax.set_title(label)
    return mappable


def draw_mesh_outline(
    ax,
    geometry: Mapping[str, Any],
    *,
    facecolor: str = '#fafafa',
    edgecolor: str = '0.70',
    linewidth: float = 0.18,
    alpha: float = 1.0,
):
    polygons = np.asarray(geometry['polygons'], dtype=float)
    bounds = np.asarray(geometry['bounds'], dtype=float)
    collection = PolyCollection(
        polygons,
        facecolors=facecolor,
        edgecolors=edgecolor,
        linewidths=linewidth,
        alpha=alpha,
    )
    ax.add_collection(collection)
    ax.set_xlim(float(bounds[0]), float(bounds[1]))
    ax.set_ylim(float(bounds[2]), float(bounds[3]))
    ax.set_aspect('equal', adjustable='box')
    return collection


def shared_color_limits(
    arrays: Iterable[Sequence[float] | np.ndarray],
    *,
    symmetric: bool = False,
) -> tuple[float, float]:
    finite_chunks = [assert_finite_range(values, 'shared color values') for values in arrays]
    if not finite_chunks:
        raise ValueError('No arrays were supplied for shared color limits')
    merged = np.concatenate(finite_chunks)
    return compute_robust_color_limits(merged, symmetric=symmetric)


def axis_limits_with_padding(
    values: Sequence[float] | np.ndarray,
    *,
    symmetric: bool = False,
    relative_pad: float = 0.08,
    min_pad: float = 1.0e-3,
) -> tuple[float, float]:
    finite = assert_finite_range(values, 'axis values')
    vmin = float(np.min(finite))
    vmax = float(np.max(finite))
    if symmetric:
        bound = max(abs(vmin), abs(vmax))
        pad = max(bound * float(relative_pad), float(min_pad))
        if bound <= float(min_pad):
            return -pad, pad
        return -(bound + pad), bound + pad
    span = vmax - vmin
    if span <= 1.0e-12:
        pad = max(abs(vmax) * float(relative_pad), float(min_pad))
        return vmin - pad, vmax + pad
    pad = max(span * float(relative_pad), float(min_pad))
    return vmin - pad, vmax + pad


def blank_image_audit(
    image_path: Path | str,
    *,
    is_2d_map: bool = False,
    manifest_row: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    path = Path(image_path)
    image = Image.open(path).convert('RGB')
    array = np.asarray(image, dtype=np.float32) / 255.0
    white_mask = np.all(array >= 0.985, axis=2)
    nonwhite_ratio = float(1.0 - white_mask.mean())
    variance = float(array.var())
    flattened = array.reshape(-1, 3)
    sample = flattened[:: max(1, flattened.shape[0] // 20000)]
    unique_colors = int(np.unique((sample * 255.0).astype(np.uint8), axis=0).shape[0])
    dominant_fraction = float(np.max(np.unique((sample * 255.0).astype(np.uint8), axis=0, return_counts=True)[1]) / sample.shape[0])
    ys, xs = np.where(~white_mask)
    if ys.size == 0:
        interior = array
    else:
        y0, y1 = int(ys.min()), int(ys.max())
        x0, x1 = int(xs.min()), int(xs.max())
        box_h = max(y1 - y0 + 1, 1)
        box_w = max(x1 - x0 + 1, 1)
        pad_y = max(int(box_h * 0.08), 4)
        pad_x = max(int(box_w * 0.08), 4)
        iy0 = min(max(y0 + pad_y, 0), array.shape[0] - 1)
        iy1 = max(min(y1 - pad_y, array.shape[0] - 1), iy0)
        ix0 = min(max(x0 + pad_x, 0), array.shape[1] - 1)
        ix1 = max(min(x1 - pad_x, array.shape[1] - 1), ix0)
        interior = array[iy0 : iy1 + 1, ix0 : ix1 + 1]
    interior_nonwhite = np.any(interior < 0.985, axis=2)
    interior_ratio = float(interior_nonwhite.mean()) if interior_nonwhite.size else 0.0
    interior_variance = float(interior.var()) if interior.size else 0.0
    interior_rgb = interior.reshape(-1, 3)
    rg = interior_rgb[:, 0] - interior_rgb[:, 1]
    yb = 0.5 * (interior_rgb[:, 0] + interior_rgb[:, 1]) - interior_rgb[:, 2]
    interior_colorfulness = float(np.sqrt(np.var(rg) + np.var(yb))) if interior_rgb.size else 0.0
    blank = bool(
        (nonwhite_ratio < 0.0015 and variance < 0.0004)
        or (unique_colors <= 2 and dominant_fraction > 0.995 and variance < 0.0004)
    )
    near_blank = bool(
        not blank
        and (
            (nonwhite_ratio < 0.008 and variance < 0.0015)
            or (is_2d_map and nonwhite_ratio < 0.12 and variance < 0.04)
            or (unique_colors <= 3 and variance < 0.0015)
            or (
                interior_ratio < 0.03
                and interior_variance < 0.007
                and interior_colorfulness < 0.005
            )
        )
    )
    manifest_entry = ''
    if manifest_row is not None:
        manifest_entry = str(manifest_row.get('figure_id', ''))
    return {
        'file_name': path.name,
        'file_size_bytes': int(path.stat().st_size),
        'width_px': int(image.size[0]),
        'height_px': int(image.size[1]),
        'pixel_variance': variance,
        'nonwhite_ratio': nonwhite_ratio,
        'interior_nonwhite_ratio': interior_ratio,
        'interior_pixel_variance': interior_variance,
        'interior_colorfulness': interior_colorfulness,
        'dominant_color_fraction': dominant_fraction,
        'unique_color_count_sampled': unique_colors,
        'is_blank': bool(blank),
        'is_near_blank': bool(near_blank),
        'blank_level': 'blank' if blank else 'near_blank' if near_blank else 'ok',
        'is_approximately_blank': bool(blank or near_blank),
        'is_2d_map': bool(is_2d_map),
        'figure_manifest_id': manifest_entry,
    }


def plot_category_for_file(file_name: str, *, is_2d_map: bool = False) -> str:
    name = str(file_name)
    if is_2d_map or name.startswith('2d_') or name in {'flood_front_overlay.png', 'test7_geometry_and_mesh.png'}:
        return '2d_map'
    if 'dashboard' in name:
        return 'dashboard'
    if any(
        token in name
        for token in (
            'hydrograph',
            'stage',
            'discharge',
            'exchange',
            'arrival',
            'rmse',
            'runtime',
            'cost',
            'interval',
            'phase',
        )
    ):
        return 'hydrograph'
    return 'other'


def _case_name_hint_from_manifest_row(manifest_row: Mapping[str, str] | None) -> str:
    if manifest_row is None:
        return ''
    input_paths = str(manifest_row.get('input_data_paths', '')).strip()
    if not input_paths:
        return ''
    for chunk in input_paths.split(';'):
        chunk = chunk.strip()
        if 'cases/' not in chunk:
            continue
        tail = chunk.split('cases/', 1)[1]
        case_hint = tail.split('/', 1)[0].strip()
        if case_hint:
            return case_hint
    return ''


def audit_plot_directory(
    plot_dir: Path | str,
    *,
    manifest_rows: Sequence[Mapping[str, str]] | None = None,
    repo_root: Path | str | None = None,
) -> list[dict[str, Any]]:
    directory = Path(plot_dir)
    resolved_repo_root = Path(repo_root) if repo_root is not None else None
    manifest_map: dict[str, Mapping[str, str]] = {}
    if manifest_rows is not None:
        manifest_map = {
            Path(str(row.get('output_png_path', ''))).name: row
            for row in manifest_rows
        }
    rows: list[dict[str, Any]] = []
    raster_suffixes = {'.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'}
    for path in sorted(directory.glob('*')):
        if path.suffix.lower() not in raster_suffixes:
            continue
        manifest_row = manifest_map.get(path.name)
        is_2d_map = path.name.startswith('2d_') or path.name == 'test7_geometry_and_mesh.png' or path.name == 'flood_front_overlay.png'
        audit = blank_image_audit(path, is_2d_map=is_2d_map, manifest_row=manifest_row)
        audit['plot_category'] = plot_category_for_file(path.name, is_2d_map=is_2d_map)
        audit['script_path'] = str(manifest_row.get('script_path', '')) if manifest_row is not None else ''
        audit['case_name_hint'] = _case_name_hint_from_manifest_row(manifest_row)
        audit['render_mode'] = str(manifest_row.get('render_mode', '')) if manifest_row is not None else ''
        audit['output_png_path'] = str(manifest_row.get('output_png_path', '')) if manifest_row is not None else ''
        if resolved_repo_root is not None:
            audit['relative_path'] = str(path.resolve().relative_to(resolved_repo_root.resolve()))
        else:
            audit['relative_path'] = str(path)
        rows.append(audit)
    return rows


def write_csv_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text('', encoding='utf-8')
        return
    fieldnames = list(rows[0].keys())
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
