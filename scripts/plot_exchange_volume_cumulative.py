from __future__ import annotations

from pathlib import Path

import numpy as np

from scripts._plot_common import chapter_case_rows, ensure_plot_dir, link_label, load_chapter_summary_rows, plt, save_figure


LINKS = ['fp1_overtop', 'fp2_return', 'front_main']


def _benchmark_case(root: Path, suffix: str) -> str:
    for row in load_chapter_summary_rows(root):
        if 'test7' in row['scenario_family'] and row['case_name'].endswith(suffix):
            return row['case_name']
    raise KeyError(f'No benchmark case with suffix {suffix}')


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    plot_dir = ensure_plot_dir(root)
    case_name = _benchmark_case(root, 'fixed_interval_015s')
    rows = chapter_case_rows(root, case_name, 'exchange_link_timeseries.csv')
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for link_id in LINKS:
        filtered = sorted([row for row in rows if row['link_id'] == link_id], key=lambda row: float(row['time']))
        times = [float(row['time']) for row in filtered]
        cumulative = np.cumsum([float(row['dV_exchange']) for row in filtered])
        ax.plot(times, cumulative, label=link_label(link_id))
    ax.set_title('代表性界面累计交换体积')
    ax.set_xlabel('时间 (s)')
    ax.set_ylabel('累计交换体积 (m$^3$)')
    ax.legend()
    save_figure(fig, plot_dir / 'exchange_volume_cumulative.png')


if __name__ == '__main__':
    main()
