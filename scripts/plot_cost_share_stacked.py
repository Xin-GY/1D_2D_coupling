from __future__ import annotations

import argparse
from pathlib import Path

from scripts._benchmark_1200_cost_common import write_benchmark_1200_cost_summary
from scripts._plot_common import ensure_plot_dir, load_chapter_timing_rows, plt, save_figure

CASE_LABELS = {
    'strict_global_min_dt': '严格同步方案',
    'fixed_interval_002s': '固定步长 2 s',
    'fixed_interval_005s': '固定步长 5 s',
    'fixed_interval_015s': '固定步长 15 s',
    'fixed_interval_060s': '固定步长 60 s',
    'fixed_interval_300s': '固定步长 300 s',
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Render cost-share figure.')
    parser.add_argument('--output-root', default='artifacts/chapter_coupling_analysis')
    parser.add_argument('--rerun-root', default='')
    return parser.parse_args()


def _load_rows(output_root: Path, rerun_root: str):
    if rerun_root:
        csv_path, _, rows = write_benchmark_1200_cost_summary(Path(rerun_root))
        print('timing summary source:', csv_path)
        return rows
    return load_chapter_timing_rows(output_root)


def _suffix(row: dict[str, str]) -> str:
    if row.get('case_suffix'):
        return str(row['case_suffix'])
    case_name = str(row.get('case_name', ''))
    for suffix in CASE_LABELS:
        if case_name.endswith(suffix):
            return suffix
    return case_name


def _label(row: dict[str, str]) -> str:
    suffix = _suffix(row)
    return CASE_LABELS.get(suffix, row.get('case_name', suffix))


def main(root: Path | str | None = None, rerun_root: str = '') -> None:
    if root is None:
        args = parse_args()
        output_root = Path(args.output_root)
        rerun_root = args.rerun_root
    else:
        output_root = Path(root)
    rows = _load_rows(output_root, rerun_root)
    fig, ax = plt.subplots(figsize=(9.6, 5.2))
    labels = [_label(row) for row in rows]
    if rerun_root:
        strict_wall = float(next(row['wall_clock_seconds'] for row in rows if _suffix(row) == 'strict_global_min_dt'))
        one_d = [float(row['one_d_advance_time']) / strict_wall for row in rows]
        two_d = [float(row['two_d_gpu_kernel_time']) / strict_wall for row in rows]
        boundary = [float(row['boundary_update_time']) / strict_wall for row in rows]
        exchange = [float(row['exchange_manager_time']) / strict_wall for row in rows]
        misc = [float(row['misc_io_time']) / strict_wall for row in rows]
        total = [float(row['relative_cost_ratio']) for row in rows]
        bottoms = [0.0] * len(labels)
        for values, name, color in [
            (one_d, '一维推进', '#355070'),
            (two_d, '二维 GPU 核函数', '#457b9d'),
            (boundary, '边界更新', '#6d597a'),
            (exchange, '交换管理', '#b56576'),
            (misc, '杂项/IO', '#adb5bd'),
        ]:
            ax.bar(labels, values, bottom=bottoms, label=name, color=color, width=0.72)
            bottoms = [bottom + value for bottom, value in zip(bottoms, values)]
        for idx, value in enumerate(total):
            ax.text(idx, value + 0.035, f'{value:.2f}', ha='center', va='bottom', fontsize=8)
        ax.axhline(1.0, color='#444444', linestyle='--', linewidth=0.8, alpha=0.6)
        ax.set_title('综合测试案例相对时间成本构成')
        ax.set_ylabel('相对时间比')
        ax.set_ylim(0.0, max(total) * 1.14)
    else:
        one_d = [float(row['one_d_share']) for row in rows]
        two_d = [float(row['two_d_share']) for row in rows]
        boundary = [float(row['boundary_share']) for row in rows]
        exchange = [float(row['exchange_manager_share']) for row in rows]
        misc = [float(row['misc_io_share']) for row in rows]
        bottoms = [0.0] * len(labels)
        for values, name, color in [
            (one_d, '一维推进', '#355070'),
            (two_d, '二维 GPU 核函数', '#457b9d'),
            (boundary, '边界更新', '#6d597a'),
            (exchange, '交换管理', '#b56576'),
            (misc, '杂项/IO', '#adb5bd'),
        ]:
            ax.bar(labels, values, bottom=bottoms, label=name, color=color, width=0.72)
            bottoms = [bottom + value for bottom, value in zip(bottoms, values)]
        ax.set_title('综合测试案例计算时间成本占比')
        ax.set_ylabel('耗时占比')
        ax.set_ylim(0.0, 1.0)
    ax.set_xlabel('耦合方案', labelpad=10)
    ax.tick_params(axis='x', rotation=20)
    ax.legend(ncol=5, fontsize=8, loc='upper center', bbox_to_anchor=(0.5, -0.24), frameon=False)
    fig.subplots_adjust(bottom=0.30)
    save_figure(fig, ensure_plot_dir(output_root) / 'cost_share_stacked.png')


if __name__ == '__main__':
    main()
