from __future__ import annotations

from typing import Any

import numpy as np


def _series_arrays(rows: list[dict[str, Any]], control_id: str, value_key: str) -> tuple[np.ndarray, np.ndarray]:
    filtered = [row for row in rows if row.get('control_id') == control_id]
    if not filtered:
        return np.asarray([], dtype=float), np.asarray([], dtype=float)
    times = np.asarray([float(row['time']) for row in filtered], dtype=float)
    values = np.asarray([float(row[value_key]) for row in filtered], dtype=float)
    order = np.argsort(times)
    return times[order], values[order]


def _rmse(reference_t: np.ndarray, reference_y: np.ndarray, candidate_t: np.ndarray, candidate_y: np.ndarray) -> float:
    if reference_t.size == 0 or candidate_t.size == 0:
        return 0.0
    interpolated = np.interp(reference_t, candidate_t, candidate_y)
    return float(np.sqrt(np.mean((interpolated - reference_y) ** 2)))


def _max_abs_diff(reference_t: np.ndarray, reference_y: np.ndarray, candidate_t: np.ndarray, candidate_y: np.ndarray) -> float:
    if reference_t.size == 0 or candidate_t.size == 0:
        return 0.0
    interpolated = np.interp(reference_t, candidate_t, candidate_y)
    return float(np.max(np.abs(interpolated - reference_y)))


def _arrival_time(times: np.ndarray, values: np.ndarray) -> float:
    if times.size == 0 or values.size == 0:
        return 0.0
    initial = float(values[0])
    peak = float(np.max(values))
    threshold = initial + 0.5 * (peak - initial)
    indices = np.where(values >= threshold)[0]
    if indices.size == 0:
        return float(times[-1])
    return float(times[indices[0]])


def compute_summary_metrics(
    *,
    case_name: str,
    wall_clock_seconds: float,
    simulated_duration: float,
    exchange_history: list[dict[str, Any]],
    mass_balance_rows: list[dict[str, Any]],
    stage_1d_rows: list[dict[str, Any]],
    stage_2d_rows: list[dict[str, Any]],
    discharge_rows: list[dict[str, Any]],
    reference: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    peak_stage_1d = max((float(row['stage']) for row in stage_1d_rows), default=0.0)
    peak_stage_2d = max((float(row['stage']) for row in stage_2d_rows), default=0.0)
    peak_q_exchange = max((abs(float(row['Q_exchange'])) for row in exchange_history), default=0.0)
    final_mass_error = float(mass_balance_rows[-1]['system_mass_error']) if mass_balance_rows else 0.0
    max_abs_mass_error = max((abs(float(row['system_mass_error'])) for row in mass_balance_rows), default=0.0)
    cumulative_exchange_volume = sum(abs(float(row['dV_exchange'])) for row in exchange_history)

    metrics = {
        'case_name': case_name,
        'wall_clock_seconds': float(wall_clock_seconds),
        'simulated_duration': float(simulated_duration),
        'exchange_count': int(len(exchange_history)),
        'cumulative_exchange_volume': float(cumulative_exchange_volume),
        'final_total_mass_error': final_mass_error,
        'max_abs_mass_error': float(max_abs_mass_error),
        'peak_stage_1d': float(peak_stage_1d),
        'peak_stage_2d': float(peak_stage_2d),
        'peak_Q_exchange': float(peak_q_exchange),
        'RMSE_stage_vs_reference': 0.0,
        'max_abs_stage_diff_vs_reference': 0.0,
        'arrival_time_diff_vs_reference': 0.0,
    }

    if reference is None:
        return metrics

    ref_1d_t, ref_1d_y = _series_arrays(reference['stage_1d_rows'], 'mainstem_mid', 'stage')
    ref_2d_t, ref_2d_y = _series_arrays(reference['stage_2d_rows'], 'floodplain_probe', 'stage')
    cur_1d_t, cur_1d_y = _series_arrays(stage_1d_rows, 'mainstem_mid', 'stage')
    cur_2d_t, cur_2d_y = _series_arrays(stage_2d_rows, 'floodplain_probe', 'stage')

    rmse_1d = _rmse(ref_1d_t, ref_1d_y, cur_1d_t, cur_1d_y)
    rmse_2d = _rmse(ref_2d_t, ref_2d_y, cur_2d_t, cur_2d_y)
    max_diff_1d = _max_abs_diff(ref_1d_t, ref_1d_y, cur_1d_t, cur_1d_y)
    max_diff_2d = _max_abs_diff(ref_2d_t, ref_2d_y, cur_2d_t, cur_2d_y)
    arr_ref = _arrival_time(ref_1d_t, ref_1d_y)
    arr_cur = _arrival_time(cur_1d_t, cur_1d_y)

    metrics['RMSE_stage_vs_reference'] = float(0.5 * (rmse_1d + rmse_2d))
    metrics['max_abs_stage_diff_vs_reference'] = float(max(max_diff_1d, max_diff_2d))
    metrics['arrival_time_diff_vs_reference'] = float(arr_cur - arr_ref)
    return metrics
