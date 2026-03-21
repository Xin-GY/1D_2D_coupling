from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
from matplotlib.collections import LineCollection
from shapely.geometry import Polygon
from shapely.ops import unary_union

from scripts._plot_common import (
    aggregate_exchange_series,
    assert_nonempty_dataframe,
    assert_required_columns,
    axis_limits_with_padding,
    build_cell_value_array,
    build_snapshot_value_array,
    chapter_case_json,
    chapter_case_rows,
    draw_mesh_outline,
    ensure_plot_dir,
    load_chapter_small_summary_rows,
    load_chapter_summary_rows,
    load_mesh_geometry_for_case,
    plt,
    render_scalar_field_on_mesh,
    shared_color_limits,
)

LEGACY_ROOT = Path('artifacts/chapter_coupling_analysis')
FASTEST_ROOT = Path('artifacts/chapter_coupling_analysis_fastest_exact')
DEFAULT_OUTPUT_ROOTS = (LEGACY_ROOT, FASTEST_ROOT)

SCHEME_LABELS = {
    'strict_global_min_dt': '严格同步方案',
    'yield_schedule': '事件触发式方案',
    'fixed_interval_002s': '固定步长 2 s',
    'fixed_interval_003s': '固定步长 3 s',
    'fixed_interval_005s': '固定步长 5 s',
    'fixed_interval_010s': '固定步长 10 s',
    'fixed_interval_015s': '固定步长 15 s',
    'fixed_interval_030s': '固定步长 30 s',
    'fixed_interval_060s': '固定步长 60 s',
    'fixed_interval_300s': '固定步长 300 s',
}

SCHEME_STYLES = {
    'strict_global_min_dt': dict(color='#111111', linestyle='-', linewidth=2.8, zorder=6),
    'yield_schedule': dict(color='#9c6644', linestyle='--', linewidth=2.1, zorder=5),
    'fixed_interval_002s': dict(color='#1d3557', linestyle='-.', linewidth=1.9, zorder=4),
    'fixed_interval_003s': dict(color='#006d77', linestyle='-', linewidth=1.8, zorder=4),
    'fixed_interval_005s': dict(color='#2a9d8f', linestyle='--', linewidth=1.8, zorder=4),
    'fixed_interval_010s': dict(color='#e9c46a', linestyle='-.', linewidth=1.8, zorder=4),
    'fixed_interval_015s': dict(color='#f4a261', linestyle=':', linewidth=2.2, zorder=5),
    'fixed_interval_030s': dict(color='#e76f51', linestyle='--', linewidth=1.9, zorder=4),
    'fixed_interval_060s': dict(color='#b56576', linestyle='-.', linewidth=1.9, zorder=4),
    'fixed_interval_300s': dict(color='#6d597a', linestyle=':', linewidth=1.9, zorder=4),
}

SMALL_FAMILY_LABELS = {
    'frontal_basin_fill': '正向耦合蓄水算例',
    'lateral_overtopping_return': '侧向耦合漫顶—回流算例',
    'early_arrival_pulse': '正向耦合快速首达算例',
    'regime_switch_backwater_or_mixed': '混合耦合回水—流态切换算例',
}

BENCHMARK_TITLE = '河道—三分区洪泛平原综合算例'
BENCHMARK_LABEL = '正向—侧向复合耦合综合算例'

PROBE_LABELS = {
    'upstream_1d': '上游断面',
    'mainstem_mid': '主河道中游断面',
    'downstream_1d': '下游断面',
    'mainstem_right_q': '主河道出口断面',
    'basin_probe': '二维蓄水区测点',
    'floodplain_probe': '二维洪泛区测点',
    'arrival_plain_probe': '二维首达测点',
    'upper_plain_probe': '上游洪泛区测点',
    'lower_plain_probe': '下游洪泛区测点',
    'arrival_downstream': '下游首达断面',
    'arrival_upstream': '上游首达断面',
    'fp1_probe': '洪泛区 1 测点',
    'fp2_probe': '洪泛区 2 测点',
    'fp3_probe': '洪泛区 3 测点',
}

PARTITION_LABELS = {
    'Floodplain_1': '洪泛区 1',
    'Floodplain_2': '洪泛区 2',
    'Floodplain_3': '洪泛区 3',
}


LINK_LABELS = {
    'fp1_overtop': '漫顶交换链路 1',
    'fp2_return': '回流交换链路',
    'fp3_overtop': '漫顶交换链路 3',
    'front_main': '正向边界链路',
    'return_link': '回流交换链路',
    'early_link': '快速首达交换链路',
    'backwater_link': '回水交换链路',
    'mixed_return_link': '混合回流链路',
}

SMALL_PROBE_CONFIG = {
    'frontal_basin_fill': ('mainstem_mid', 'basin_probe'),
    'lateral_overtopping_return': ('mainstem_mid', 'floodplain_probe'),
    'early_arrival_pulse': ('arrival_downstream', 'arrival_plain_probe'),
    'regime_switch_backwater_or_mixed': ('mainstem_mid', 'upper_plain_probe'),
}

SMALL_SWEEP_SUFFIXES = [
    'strict_global_min_dt',
    'fixed_interval_002s',
    'fixed_interval_005s',
    'fixed_interval_015s',
    'fixed_interval_060s',
    'fixed_interval_300s',
]

BENCHMARK_COMPARE_SUFFIXES = [
    'strict_global_min_dt',
    'yield_schedule',
    'fixed_interval_002s',
    'fixed_interval_003s',
    'fixed_interval_005s',
    'fixed_interval_010s',
    'fixed_interval_015s',
]

BENCHMARK_EXCHANGE_SUFFIXES = [
    'strict_global_min_dt',
    'yield_schedule',
    'fixed_interval_005s',
    'fixed_interval_015s',
]

BENCHMARK_MAP_SUFFIXES = [
    'strict_global_min_dt',
    'yield_schedule',
    'fixed_interval_005s',
    'fixed_interval_015s',
]


def parse_cli(default_roots: Sequence[Path] = DEFAULT_OUTPUT_ROOTS) -> list[Path]:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-root', action='append', dest='roots', default=[])
    args = parser.parse_args()
    if args.roots:
        return [Path(root) for root in args.roots]
    return [Path(root) for root in default_roots]


def output_roots(root: Path | str | None) -> list[Path]:
    if root is None:
        return [Path(item) for item in DEFAULT_OUTPUT_ROOTS]
    return [Path(root)]


def scheme_label(suffix: str) -> str:
    return SCHEME_LABELS[suffix]


def scheme_style(suffix: str) -> dict[str, object]:
    return dict(SCHEME_STYLES[suffix])


def probe_label(probe_id: str) -> str:
    return PROBE_LABELS.get(probe_id, probe_id)


def link_label_cn(link_id: str) -> str:
    return LINK_LABELS.get(link_id, link_id)


def small_family_label(family: str) -> str:
    return SMALL_FAMILY_LABELS.get(family, family)


def file_stem_label(path_stem: str) -> str:
    return Path(path_stem).name


def print_input_files(output_name: str, paths: Sequence[Path], *, provenance: str | None = None) -> None:
    print(f'[4.5 CN Plot] {output_name}')
    if provenance:
        print(f'  provenance: {provenance}')
    for path in paths:
        print(f'  input: {path}')


def require_paths(paths: Sequence[Path]) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError('Missing required input files:\n' + '\n'.join(missing))


def save_png_pdf(fig, plot_dir: Path, stem: str) -> None:
    plot_dir.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({}):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='This figure includes Axes that are not compatible with tight_layout, so results might be incorrect\.')
            fig.tight_layout()
        fig.savefig(plot_dir / f'{stem}.png', dpi=180, facecolor='white', bbox_inches='tight')
        fig.savefig(plot_dir / f'{stem}.pdf', facecolor='white', bbox_inches='tight')
    plt.close(fig)


def legacy_small_source_root() -> Path:
    return LEGACY_ROOT


def benchmark_family(root: Path) -> str:
    for row in load_chapter_summary_rows(root):
        family = row['scenario_family']
        if 'test7' in family:
            return family
    raise KeyError(f'No benchmark family found under {root}')


def benchmark_case_name(root: Path, suffix: str) -> str:
    return f'{benchmark_family(root)}_{suffix}'


def small_case_name(family: str, suffix: str) -> str:
    return f'{family}_{suffix}'


def available_small_suffixes(family: str, source_root: Path | None = None) -> list[str]:
    rows = load_chapter_small_summary_rows(legacy_small_source_root() if source_root is None else source_root)
    names = {row['case_name'] for row in rows if row['scenario_family'] == family}
    return [suffix for suffix in SMALL_SWEEP_SUFFIXES if f'{family}_{suffix}' in names]


def load_case_rows_with_inputs(root: Path, case_name: str, filename: str) -> tuple[list[dict[str, str]], list[Path]]:
    path = root / 'cases' / case_name / filename
    require_paths([path])
    return chapter_case_rows(root, case_name, filename), [path]


def load_case_json_with_inputs(root: Path, case_name: str, filename: str) -> tuple[dict[str, object], list[Path]]:
    path = root / 'cases' / case_name / filename
    require_paths([path])
    return chapter_case_json(root, case_name, filename), [path]


def load_mesh_with_inputs(root: Path, case_name: str) -> tuple[dict[str, object], list[Path]]:
    cache_dir = root / 'cases' / case_name / 'plot_cache'
    npz = cache_dir / 'mesh_geometry.npz'
    meta = cache_dir / 'mesh_geometry.json'
    require_paths([npz, meta])
    return load_mesh_geometry_for_case(root, case_name), [npz, meta]


def choose_small_source_root(output_root: Path) -> tuple[Path, str]:
    source_root = legacy_small_source_root()
    provenance = 'small-case richer interval sweep read from artifacts/chapter_coupling_analysis'
    if output_root == source_root:
        provenance = 'small-case data read from output root'
    return source_root, provenance


def summary_row_map(rows: Sequence[Mapping[str, str]]) -> dict[str, Mapping[str, str]]:
    return {row['case_name']: row for row in rows}


def float_series(rows: Sequence[Mapping[str, str]], x_key: str, y_key: str, *, filter_key: str | None = None, filter_value: str | None = None) -> tuple[list[float], list[float]]:
    filtered = list(rows)
    if filter_key is not None:
        filtered = [row for row in filtered if row.get(filter_key) == filter_value]
    assert_nonempty_dataframe(filtered, f'{y_key} series filtered by {filter_key}={filter_value}')
    pairs = sorted((float(row[x_key]), float(row[y_key])) for row in filtered)
    return [pair[0] for pair in pairs], [pair[1] for pair in pairs]


def interval_value(row: Mapping[str, str]) -> float:
    value = row.get('exchange_interval', '')
    return float(value)


def fixed_interval_rows(rows: Sequence[Mapping[str, str]], scenario_family: str) -> list[Mapping[str, str]]:
    filtered = [row for row in rows if row['scenario_family'] == scenario_family and row['scheduler_mode'] == 'fixed_interval']
    return sorted(filtered, key=interval_value)


def draw_partition_polygons(ax, partitions: Mapping[str, Sequence[Sequence[float]]]) -> None:
    palette = ['#d9ecf2', '#fcecc9', '#e8dff5', '#e2f0cb']
    for idx, (name, polygon) in enumerate(partitions.items()):
        closed = list(polygon) + [polygon[0]]
        xs = [point[0] for point in closed]
        ys = [point[1] for point in closed]
        ax.fill(xs, ys, facecolor=palette[idx % len(palette)], edgecolor='0.65', alpha=0.42)
        centroid_x = sum(point[0] for point in polygon) / len(polygon)
        centroid_y = sum(point[1] for point in polygon) / len(polygon)
        ax.text(
            centroid_x,
            centroid_y,
            PARTITION_LABELS.get(name, name.replace('_', ' ')),
            ha='center',
            va='center',
            fontsize=8.5,
            bbox={'facecolor': 'white', 'edgecolor': '0.7', 'alpha': 0.92, 'pad': 1.8},
        )


def _probe_centroid(probe: Mapping[str, object]) -> tuple[float, float]:
    polygon = probe['polygon']
    cx = sum(point[0] for point in polygon) / len(polygon)
    cy = sum(point[1] for point in polygon) / len(polygon)
    return float(cx), float(cy)


def draw_case_schematic(ax, geometry: Mapping[str, object], *, title: str) -> None:
    floodplain = geometry['floodplain_polygon']
    closed = list(floodplain) + [floodplain[0]]
    ax.fill([p[0] for p in closed], [p[1] for p in closed], facecolor='#f6fbff', edgecolor='black', linewidth=1.6, alpha=1.0)
    draw_partition_polygons(ax, geometry.get('partitions', {}))

    if geometry.get('breaklines'):
        lines = [np.asarray(line, dtype=float) for line in geometry['breaklines']]
        ax.add_collection(LineCollection(lines, colors='0.82', linewidths=0.8, linestyles='-'))

    centerline = np.asarray(geometry['centerline'], dtype=float)
    ax.plot(centerline[:, 0], centerline[:, 1], color='#1d3557', lw=3.0, label='一维河道中心线')

    for idx, line in enumerate(geometry.get('levee_lines', [])):
        arr = np.asarray(line, dtype=float)
        ax.plot(arr[:, 0], arr[:, 1], color='#8c4f2c', lw=2.2, linestyle='--', label='堤线' if idx == 0 else None)

    for idx, (name, line) in enumerate(geometry.get('lateral_lines', {}).items()):
        arr = np.asarray(line, dtype=float)
        ax.plot(arr[:, 0], arr[:, 1], color='#d17b0f', lw=3.0, label='侧向交换线' if idx == 0 else None)
        ax.text(arr[:, 0].mean(), arr[:, 1].mean() + 1.0, link_label_cn(name), fontsize=8, ha='center')

    for idx, (name, line) in enumerate(geometry.get('direct_connection_lines', {}).items()):
        arr = np.asarray(line, dtype=float)
        ax.plot(arr[:, 0], arr[:, 1], color='#7b2cbf', lw=3.0, label='正向耦合边界' if idx == 0 else None)
        ax.text(arr[:, 0].mean() + 1.0, arr[:, 1].mean(), link_label_cn(name), fontsize=8, va='center')

    for probe in geometry.get('one_d_probes', []):
        river_x = centerline[0, 0] + (centerline[-1, 0] - centerline[0, 0]) * 0.5
        river_y = centerline[:, 1].mean()
        cell_id = float(probe.get('cell_id', 0.0))
        x_pos = np.interp(cell_id, [0.0, max(cell_id, 1.0) + 2.0], [centerline[0, 0] + 0.12 * (centerline[-1, 0] - centerline[0, 0]), centerline[-1, 0] - 0.12 * (centerline[-1, 0] - centerline[0, 0])])
        ax.plot([x_pos], [river_y], marker='^', color='black', markersize=6)
        ax.text(x_pos, river_y + 2.4, probe_label(str(probe['probe_id'])), fontsize=8, ha='center')

    for probe in geometry.get('two_d_probes', []):
        cx, cy = _probe_centroid(probe)
        ax.plot([cx], [cy], marker='o', color='#c1121f', markersize=5)
        ax.text(cx, cy + 2.4, probe_label(str(probe['probe_id'])), fontsize=8, ha='center')

    ax.set_aspect('equal', adjustable='box')
    ax.set_title(title)
    ax.set_xlabel('x / m')
    ax.set_ylabel('y / m')
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        unique = dict(zip(labels, handles))
        ax.legend(unique.values(), unique.keys(), fontsize=7.5, ncol=2, loc='upper center', bbox_to_anchor=(0.5, -0.08))


def draw_composite_geometry_mesh(ax, root: Path, case_name: str) -> list[Path]:
    geometry, geom_inputs = load_case_json_with_inputs(root, case_name, 'geometry.json')
    mesh_geometry, mesh_inputs = load_mesh_with_inputs(root, case_name)
    draw_mesh_outline(ax, mesh_geometry, facecolor='#fcfcfd', edgecolor='0.77', linewidth=0.18, alpha=1.0)
    floodplain = geometry['floodplain_polygon']
    closed = list(floodplain) + [floodplain[0]]
    ax.plot([p[0] for p in closed], [p[1] for p in closed], color='black', lw=1.8, label='洪泛区边界')
    centerline = np.asarray(geometry['centerline'], dtype=float)
    ax.plot(centerline[:, 0], centerline[:, 1], color='#1d3557', lw=3.0, label='一维主河道')
    draw_partition_polygons(ax, geometry.get('partitions', {}))

    xmid = 0.55 * centerline[0, 0] + 0.45 * centerline[-1, 0]
    ymid = float(np.mean(centerline[:, 1]))
    ax.annotate('', xy=(xmid + 10.0, ymid + 6.5), xytext=(xmid - 10.0, ymid + 6.5), arrowprops=dict(arrowstyle='->', color='#1d3557', lw=1.6))
    ax.text(xmid, ymid + 10.0, '河道主流方向', color='#1d3557', fontsize=8.5, ha='center')

    for idx, (name, line) in enumerate(geometry.get('lateral_lines', {}).items()):
        arr = np.asarray(line, dtype=float)
        label = '侧向交换界面' if idx == 0 else None
        ax.plot(arr[:, 0], arr[:, 1], color='#d17b0f', lw=2.6, label=label)
        ax.text(arr[:, 0].mean(), arr[:, 1].mean() + 5.5, link_label_cn(name), fontsize=8, ha='center', bbox={'facecolor': 'white', 'edgecolor': 'none', 'alpha': 0.88, 'pad': 0.6})
    for idx, (name, line) in enumerate(geometry.get('direct_connection_lines', {}).items()):
        arr = np.asarray(line, dtype=float)
        label = '正向耦合边界' if idx == 0 else None
        ax.plot(arr[:, 0], arr[:, 1], color='#7b2cbf', lw=2.6, label=label)
        ax.text(arr[:, 0].mean() + 7.0, arr[:, 1].mean() + 10.0, link_label_cn(name), fontsize=8, va='center', bbox={'facecolor': 'white', 'edgecolor': 'none', 'alpha': 0.88, 'pad': 0.6})

    control_probe = next((probe for probe in geometry.get('one_d_probes', []) if str(probe.get('probe_id')) == 'mainstem_mid'), None)
    if control_probe is not None:
        cx = centerline[0, 0] + (centerline[-1, 0] - centerline[0, 0]) * 0.50
        cy = float(np.mean(centerline[:, 1]))
        ax.plot([cx], [cy], marker='^', color='black', markersize=6)
        ax.text(cx, cy + 10.0, probe_label(str(control_probe['probe_id'])), fontsize=7.8, ha='center', bbox={'facecolor':'white','edgecolor':'0.8','alpha':0.92,'pad':1.2})

    ax.text(centerline[0,0] - 6.0, ymid + 11.0, '上游来水边界', fontsize=8.2, ha='left')
    ax.text(centerline[-1,0] - 8.0, ymid - 11.0, '下游出流边界', fontsize=8.2, ha='right')
    ax.set_title('综合案例耦合位置示意图')
    ax.set_xlabel('横向距离 / m')
    ax.set_ylabel('纵向距离 / m')
    handles, labels = ax.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    ax.legend(unique.values(), unique.keys(), fontsize=7.5, ncol=4, loc='upper center', bbox_to_anchor=(0.5, -0.10))
    return geom_inputs + mesh_inputs


def plot_scheme_lines(ax, x: Sequence[float], y: Sequence[float], suffix: str) -> None:
    ax.plot(x, y, label=scheme_label(suffix), **scheme_style(suffix))


def _resample_series(times: Sequence[float], values: Sequence[float], dt: float) -> tuple[list[float], list[float]]:
    x = np.asarray(times, dtype=float)
    y = np.asarray(values, dtype=float)
    if x.size <= 2:
        return x.tolist(), y.tolist()
    unique_x, unique_idx = np.unique(x, return_index=True)
    unique_y = y[unique_idx]
    if unique_x.size <= 2:
        return unique_x.tolist(), unique_y.tolist()
    start = float(unique_x[0])
    end = float(unique_x[-1])
    grid = np.arange(start, end + 0.5 * float(dt), float(dt), dtype=float)
    if grid.size == 0 or grid[-1] < end:
        grid = np.append(grid, end)
    elif grid[-1] > end:
        grid[-1] = end
    resampled = np.interp(grid, unique_x, unique_y)
    return grid.tolist(), resampled.tolist()


def plot_process_compare(
    output_root: Path,
    source_root: Path,
    family: str,
    probe_1d: str,
    probe_2d: str,
    suffixes: Sequence[str],
    *,
    title: str,
    stem: str,
    zoom_xlim: tuple[float, float] | None = None,
    reference_underlay: bool = False,
    resample_dt: float | None = None,
) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(9.2, 7.2), sharex=True)
    input_paths: list[Path] = []
    for suffix in suffixes:
        case_name = small_case_name(family, suffix)
        rows_1d, paths_1d = load_case_rows_with_inputs(source_root, case_name, 'stage_timeseries_1d.csv')
        rows_2d, paths_2d = load_case_rows_with_inputs(source_root, case_name, 'stage_timeseries_2d.csv')
        input_paths.extend(paths_1d + paths_2d)
        x1, y1 = float_series(rows_1d, 'time', 'stage', filter_key='probe_id', filter_value=probe_1d)
        x2, y2 = float_series(rows_2d, 'time', 'stage', filter_key='probe_id', filter_value=probe_2d)
        if resample_dt is not None:
            x1, y1 = _resample_series(x1, y1, float(resample_dt))
            x2, y2 = _resample_series(x2, y2, float(resample_dt))
        style = scheme_style(suffix)
        if reference_underlay and suffix == 'strict_global_min_dt':
            style['zorder'] = 1
            style['alpha'] = 0.9
        axes[0].plot(x1, y1, label=scheme_label(suffix), **style)
        axes[1].plot(x2, y2, label=scheme_label(suffix), **style)
    axes[0].set_ylabel(f'{probe_label(probe_1d)}\n水位 / m')
    axes[1].set_ylabel(f'{probe_label(probe_2d)}\n水位 / m')
    axes[1].set_xlabel('时间 / s')
    axes[0].set_title(title)
    axes[0].legend(ncol=3, fontsize=7.5)
    if zoom_xlim is not None:
        axes[0].set_xlim(*zoom_xlim)
    save_png_pdf(fig, ensure_plot_dir(output_root), stem)
    print_input_files(stem, input_paths, provenance=f'source_root={source_root}')


def plot_small_rmse(output_root: Path, family: str, *, stem: str, title: str) -> None:
    source_root, provenance = choose_small_source_root(output_root)
    rows = load_chapter_small_summary_rows(source_root)
    rows = fixed_interval_rows(rows, family)
    assert_nonempty_dataframe(rows, f'summary rows for {family}')
    x = [interval_value(row) for row in rows]
    y = [float(row['stage_rmse']) for row in rows]
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ax.plot(x, y, marker='o', color='#1d3557', linewidth=2.0)
    ax.set_xscale('log')
    ax.set_xlabel('耦合时间步长 / s')
    ax.set_ylabel('水位 RMSE / m')
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    save_png_pdf(fig, ensure_plot_dir(output_root), stem)
    print_input_files(stem, [source_root / 'summaries' / 'summary_table_small_cases.csv'], provenance=provenance)


def _wet_union(geometry: Mapping[str, object], values: np.ndarray, depth_threshold: float = 0.02):
    polygons = [Polygon(poly) for poly, value in zip(geometry['polygons'], values) if float(value) >= depth_threshold]
    if not polygons:
        return None
    return unary_union(polygons)


def _plot_union_boundary(ax, union_geometry, *, color: str, linestyle: str, linewidth: float, label: str):
    if union_geometry is None or union_geometry.is_empty:
        return
    geometries = [union_geometry] if union_geometry.geom_type == 'Polygon' else list(union_geometry.geoms)
    pending = label
    for polygon in geometries:
        x, y = polygon.exterior.xy
        ax.plot(x, y, color=color, linestyle=linestyle, linewidth=linewidth, label=pending)
        pending = ''


def benchmark_compare_suffixes() -> list[str]:
    return list(BENCHMARK_COMPARE_SUFFIXES)


def benchmark_exchange_suffixes() -> list[str]:
    return list(BENCHMARK_EXCHANGE_SUFFIXES)


def benchmark_map_suffixes() -> list[str]:
    return list(BENCHMARK_MAP_SUFFIXES)
