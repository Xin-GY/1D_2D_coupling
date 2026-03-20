from __future__ import annotations

from pathlib import Path

from scripts._plot_common import chapter_case_rows, ensure_plot_dir, link_label, load_chapter_summary_rows, plt, save_figure, series_from_rows


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
    fig, axes = plt.subplots(len(LINKS), 1, figsize=(9, 7), sharex=True)
    for ax, link_id in zip(axes, LINKS):
        x, y = series_from_rows(rows, 'time', 'deta', filter_key='link_id', filter_value=link_id)
        ax.plot(x, y, label=link_id, color='#7c3f58')
        ax.axhline(0.0, color='0.7', lw=1)
        ax.set_ylabel(f'{link_label(link_id)}\nΔη (m)')
    axes[0].set_title('代表性界面水位差时序')
    axes[-1].set_xlabel('时间 (s)')
    save_figure(fig, plot_dir / 'exchange_deta_timeseries.png')


if __name__ == '__main__':
    main()
