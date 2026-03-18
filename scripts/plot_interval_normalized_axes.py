from __future__ import annotations

from pathlib import Path

from scripts._plot_common import (
    axis_limits_with_padding,
    chapter_fixed_interval_rows,
    ensure_plot_dir,
    load_chapter_summary_rows,
    plt,
    save_figure,
)


def _benchmark_family(rows):
    for row in rows:
        if 'test7' in row['scenario_family']:
            return row['scenario_family']
    raise KeyError('No benchmark family found')


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    rows = load_chapter_summary_rows(root)
    interval_rows = chapter_fixed_interval_rows(rows, _benchmark_family(rows))
    x_arr = [float(row['interval_over_t_arr_ref']) for row in interval_rows]
    y_arr = [float(row['arrival_time_error']) for row in interval_rows]
    x_peak = [float(row['interval_over_t_rise_ref']) for row in interval_rows]
    y_peak = [float(row['peak_stage_error']) for row in interval_rows]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    axes[0].plot(
        x_arr,
        y_arr,
        marker='o',
        linewidth=2.0,
        markersize=6.0,
        markerfacecolor='white',
        markeredgewidth=1.6,
        color='#e15759',
    )
    axes[0].axhline(0.0, color='0.55', linewidth=1.0, linestyle='--', zorder=0)
    axes[0].set_ylim(*axis_limits_with_padding(y_arr + y_peak, symmetric=False, min_pad=0.15))
    axes[0].set_xlabel('Δt_ex / t_arr_ref')
    axes[0].set_ylabel('arrival error')
    axes[0].grid(True, alpha=0.25)
    if max(y_arr) - min(y_arr) <= 1.0e-12:
        axes[0].annotate(
            f'constant {y_arr[0]:.3f} s',
            xy=(x_arr[-1], y_arr[-1]),
            xytext=(-6, 10),
            textcoords='offset points',
            ha='right',
            fontsize=8.5,
            color='#444444',
        )

    axes[1].plot(
        x_peak,
        y_peak,
        marker='o',
        linewidth=2.0,
        markersize=6.0,
        markerfacecolor='white',
        markeredgewidth=1.6,
        color='#b56576',
    )
    axes[1].axhline(0.0, color='0.55', linewidth=1.0, linestyle='--', zorder=0)
    axes[1].set_xlabel('Δt_ex / t_rise_ref')
    axes[1].set_ylabel('peak stage error')
    axes[1].grid(True, alpha=0.25)
    if max(y_peak) - min(y_peak) <= 1.0e-12:
        axes[1].annotate(
            f'constant {y_peak[0]:.3f} m',
            xy=(x_peak[-1], y_peak[-1]),
            xytext=(-6, 10),
            textcoords='offset points',
            ha='right',
            fontsize=8.5,
            color='#444444',
        )
    save_figure(fig, ensure_plot_dir(root) / 'interval_normalized_axes.png')


if __name__ == '__main__':
    main()
