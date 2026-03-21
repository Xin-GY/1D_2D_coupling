from __future__ import annotations

# Inputs:
# - docs/chapter_coupling_time_discretization.md
# - docs/figure_manifest.md
# - artifacts/chapter_coupling_analysis[_fastest_exact]/cases/<benchmark>/geometry.json
# - artifacts/chapter_coupling_analysis[_fastest_exact]/cases/<benchmark>/plot_cache/mesh_geometry.*

from pathlib import Path
import numpy as np

from scripts._plot_ch4_5_common import (
    BENCHMARK_TITLE,
    benchmark_case_name,
    draw_composite_geometry_mesh,
    output_roots,
    parse_cli,
    print_input_files,
    save_png_pdf,
)
from scripts._plot_common import ensure_plot_dir, plt


def _draw_coupling_schematic(ax, title: str, *, frontal: bool, lateral: bool, composite: bool = False) -> None:
    ax.set_title(title)
    ax.add_patch(plt.Rectangle((0.05, 0.48), 0.90, 0.15, facecolor='#3d5a80', alpha=0.95))
    ax.text(0.50, 0.555, '一维河道', color='white', ha='center', va='center', fontsize=10)
    ax.add_patch(plt.Rectangle((0.08, 0.08), 0.84, 0.25, facecolor='#d9ecf2', edgecolor='0.75', alpha=0.95))
    ax.text(0.50, 0.205, '二维洪泛区', ha='center', va='center', fontsize=9.5)
    if lateral:
        ax.plot([0.30, 0.70], [0.46, 0.46], color='#bc6c25', lw=4)
        ax.annotate('', xy=(0.55, 0.35), xytext=(0.49, 0.47), arrowprops=dict(arrowstyle='->', color='#bc6c25', lw=1.8))
        ax.annotate('', xy=(0.38, 0.46), xytext=(0.44, 0.33), arrowprops=dict(arrowstyle='->', color='#7c3f58', lw=1.8))
        ax.text(0.50, 0.31, '侧向堰流交换', ha='center', fontsize=8.5)
    if frontal:
        ax.plot([0.92, 0.92], [0.28, 0.74], color='#7b2cbf', lw=4)
        ax.annotate('', xy=(0.90, 0.62), xytext=(0.78, 0.62), arrowprops=dict(arrowstyle='->', color='#355070', lw=1.8))
        ax.text(0.67, 0.66, '一维提供流量', fontsize=8.5)
        ax.annotate('', xy=(0.78, 0.46), xytext=(0.90, 0.46), arrowprops=dict(arrowstyle='->', color='#6d597a', lw=1.8))
        ax.text(0.66, 0.39, '二维提供水位', fontsize=8.5)
    if composite:
        ax.text(0.50, 0.88, '正向与侧向交换并存', ha='center', fontsize=9, color='#1d3557')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')


def _render_for_root(root: Path) -> None:
    plot_dir = ensure_plot_dir(root)
    docs_inputs = [Path('docs/chapter_coupling_time_discretization.md'), Path('docs/figure_manifest.md')]

    fig, axes = plt.subplots(1, 4, figsize=(14, 3.8), sharey=True)
    configs = [
        ('正向耦合', True, False, False),
        ('侧向耦合', False, True, False),
        ('混合耦合', True, True, False),
        ('复合耦合', True, True, True),
    ]
    for ax, (title, frontal, lateral, composite) in zip(axes, configs):
        _draw_coupling_schematic(ax, title, frontal=frontal, lateral=lateral, composite=composite)
    save_png_pdf(fig, plot_dir, 'coupling_schematic_cn')
    print_input_files('coupling_schematic_cn', docs_inputs, provenance='schematic drawn from chapter documentation constraints')

    case_name = benchmark_case_name(root, 'strict_global_min_dt')
    fig, ax = plt.subplots(figsize=(11.5, 5.6))
    inputs = draw_composite_geometry_mesh(ax, root, case_name)
    ax.set_title('综合案例耦合位置示意图')
    save_png_pdf(fig, plot_dir, 'composite_case_geometry_mesh_cn')
    print_input_files('composite_case_geometry_mesh_cn', inputs, provenance=f'benchmark_case={case_name}')


def main(root: Path | str | None = None) -> None:
    for output_root in output_roots(root):
        _render_for_root(Path(output_root))


if __name__ == '__main__':
    cli_roots = parse_cli()
    if len(cli_roots) == 1:
        main(cli_roots[0])
    else:
        main()
