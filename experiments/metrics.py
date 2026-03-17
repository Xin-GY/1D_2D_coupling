from __future__ import annotations

from typing import Any

import numpy as np


ANALYSIS_DT = 0.5
TARGET_STAGE_DIFF_CASES = {
    'fixed_interval_015s',
    'fixed_interval_030s',
    'fixed_interval_060s',
    'fixed_interval_300s',
}


def _filtered_series_arrays(
    rows: list[dict[str, Any]],
    *,
    id_key: str,
    id_value: str,
    value_key: str,
) -> tuple[np.ndarray, np.ndarray]:
    time_map: dict[float, float] = {}
    for row in rows:
        if row.get(id_key) != id_value:
            continue
        time_map[float(row['time'])] = float(row[value_key])
    if not time_map:
        return np.asarray([], dtype=float), np.asarray([], dtype=float)
    times = np.asarray(sorted(time_map.keys()), dtype=float)
    values = np.asarray([time_map[float(time_value)] for time_value in times], dtype=float)
    return times, values


def _analysis_grid(simulated_duration: float, dt: float = ANALYSIS_DT) -> np.ndarray:
    steps = int(round(float(simulated_duration) / float(dt)))
    grid = np.asarray([float(idx) * float(dt) for idx in range(steps + 1)], dtype=float)
    if grid.size == 0 or grid[-1] < float(simulated_duration):
        grid = np.append(grid, float(simulated_duration))
    else:
        grid[-1] = float(simulated_duration)
    return grid


def _interp_linear(times: np.ndarray, values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    if times.size == 0 or values.size == 0:
        return np.zeros_like(grid)
    return np.interp(grid, times, values)


def _interp_stepwise(times: np.ndarray, values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    if times.size == 0 or values.size == 0:
        return np.zeros_like(grid)
    result = np.empty_like(grid, dtype=float)
    for idx, target in enumerate(grid):
        pos = int(np.searchsorted(times, target, side='right') - 1)
        pos = min(max(pos, 0), len(values) - 1)
        result[idx] = float(values[pos])
    return result


def _rmse(reference_y: np.ndarray, candidate_y: np.ndarray) -> float:
    if reference_y.size == 0 or candidate_y.size == 0:
        return 0.0
    return float(np.sqrt(np.mean((candidate_y - reference_y) ** 2)))


def _max_abs_diff(reference_y: np.ndarray, candidate_y: np.ndarray) -> float:
    if reference_y.size == 0 or candidate_y.size == 0:
        return 0.0
    return float(np.max(np.abs(candidate_y - reference_y)))


def _threshold_from_series(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    initial = float(values[0])
    peak = float(np.max(values))
    return float(initial + 0.5 * (peak - initial))


def _crossing_diagnostic(times: np.ndarray, values: np.ndarray, threshold: float) -> dict[str, Any]:
    if times.size == 0 or values.size == 0:
        return {
            'found_crossing': False,
            'bracket_t0': np.nan,
            'bracket_t1': np.nan,
            'bracket_y0': np.nan,
            'bracket_y1': np.nan,
            'crossing_time_interp': np.nan,
            'peak_value': np.nan,
            'peak_time': np.nan,
        }

    peak_idx = int(np.argmax(values))
    peak_value = float(values[peak_idx])
    peak_time = float(times[peak_idx])
    initial = float(values[0])
    rising = peak_value >= initial

    for idx in range(values.size):
        if abs(float(values[idx]) - float(threshold)) <= 1.0e-12:
            return {
                'found_crossing': True,
                'bracket_t0': float(times[idx]),
                'bracket_t1': float(times[idx]),
                'bracket_y0': float(values[idx]),
                'bracket_y1': float(values[idx]),
                'crossing_time_interp': float(times[idx]),
                'peak_value': peak_value,
                'peak_time': peak_time,
            }

    for idx in range(values.size - 1):
        y0 = float(values[idx])
        y1 = float(values[idx + 1])
        crossed = (y0 < threshold <= y1) if rising else (y0 > threshold >= y1)
        if not crossed:
            continue
        t0 = float(times[idx])
        t1 = float(times[idx + 1])
        if abs(y1 - y0) <= 1.0e-12:
            crossing_time = t0
        else:
            crossing_time = float(t0 + (threshold - y0) * (t1 - t0) / (y1 - y0))
        return {
            'found_crossing': True,
            'bracket_t0': t0,
            'bracket_t1': t1,
            'bracket_y0': y0,
            'bracket_y1': y1,
            'crossing_time_interp': crossing_time,
            'peak_value': peak_value,
            'peak_time': peak_time,
        }

    return {
        'found_crossing': False,
        'bracket_t0': np.nan,
        'bracket_t1': np.nan,
        'bracket_y0': np.nan,
        'bracket_y1': np.nan,
        'crossing_time_interp': float(times[-1]),
        'peak_value': peak_value,
        'peak_time': peak_time,
    }


def _phase_lag_seconds(reference_y: np.ndarray, candidate_y: np.ndarray, dt: float = ANALYSIS_DT) -> float:
    if reference_y.size == 0 or candidate_y.size == 0:
        return 0.0
    ref = np.asarray(reference_y, dtype=float)
    cur = np.asarray(candidate_y, dtype=float)
    if np.std(ref) <= 1.0e-12 or np.std(cur) <= 1.0e-12:
        return 0.0
    if np.allclose(ref, cur, atol=1.0e-10, rtol=1.0e-8):
        return 0.0
    ref = (ref - np.mean(ref)) / np.std(ref)
    cur = (cur - np.mean(cur)) / np.std(cur)
    max_lag = ref.size - 1
    min_overlap = max(8, int(np.ceil(min(ref.size, cur.size) * 0.5)))
    best_lag = 0
    best_score = -np.inf
    best_overlap = -1
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            ref_slice = ref[-lag:]
            cur_slice = cur[: cur.size + lag]
        elif lag > 0:
            ref_slice = ref[: ref.size - lag]
            cur_slice = cur[lag:]
        else:
            ref_slice = ref
            cur_slice = cur
        if ref_slice.size == 0 or cur_slice.size == 0:
            continue
        overlap = int(ref_slice.size)
        if overlap < min_overlap:
            continue
        denominator = float(np.linalg.norm(ref_slice) * np.linalg.norm(cur_slice))
        if denominator <= 1.0e-12:
            continue
        score = float(np.dot(ref_slice, cur_slice) / denominator)
        if (
            score > best_score + 1.0e-12
            or (
                abs(score - best_score) <= 1.0e-12
                and (overlap > best_overlap or (overlap == best_overlap and abs(lag) < abs(best_lag)))
            )
        ):
            best_score = score
            best_lag = lag
            best_overlap = overlap
    return float(best_lag * dt)


def _nash_sutcliffe_efficiency(reference_y: np.ndarray, candidate_y: np.ndarray) -> float:
    if reference_y.size == 0 or candidate_y.size == 0:
        return 0.0
    denominator = float(np.sum((reference_y - np.mean(reference_y)) ** 2))
    if denominator <= 1.0e-12:
        return 1.0 if np.allclose(reference_y, candidate_y) else 0.0
    numerator = float(np.sum((candidate_y - reference_y) ** 2))
    return float(1.0 - numerator / denominator)


def _cumulative_mass_error(mass_balance_rows: list[dict[str, Any]]) -> tuple[float, float]:
    if not mass_balance_rows:
        return 0.0, 0.0
    times = np.asarray([float(row['time']) for row in mass_balance_rows], dtype=float)
    errors = np.asarray([abs(float(row['system_mass_error'])) for row in mass_balance_rows], dtype=float)
    if times.size and times[0] > 0.0:
        times = np.insert(times, 0, 0.0)
        errors = np.insert(errors, 0, 0.0)
    cumulative = float(np.trapezoid(errors, times)) if times.size > 1 else float(errors[0])
    initial_volume = float(mass_balance_rows[0].get('system_volume', 0.0))
    simulated_duration = float(times[-1]) if times.size else 0.0
    if initial_volume <= 1.0e-12 or simulated_duration <= 1.0e-12:
        return cumulative, 0.0
    return cumulative, float(cumulative / (initial_volume * simulated_duration))


def _build_crossing_row(series_id: str, threshold: float, crossing: dict[str, Any]) -> dict[str, Any]:
    return {
        'series_id': series_id,
        'threshold': float(threshold),
        'found_crossing': bool(crossing['found_crossing']),
        'bracket_t0': float(crossing['bracket_t0']) if not np.isnan(crossing['bracket_t0']) else np.nan,
        'bracket_t1': float(crossing['bracket_t1']) if not np.isnan(crossing['bracket_t1']) else np.nan,
        'bracket_y0': float(crossing['bracket_y0']) if not np.isnan(crossing['bracket_y0']) else np.nan,
        'bracket_y1': float(crossing['bracket_y1']) if not np.isnan(crossing['bracket_y1']) else np.nan,
        'crossing_time_interp': float(crossing['crossing_time_interp']) if not np.isnan(crossing['crossing_time_interp']) else np.nan,
        'peak_value': float(crossing['peak_value']) if not np.isnan(crossing['peak_value']) else np.nan,
        'peak_time': float(crossing['peak_time']) if not np.isnan(crossing['peak_time']) else np.nan,
    }


def compute_case_analysis(
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
    triangle_count: int = 0,
) -> dict[str, Any]:
    peak_stage_1d = max((float(row['stage']) for row in stage_1d_rows), default=0.0)
    peak_stage_2d = max((float(row['stage']) for row in stage_2d_rows), default=0.0)
    peak_q_exchange = max((abs(float(row['Q_exchange'])) for row in exchange_history), default=0.0)
    final_mass_error = float(mass_balance_rows[-1]['system_mass_error']) if mass_balance_rows else 0.0
    max_abs_mass_error = max((abs(float(row['system_mass_error'])) for row in mass_balance_rows), default=0.0)
    cumulative_exchange_volume = sum(abs(float(row['dV_exchange'])) for row in exchange_history)
    cumulative_mass_error, normalized_mass_error = _cumulative_mass_error(mass_balance_rows)

    cur_1d_t, cur_1d_y = _filtered_series_arrays(stage_1d_rows, id_key='control_id', id_value='mainstem_mid', value_key='stage')
    cur_2d_t, cur_2d_y = _filtered_series_arrays(stage_2d_rows, id_key='control_id', id_value='floodplain_probe', value_key='stage')
    discharge_t, discharge_y = _filtered_series_arrays(discharge_rows, id_key='series_id', id_value='exchange_q_total', value_key='discharge')
    analysis_grid = _analysis_grid(simulated_duration)
    cur_1d_grid = _interp_linear(cur_1d_t, cur_1d_y, analysis_grid)
    cur_2d_grid = _interp_linear(cur_2d_t, cur_2d_y, analysis_grid)

    self_threshold = _threshold_from_series(cur_1d_y)
    cur_crossing = _crossing_diagnostic(cur_1d_t, cur_1d_y, self_threshold)
    cur_2d_threshold = _threshold_from_series(cur_2d_y)
    cur_2d_crossing = _crossing_diagnostic(cur_2d_t, cur_2d_y, cur_2d_threshold)

    summary = {
        'case_name': case_name,
        'wall_clock_seconds': float(wall_clock_seconds),
        'simulated_duration': float(simulated_duration),
        'exchange_count': int(len(exchange_history)),
        'cumulative_exchange_volume': float(cumulative_exchange_volume),
        'final_total_mass_error': final_mass_error,
        'max_abs_mass_error': float(max_abs_mass_error),
        'cumulative_mass_error': float(cumulative_mass_error),
        'normalized_mass_error': float(normalized_mass_error),
        'peak_stage_1d': float(peak_stage_1d),
        'peak_stage_2d': float(peak_stage_2d),
        'peak_Q_exchange': float(peak_q_exchange),
        'triangle_count': int(triangle_count),
        'RMSE_stage_vs_reference': 0.0,
        'max_abs_stage_diff_vs_reference': 0.0,
        'arrival_time_diff_vs_reference': 0.0,
        'phase_lag_seconds': 0.0,
        'peak_stage_error': 0.0,
        'peak_time_error': 0.0,
        'hydrograph_NSE': 1.0,
    }

    crossing_rows = [
        _build_crossing_row('mainstem_mid_stage', self_threshold, cur_crossing),
        _build_crossing_row('floodplain_probe_stage', cur_2d_threshold, cur_2d_crossing),
    ]
    stage_diff_rows: list[dict[str, Any]] = []

    if reference is None:
        return {
            'summary': summary,
            'crossing_diagnostics': crossing_rows,
            'stage_diff_rows': stage_diff_rows,
        }

    ref_1d_t, ref_1d_y = _filtered_series_arrays(reference['stage_1d_rows'], id_key='control_id', id_value='mainstem_mid', value_key='stage')
    ref_2d_t, ref_2d_y = _filtered_series_arrays(reference['stage_2d_rows'], id_key='control_id', id_value='floodplain_probe', value_key='stage')
    ref_discharge_t, ref_discharge_y = _filtered_series_arrays(reference['discharge_rows'], id_key='series_id', id_value='exchange_q_total', value_key='discharge')
    ref_1d_grid = _interp_linear(ref_1d_t, ref_1d_y, analysis_grid)
    ref_2d_grid = _interp_linear(ref_2d_t, ref_2d_y, analysis_grid)

    threshold = _threshold_from_series(ref_1d_y)
    ref_crossing = _crossing_diagnostic(ref_1d_t, ref_1d_y, threshold)
    cur_crossing = _crossing_diagnostic(cur_1d_t, cur_1d_y, threshold)
    crossing_rows[0] = _build_crossing_row('mainstem_mid_stage', threshold, cur_crossing)
    crossing_rows.append(_build_crossing_row('mainstem_mid_stage_reference', threshold, ref_crossing))

    rmse_1d = _rmse(ref_1d_grid, cur_1d_grid)
    rmse_2d = _rmse(ref_2d_grid, cur_2d_grid)
    max_diff_1d = _max_abs_diff(ref_1d_grid, cur_1d_grid)
    max_diff_2d = _max_abs_diff(ref_2d_grid, cur_2d_grid)
    phase_lag_seconds = _phase_lag_seconds(ref_1d_grid, cur_1d_grid)

    ref_peak_idx = int(np.argmax(ref_1d_grid)) if ref_1d_grid.size else 0
    cur_peak_idx = int(np.argmax(cur_1d_grid)) if cur_1d_grid.size else 0
    ref_peak_time = float(analysis_grid[ref_peak_idx]) if analysis_grid.size else 0.0
    cur_peak_time = float(analysis_grid[cur_peak_idx]) if analysis_grid.size else 0.0

    ref_q_grid = _interp_stepwise(ref_discharge_t, ref_discharge_y, analysis_grid)
    cur_q_grid = _interp_stepwise(discharge_t, discharge_y, analysis_grid)

    summary['RMSE_stage_vs_reference'] = float(0.5 * (rmse_1d + rmse_2d))
    summary['max_abs_stage_diff_vs_reference'] = float(max(max_diff_1d, max_diff_2d))
    summary['arrival_time_diff_vs_reference'] = float(cur_crossing['crossing_time_interp'] - ref_crossing['crossing_time_interp'])
    summary['phase_lag_seconds'] = float(phase_lag_seconds)
    summary['peak_stage_error'] = float(np.max(cur_1d_grid) - np.max(ref_1d_grid)) if cur_1d_grid.size and ref_1d_grid.size else 0.0
    summary['peak_time_error'] = float(cur_peak_time - ref_peak_time)
    summary['hydrograph_NSE'] = float(_nash_sutcliffe_efficiency(ref_q_grid, cur_q_grid))

    stage_diff_rows = [
        {
            't': float(time_value),
            'stage_ref': float(ref_stage),
            'stage_case': float(case_stage),
            'diff': float(case_stage - ref_stage),
            'threshold': float(threshold),
            'ref_crossing_time': float(ref_crossing['crossing_time_interp']),
            'case_crossing_time': float(cur_crossing['crossing_time_interp']),
            'arrival_time_diff': float(cur_crossing['crossing_time_interp'] - ref_crossing['crossing_time_interp']),
        }
        for time_value, ref_stage, case_stage in zip(analysis_grid.tolist(), ref_1d_grid.tolist(), cur_1d_grid.tolist())
    ]

    return {
        'summary': summary,
        'crossing_diagnostics': crossing_rows,
        'stage_diff_rows': stage_diff_rows,
    }


def should_write_stage_diff(case_name: str) -> bool:
    return any(token in case_name for token in TARGET_STAGE_DIFF_CASES)


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
    triangle_count: int = 0,
) -> dict[str, Any]:
    return compute_case_analysis(
        case_name=case_name,
        wall_clock_seconds=wall_clock_seconds,
        simulated_duration=simulated_duration,
        exchange_history=exchange_history,
        mass_balance_rows=mass_balance_rows,
        stage_1d_rows=stage_1d_rows,
        stage_2d_rows=stage_2d_rows,
        discharge_rows=discharge_rows,
        reference=reference,
        triangle_count=triangle_count,
    )['summary']
