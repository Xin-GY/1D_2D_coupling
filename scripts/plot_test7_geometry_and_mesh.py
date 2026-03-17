from __future__ import annotations

from pathlib import Path

from scripts._plot_common import chapter_case_json, chapter_case_rows, ensure_plot_dir, load_chapter_summary_rows, plt, save_figure


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
    mesh_rows = chapter_case_rows(root, case_name, 'two_d_field_summary.csv')

    fig, ax = plt.subplots(figsize=(10, 4.5))
    floodplain = geometry['floodplain_polygon'] + [geometry['floodplain_polygon'][0]]
    ax.plot([p[0] for p in floodplain], [p[1] for p in floodplain], color='black', lw=2, label='Floodplain boundary')
    centerline = geometry['centerline']
    ax.plot([p[0] for p in centerline], [p[1] for p in centerline], color='#355070', lw=3, label='1D river')
    for name, line in geometry['lateral_lines'].items():
        ax.plot([p[0] for p in line], [p[1] for p in line], lw=3, label=name)
    for line in geometry['direct_connection_lines'].values():
        ax.plot([p[0] for p in line], [p[1] for p in line], color='#7b2cbf', lw=3, label='frontal link')
    for name, polygon in geometry['partitions'].items():
        centroid_x = sum(point[0] for point in polygon) / len(polygon)
        centroid_y = sum(point[1] for point in polygon) / len(polygon)
        ax.text(centroid_x, centroid_y, name.replace('_', ' '), ha='center', va='center', fontsize=9)
    xs = [float(row['x']) for row in mesh_rows]
    ys = [float(row['y']) for row in mesh_rows]
    ax.scatter(xs, ys, s=4, color='0.65', alpha=0.7, label='2D centroids')
    for probe in geometry['one_d_probes']:
        ax.scatter([probe['cell_id'] * 10.0], [centerline[0][1]], marker='^', color='black')
        ax.text(probe['cell_id'] * 10.0, centerline[0][1] + 10.0, probe['probe_id'], fontsize=8)
    for probe in geometry['two_d_probes']:
        cx = sum(point[0] for point in probe['polygon']) / len(probe['polygon'])
        cy = sum(point[1] for point in probe['polygon']) / len(probe['polygon'])
        ax.scatter([cx], [cy], marker='o', color='#d62828')
        ax.text(cx, cy + 10.0, probe['probe_id'], fontsize=8)
    ax.set_title(f'{family} geometry / mesh')
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.legend(loc='upper right', fontsize=7)
    save_figure(fig, plot_dir / 'test7_geometry_and_mesh.png')


if __name__ == '__main__':
    main()
