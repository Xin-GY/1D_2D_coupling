from __future__ import annotations

from pathlib import Path

from scripts._plot_common import case_name_to_display, ensure_plot_dir, load_chapter_partition_rows, partition_label, plt, save_figure


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    rows = load_chapter_partition_rows(root)
    target_cases = [
        row for row in rows
        if row['case_name'].endswith('strict_global_min_dt')
        or row['case_name'].endswith('yield_schedule')
        or row['case_name'].endswith('fixed_interval_005s')
        or row['case_name'].endswith('fixed_interval_015s')
        or row['case_name'].endswith('fixed_interval_060s')
    ]
    partitions = sorted({row['partition'] for row in target_cases})
    cases = sorted({row['case_name'] for row in target_cases})
    fig, ax = plt.subplots(figsize=(11, 5))
    width = 0.14
    for idx, case_name in enumerate(cases):
        values = []
        for partition in partitions:
            row = next(
                (
                    row
                    for row in target_cases
                    if row['case_name'] == case_name and row['partition'] == partition
                ),
                None,
            )
            values.append(float(row['max_depth_map_difference']) if row is not None else 0.0)
        ax.bar([pos + idx * width for pos in range(len(partitions))], values, width=width, label=case_name_to_display(case_name))
    ax.set_xticks(
        [pos + width * (len(cases) - 1) / 2.0 for pos in range(len(partitions))],
        [partition_label(partition) for partition in partitions],
    )
    ax.legend(fontsize=7, ncol=3)
    ax.set_title('各洪泛区最大水深差异对比')
    ax.set_ylabel('最大水深差值 (m)')
    save_figure(fig, ensure_plot_dir(root) / 'floodplain_partition_compare.png')


if __name__ == '__main__':
    main()
