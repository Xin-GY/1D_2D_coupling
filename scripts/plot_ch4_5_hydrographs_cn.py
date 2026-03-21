from __future__ import annotations

# Inputs:
# - <source_root>/cases/<benchmark>/stage_timeseries_1d.csv
# - <source_root>/cases/<benchmark>/discharge_timeseries.csv
# - <source_root>/cases/<benchmark>/two_d_snapshots.csv
# - <source_root>/cases/<benchmark>/plot_cache/mesh_geometry.*

import argparse
from pathlib import Path

from matplotlib.transforms import blended_transform_factory
import numpy as np

from scripts._plot_ch4_5_common import (
    BENCHMARK_COMPARE_SUFFIXES,
    benchmark_case_name,
    output_roots,
    print_input_files,
    save_png_pdf,
    scheme_label,
    scheme_style,
)
from scripts._plot_common import (
    build_snapshot_value_array,
    chapter_case_rows,
    ensure_plot_dir,
    load_mesh_geometry_for_case,
    plt,
    render_scalar_field_on_mesh,
    shared_color_limits,
)

PROBE_ID = 'mainstem_mid'
SERIES_ID = 'mainstem_right_q'
STAGE_COMPARE_SUFFIXES = [
    'strict_global_min_dt',
    'fixed_interval_002s',
    'fixed_interval_005s',
    'fixed_interval_015s',
    'fixed_interval_060s',
    'fixed_interval_300s',
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Render chapter 4.5 benchmark hydrographs in Chinese.')
    parser.add_argument('--output-root', action='append', dest='roots', default=[])
    parser.add_argument('--source-root')
    parser.add_argument('--stage-only', action='store_true')
    return parser.parse_args()


def _resolve_benchmark_case_name(source_root: Path, suffix: str) -> str:
    try:
        return benchmark_case_name(source_root, suffix)
    except Exception:
        pattern = f'*_{suffix}'
        matches = sorted((source_root / 'cases').glob(pattern))
        for match in matches:
            if (match / 'stage_timeseries_1d.csv').exists():
                return match.name
        raise


def _load_stage_pairs(source_root: Path, suffix: str) -> tuple[list[tuple[float, float]], Path]:
    case_name = _resolve_benchmark_case_name(source_root, suffix)
    path = source_root / 'cases' / case_name / 'stage_timeseries_1d.csv'
    rows = chapter_case_rows(source_root, case_name, 'stage_timeseries_1d.csv')
    pairs = sorted((float(r['time']), float(r['stage'])) for r in rows if r['probe_id'] == PROBE_ID)
    return pairs, path


def _load_discharge_pairs(source_root: Path, suffix: str) -> tuple[list[tuple[float, float]], Path]:
    case_name = _resolve_benchmark_case_name(source_root, suffix)
    path = source_root / 'cases' / case_name / 'discharge_timeseries.csv'
    rows = chapter_case_rows(source_root, case_name, 'discharge_timeseries.csv')
    pairs = sorted((float(r['time']), float(r['discharge'])) for r in rows if r['series_id'] == SERIES_ID)
    return pairs, path


def _snapshot_layout(source_root: Path):
    strict_case = _resolve_benchmark_case_name(source_root, 'strict_global_min_dt')
    geometry = load_mesh_geometry_for_case(source_root, strict_case)
    strict_path = source_root / 'cases' / strict_case / 'two_d_snapshots.csv'
    strict_rows = chapter_case_rows(source_root, strict_case, 'two_d_snapshots.csv')
    snapshot_ids = sorted({row['snapshot_id'] for row in strict_rows}, key=lambda item: int(item.split('_')[-1]))
    snapshot_times = []
    for snapshot_id in snapshot_ids:
        filtered = [row for row in strict_rows if row['snapshot_id'] == snapshot_id]
        if not filtered:
            continue
        snapshot_times.append(float(filtered[0]['time']))
    mesh_inputs = [
        source_root / 'cases' / strict_case / 'plot_cache' / 'mesh_geometry.npz',
        source_root / 'cases' / strict_case / 'plot_cache' / 'mesh_geometry.json',
        strict_path,
    ]
    return strict_case, geometry, snapshot_ids, snapshot_times, mesh_inputs


def _load_snapshot_arrays(source_root: Path, suffix: str, snapshot_ids: list[str], geometry) -> tuple[list[np.ndarray], Path]:
    case_name = _resolve_benchmark_case_name(source_root, suffix)
    path = source_root / 'cases' / case_name / 'two_d_snapshots.csv'
    rows = chapter_case_rows(source_root, case_name, 'two_d_snapshots.csv')
    arrays = [
        build_snapshot_value_array(rows, snapshot_id, 'depth', expected_cells=int(geometry['triangles'].shape[0]))
        for snapshot_id in snapshot_ids
    ]
    return arrays, path


def _render_stage(output_root: Path, source_root: Path) -> None:
    plot_dir = ensure_plot_dir(output_root)
    input_paths: list[Path] = []

    fig = plt.figure(figsize=(12.0, 11.0))
    gs = fig.add_gridspec(2, 1, height_ratios=[3.0, 7.0], hspace=0.12)
    ax = fig.add_subplot(gs[0])
    ax_strip = fig.add_subplot(gs[1])

    xmin = None
    xmax = None
    for suffix in STAGE_COMPARE_SUFFIXES:
        pairs, path = _load_stage_pairs(source_root, suffix)
        input_paths.append(path)
        xs = [x for x, _ in pairs]
        ys = [y for _, y in pairs]
        style = scheme_style(suffix)
        if suffix == 'strict_global_min_dt':
            style['zorder'] = 0
            style['alpha'] = 0.90
            style['linewidth'] = 2.0
        else:
            style['zorder'] = 3
            style['linewidth'] = max(float(style.get('linewidth', 1.8)), 1.8)
        ax.plot(xs, ys, label=scheme_label(suffix), **style)
        if xs:
            xmin = min(xs[0], xmin) if xmin is not None else xs[0]
            xmax = max(xs[-1], xmax) if xmax is not None else xs[-1]

    snapshot_suffixes = STAGE_COMPARE_SUFFIXES
    _, geometry, snapshot_ids, snapshot_times, snapshot_inputs = _snapshot_layout(source_root)
    input_paths.extend(snapshot_inputs)
    snapshot_arrays_by_suffix = {}
    all_snapshot_arrays = []
    for suffix in snapshot_suffixes:
        arrays, path = _load_snapshot_arrays(source_root, suffix, snapshot_ids, geometry)
        snapshot_arrays_by_suffix[suffix] = arrays
        all_snapshot_arrays.extend(arrays)
        input_paths.append(path)

    spacing = min(np.diff(snapshot_times)) if len(snapshot_times) >= 2 else max((float(xmax or 1.0) - float(xmin or 0.0)) * 0.25, 1.0)
    x0 = min(-5.0, float(xmin or 0.0))
    x1 = max(float(xmax or 1.0), float(max(snapshot_times, default=float(xmax or 1.0))) + 0.55 * float(spacing))
    limits = shared_color_limits(all_snapshot_arrays)

    ax.set_xlim(x0, x1)
    ax.margins(x=0.0)
    ax.set_title('综合测试案例河道水位过程线对比图')
    ax.set_xlabel('时间 / s')
    ax.set_ylabel('水位 / m')
    ax.legend(ncol=3, fontsize=7.5)

    ax_strip.set_xlim(x0, x1)
    ax_strip.set_ylim(0.0, 1.0)
    ax_strip.set_xticks([])
    ax_strip.set_yticks([])
    for spine in ax_strip.spines.values():
        spine.set_visible(False)

    blend = blended_transform_factory(ax_strip.transData, ax_strip.transAxes)
    row_count = len(snapshot_suffixes)
    top_y = 0.88
    bottom_y = 0.08
    row_gap = 0.008
    usable_h = top_y - bottom_y - row_gap * (row_count - 1)
    row_h = usable_h / row_count
    width_data = min(max(220.0, 0.82 * float(spacing)), 0.24 * (x1 - x0))
    label_x = x0 + 0.015 * (x1 - x0)

    ax_strip.text(0.5, 0.95, '二维区域结果示意图', transform=ax_strip.transAxes, ha='center', va='center', fontsize=plt.rcParams.get('axes.titlesize', 12))

    last_mappable = None
    for col_time in snapshot_times:
        ax.axvline(float(col_time), color='0.88', linestyle='--', linewidth=0.8, zorder=1)
        ax_strip.plot([float(col_time), float(col_time)], [0.0, top_y], color='0.93', linewidth=0.7, transform=blend, zorder=0)

    for row_idx, suffix in enumerate(snapshot_suffixes):
        y_bottom = top_y - (row_idx + 1) * row_h - row_idx * row_gap
        y_center = y_bottom + 0.5 * row_h
        ax_strip.text(
            label_x,
            y_center,
            scheme_label(suffix),
            transform=blend,
            ha='left',
            va='center',
            fontsize=8.2,
            zorder=5,
        )
        arrays = snapshot_arrays_by_suffix[suffix]
        for col_idx, (time_value, values) in enumerate(zip(snapshot_times, arrays)):
            center = float(time_value)
            left = min(max(center - 0.5 * width_data, x0), x1 - width_data)
            inset = ax_strip.inset_axes([left, y_bottom, width_data, row_h], transform=blend)
            last_mappable = render_scalar_field_on_mesh(
                inset,
                geometry,
                values,
                cmap='Blues',
                limits=limits,
                nan_color='#efefef',
                mesh_edgecolor='0.72',
                mesh_linewidth=0.14,
                mesh_alpha=1.0,
            )
            inset.set_xticks([])
            inset.set_yticks([])
            inset.set_xlabel('')
            inset.set_ylabel('')
            if row_idx == 0:
                inset.set_title(f'{time_value:.0f} s', fontsize=8, pad=2)
            for spine in inset.spines.values():
                spine.set_color('0.75')
                spine.set_linewidth(0.55)

    if last_mappable is not None:
        cax = ax_strip.inset_axes([0.23, 0.012, 0.54, 0.025], transform=ax_strip.transAxes)
        cbar = fig.colorbar(last_mappable, cax=cax, orientation='horizontal')
        cbar.set_label('水深 / m', fontsize=8)
        cbar.ax.tick_params(labelsize=7)

    save_png_pdf(fig, plot_dir, 'stage_hydrographs_1d_cn')
    print_input_files('stage_hydrographs_1d_cn', input_paths, provenance=f'probe_id={PROBE_ID}; source_root={source_root}; stage_suffixes={STAGE_COMPARE_SUFFIXES}; snapshot_suffixes={snapshot_suffixes}')


def _render_discharge(output_root: Path, source_root: Path) -> None:
    plot_dir = ensure_plot_dir(output_root)
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    input_paths = []
    for suffix in BENCHMARK_COMPARE_SUFFIXES:
        pairs, path = _load_discharge_pairs(source_root, suffix)
        input_paths.append(path)
        ax.plot([x for x, _ in pairs], [y for _, y in pairs], label=scheme_label(suffix), **scheme_style(suffix))
    ax.set_title('河道—三分区洪泛平原综合算例主河道流量过程线对比图')
    ax.set_xlabel('时间 / s')
    ax.set_ylabel('流量 / m^3/s')
    ax.legend(ncol=3, fontsize=7.5)
    save_png_pdf(fig, plot_dir, 'discharge_hydrographs_1d_cn')
    print_input_files('discharge_hydrographs_1d_cn', input_paths, provenance=f'series_id={SERIES_ID}; source_root={source_root}')


def main(root: Path | str | None = None, source_root: Path | str | None = None, *, stage_only: bool = False) -> None:
    for output_root in output_roots(root):
        output_path = Path(output_root)
        source_path = Path(source_root) if source_root is not None else output_path
        _render_stage(output_path, source_path)
        if not stage_only:
            _render_discharge(output_path, source_path)


if __name__ == '__main__':
    args = parse_args()
    roots = [Path(item) for item in args.roots] if args.roots else None
    if roots is None:
        main(source_root=args.source_root, stage_only=args.stage_only)
    elif len(roots) == 1:
        main(roots[0], source_root=args.source_root, stage_only=args.stage_only)
    else:
        for root in roots:
            main(root, source_root=args.source_root, stage_only=args.stage_only)
