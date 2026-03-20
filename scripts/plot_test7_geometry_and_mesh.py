from __future__ import annotations

from pathlib import Path

import numpy as np

from scripts._plot_common import (
    chapter_case_json,
    draw_mesh_outline,
    ensure_plot_dir,
    family_label,
    load_chapter_summary_rows,
    load_mesh_geometry_for_case,
    partition_label,
    plt,
    probe_label,
    save_figure,
)


def _benchmark_family(rows: list[dict[str, str]]) -> str:
    for row in rows:
        family = row['scenario_family']
        if 'test7' in family:
            return family
    raise KeyError('No Test7 family found in chapter summaries')


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    plot_dir = ensure_plot_dir(root)
    summary_rows = load_chapter_summary_rows(root)
    family = _benchmark_family(summary_rows)
    case_name = f'{family}_strict_global_min_dt'
    geometry = chapter_case_json(root, case_name, 'geometry.json')
    mesh_geometry = load_mesh_geometry_for_case(root, case_name)
    bounds = np.asarray(mesh_geometry['bounds'], dtype=float)
    x_span = float(bounds[1] - bounds[0])
    y_span = float(bounds[3] - bounds[2])

    fig, ax = plt.subplots(figsize=(11.5, 5.4))
    draw_mesh_outline(ax, mesh_geometry, facecolor='#fbfbfb', edgecolor='0.72', linewidth=0.18, alpha=1.0)
    floodplain = geometry['floodplain_polygon'] + [geometry['floodplain_polygon'][0]]
    ax.plot([p[0] for p in floodplain], [p[1] for p in floodplain], color='black', lw=2, label='洪泛区边界')
    centerline = geometry['centerline']
    ax.plot([p[0] for p in centerline], [p[1] for p in centerline], color='#355070', lw=3, label='一维主河道')
    for name, line in geometry['lateral_lines'].items():
        chinese_label = '侧向漫顶界面' if 'overtop' in name else '侧向回流界面'
        ax.plot([p[0] for p in line], [p[1] for p in line], lw=3, label=chinese_label)
    for line in geometry['direct_connection_lines'].values():
        ax.plot([p[0] for p in line], [p[1] for p in line], color='#7b2cbf', lw=3, label='端部直连接口')
    partition_offsets = {
        'Floodplain_1': (-0.04 * x_span, 0.12 * y_span),
        'Floodplain_2': (0.0, -0.15 * y_span),
        'Floodplain_3': (0.04 * x_span, 0.12 * y_span),
    }
    for name, polygon in geometry['partitions'].items():
        centroid_x = sum(point[0] for point in polygon) / len(polygon)
        centroid_y = sum(point[1] for point in polygon) / len(polygon)
        dx, dy = partition_offsets.get(name, (0.0, 0.0))
        ax.text(
            centroid_x + dx,
            centroid_y + dy,
            partition_label(name),
            ha='center',
            va='center',
            fontsize=9,
            bbox={'facecolor': 'white', 'edgecolor': '0.75', 'alpha': 0.92, 'pad': 2.5},
        )
    one_d_offsets = {
        'upstream_1d': (-0.03 * x_span, 0.08 * y_span),
        'mainstem_mid': (0.0, -0.10 * y_span),
        'downstream_1d': (0.03 * x_span, 0.08 * y_span),
    }
    for idx, probe in enumerate(geometry['one_d_probes']):
        x_pos = np.interp(idx + 1, [0.0, len(geometry['one_d_probes']) + 1], [centerline[0][0] + 0.18 * x_span, centerline[-1][0] - 0.18 * x_span])
        y_pos = centerline[0][1]
        ax.plot([x_pos], [y_pos], marker='^', color='black', markersize=7, linestyle='none')
        dx, dy = one_d_offsets.get(probe['probe_id'], (0.0, 0.07 * y_span))
        ax.annotate(
            probe_label(probe['probe_id']),
            xy=(x_pos, y_pos),
            xytext=(x_pos + dx, y_pos + dy),
            textcoords='data',
            fontsize=8,
            ha='center',
            va='center',
            bbox={'facecolor': 'white', 'edgecolor': '0.8', 'alpha': 0.94, 'pad': 1.8},
            arrowprops={'arrowstyle': '-', 'color': '0.45', 'lw': 0.8},
        )
    two_d_offsets = {
        'fp1_probe': (-0.07 * x_span, 0.10 * y_span),
        'fp2_probe': (0.0, -0.11 * y_span),
        'fp3_probe': (0.07 * x_span, 0.10 * y_span),
    }
    for probe in geometry['two_d_probes']:
        cx = sum(point[0] for point in probe['polygon']) / len(probe['polygon'])
        cy = sum(point[1] for point in probe['polygon']) / len(probe['polygon'])
        ax.plot([cx], [cy], marker='o', color='#d62828', markersize=6, linestyle='none')
        dx, dy = two_d_offsets.get(probe['probe_id'], (0.0, 0.08 * y_span))
        ax.annotate(
            probe_label(probe['probe_id']),
            xy=(cx, cy),
            xytext=(cx + dx, cy + dy),
            textcoords='data',
            fontsize=8,
            ha='center',
            va='center',
            bbox={'facecolor': 'white', 'edgecolor': '0.8', 'alpha': 0.94, 'pad': 1.8},
            arrowprops={'arrowstyle': '-', 'color': '0.45', 'lw': 0.8},
        )
    ax.set_title(f'{family_label(family)}几何与网格')
    ax.set_xlabel('x 坐标')
    ax.set_ylabel('y 坐标')
    handles, labels = ax.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    ax.legend(
        unique.values(),
        unique.keys(),
        loc='upper center',
        bbox_to_anchor=(0.5, -0.10),
        ncol=3,
        fontsize=7.5,
        frameon=True,
    )
    save_figure(fig, plot_dir / 'test7_geometry_and_mesh.png')


if __name__ == '__main__':
    main()
