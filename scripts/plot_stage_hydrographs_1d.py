from __future__ import annotations

from pathlib import Path

from scripts._plot_common import (
    case_label,
    chapter_case_rows,
    ensure_plot_dir,
    load_chapter_summary_rows,
    plt,
    probe_label,
    save_figure,
    series_from_rows,
)


CASE_SUFFIXES = ['strict_global_min_dt', 'yield_schedule', 'fixed_interval_002s', 'fixed_interval_003s', 'fixed_interval_005s', 'fixed_interval_010s', 'fixed_interval_015s', 'fixed_interval_030s', 'fixed_interval_060s', 'fixed_interval_300s']
PROBES = ['upstream_1d', 'mainstem_mid', 'downstream_1d']


def _benchmark_family(rows: list[dict[str, str]]) -> str:
    for row in rows:
        if 'test7' in row['scenario_family']:
            return row['scenario_family']
    raise KeyError('No Test7 family found')


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    plot_dir = ensure_plot_dir(root)
    summary_rows = load_chapter_summary_rows(root)
    family = _benchmark_family(summary_rows)
    fig, axes = plt.subplots(len(PROBES), 1, figsize=(9, 8), sharex=True)
    for ax, probe in zip(axes, PROBES):
        for suffix in CASE_SUFFIXES:
            case_name = f'{family}_{suffix}'
            rows = chapter_case_rows(root, case_name, 'stage_timeseries_1d.csv')
            x, y = series_from_rows(rows, 'time', 'stage', filter_key='probe_id', filter_value=probe)
            ax.plot(x, y, label=case_label(suffix))
        ax.set_ylabel(f'{probe_label(probe)}\n水位 (m)')
    axes[0].legend(ncol=5, fontsize=7)
    axes[0].set_title('一维关键断面水位过程线对比')
    axes[-1].set_xlabel('时间 (s)')
    save_figure(fig, plot_dir / 'stage_hydrographs_1d.png')


if __name__ == '__main__':
    main()
