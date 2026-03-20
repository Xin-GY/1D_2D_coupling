from __future__ import annotations

from pathlib import Path

from scripts._plot_common import case_name_to_display, ensure_plot_dir, load_chapter_timing_rows, plt, save_figure


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    rows = load_chapter_timing_rows(root)
    fig, ax = plt.subplots(figsize=(11, 5))
    labels = [case_name_to_display(row['case_name']) for row in rows[:12]]
    one_d = [float(row['one_d_share']) for row in rows[:12]]
    two_d = [float(row['two_d_share']) for row in rows[:12]]
    boundary = [float(row['boundary_share']) for row in rows[:12]]
    exchange = [float(row['exchange_manager_share']) for row in rows[:12]]
    misc = [float(row['misc_io_share']) for row in rows[:12]]
    bottoms = [0.0] * len(labels)
    for values, name, color in [
        (one_d, '一维推进', '#355070'),
        (two_d, '二维 GPU 核函数', '#457b9d'),
        (boundary, '边界更新', '#6d597a'),
        (exchange, '交换管理', '#b56576'),
        (misc, '杂项/IO', '#adb5bd'),
    ]:
        ax.bar(labels, values, bottom=bottoms, label=name, color=color)
        bottoms = [bottom + value for bottom, value in zip(bottoms, values)]
    ax.set_title('不同策略的计算成本占比')
    ax.set_xlabel('工况')
    ax.set_ylabel('耗时占比')
    ax.tick_params(axis='x', rotation=60)
    ax.legend(ncol=5, fontsize=7)
    save_figure(fig, ensure_plot_dir(root) / 'cost_share_stacked.png')


if __name__ == '__main__':
    main()
