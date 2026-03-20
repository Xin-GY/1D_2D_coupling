from __future__ import annotations

import math
from pathlib import Path

from scripts._plot_common import (
    axis_limits_with_padding,
    chapter_case_json,
    chapter_case_rows,
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


def _crossing_time(times: list[float], values: list[float], threshold: float) -> float:
    if not times or not values:
        return float('nan')
    if len(times) != len(values):
        raise ValueError('times and values must have the same length')
    previous_t = float(times[0])
    previous_v = float(values[0])
    if previous_v >= threshold:
        return previous_t
    for current_t, current_v in zip(times[1:], values[1:]):
        current_t = float(current_t)
        current_v = float(current_v)
        if current_v >= threshold:
            dv = current_v - previous_v
            if abs(dv) <= 1.0e-12:
                return current_t
            weight = (threshold - previous_v) / dv
            return previous_t + weight * (current_t - previous_t)
        previous_t = current_t
        previous_v = current_v
    return float('nan')


def _normalized_axis_fallback(root: Path, family: str) -> tuple[list[float], list[float], str]:
    reference_case = f'{family}_strict_global_min_dt'
    config = chapter_case_json(root, reference_case, 'config.json')
    primary_q = str(config.get('probe_defs', {}).get('primary_discharge_probe', 'mainstem_right_q'))
    discharge_rows = chapter_case_rows(root, reference_case, 'discharge_timeseries.csv')
    probe_rows = [row for row in discharge_rows if row.get('series_id') == primary_q]
    if not probe_rows:
        return [], [], 'missing_reference_discharge'
    times = [float(row['time']) for row in probe_rows]
    values = [float(row['discharge']) for row in probe_rows]
    base = float(values[0])
    peak = float(max(values))
    amplitude = peak - base
    if amplitude <= 1.0e-12:
        return [], [], 'degenerate_reference_discharge'
    arr_threshold = base + 0.10 * amplitude
    rise_threshold_lo = base + 0.10 * amplitude
    rise_threshold_hi = base + 0.90 * amplitude
    arr_ref = _crossing_time(times, values, arr_threshold)
    t10 = _crossing_time(times, values, rise_threshold_lo)
    t90 = _crossing_time(times, values, rise_threshold_hi)
    rise_ref = t90 - t10 if math.isfinite(t10) and math.isfinite(t90) else float('nan')

    summary_rows = load_chapter_summary_rows(root)
    interval_rows = chapter_fixed_interval_rows(summary_rows, family)
    arr_values = []
    rise_values = []
    for row in interval_rows:
        interval = float(row['exchange_interval'])
        arr_values.append(interval / arr_ref if math.isfinite(arr_ref) and arr_ref > 1.0e-12 else float('nan'))
        rise_values.append(interval / rise_ref if math.isfinite(rise_ref) and rise_ref > 1.0e-12 else float('nan'))
    return arr_values, rise_values, '参考流量过程回算'


def main(root: Path | str | None = None) -> None:
    root = Path('artifacts/chapter_coupling_analysis') if root is None else Path(root)
    rows = load_chapter_summary_rows(root)
    family = _benchmark_family(rows)
    interval_rows = chapter_fixed_interval_rows(rows, family)
    x_arr = [float(row['interval_over_t_arr_ref']) for row in interval_rows]
    y_arr = [float(row['arrival_time_error']) for row in interval_rows]
    x_peak = [float(row['interval_over_t_rise_ref']) for row in interval_rows]
    y_peak = [float(row['peak_stage_error']) for row in interval_rows]
    normalized_source = 'summary'
    if not any(math.isfinite(value) for value in x_arr) or not any(math.isfinite(value) for value in x_peak):
        fallback_arr, fallback_peak, normalized_source = _normalized_axis_fallback(root, family)
        if fallback_arr:
            x_arr = fallback_arr
        if fallback_peak:
            x_peak = fallback_peak
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
    axes[0].set_ylabel('到达时间误差 (s)')
    axes[0].grid(True, alpha=0.25)
    if max(y_arr) - min(y_arr) <= 1.0e-12:
        axes[0].annotate(
            f'当前序列恒为 {y_arr[0]:.3f} s',
            xy=(x_arr[-1], y_arr[-1]),
            xytext=(-6, 10),
            textcoords='offset points',
            ha='right',
            fontsize=8.5,
            color='#444444',
        )
    if normalized_source != 'summary':
        axes[0].text(
            0.03,
            0.96,
            f'x 轴来源：{normalized_source}',
            transform=axes[0].transAxes,
            ha='left',
            va='top',
            fontsize=8,
            color='#555555',
            bbox={'facecolor': 'white', 'edgecolor': '0.8', 'alpha': 0.9, 'pad': 2.5},
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
    axes[1].set_ylabel('峰值水位误差 (m)')
    axes[1].grid(True, alpha=0.25)
    if max(y_peak) - min(y_peak) <= 1.0e-12:
        axes[1].annotate(
            f'当前序列恒为 {y_peak[0]:.3f} m',
            xy=(x_peak[-1], y_peak[-1]),
            xytext=(-6, 10),
            textcoords='offset points',
            ha='right',
            fontsize=8.5,
            color='#444444',
        )
    if normalized_source != 'summary':
        axes[1].text(
            0.03,
            0.96,
            f'x 轴来源：{normalized_source}',
            transform=axes[1].transAxes,
            ha='left',
            va='top',
            fontsize=8,
            color='#555555',
            bbox={'facecolor': 'white', 'edgecolor': '0.8', 'alpha': 0.9, 'pad': 2.5},
        )
    save_figure(fig, ensure_plot_dir(root) / 'interval_normalized_axes.png')


if __name__ == '__main__':
    main()
