from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from experiments.io import read_csv, read_json
from experiments.metrics import (
    ANALYSIS_DT,
    _analysis_grid,
    _crossing_diagnostic,
    _cumulative_mass_error,
    _filtered_series_arrays,
    _interp_linear,
    _max_abs_diff,
    _nash_sutcliffe_efficiency,
    _phase_lag_seconds,
    _rmse,
    _threshold_from_series,
)


def _load_case_dir(case_dir: Path) -> dict[str, Any]:
    return {
        'config': read_json(case_dir / 'config.json'),
        'provenance': read_json(case_dir / 'provenance.json'),
        'mass_balance_rows': read_csv(case_dir / 'mass_balance.csv'),
        'stage_1d_rows': read_csv(case_dir / 'stage_timeseries_1d.csv'),
        'stage_2d_rows': read_csv(case_dir / 'stage_timeseries_2d.csv'),
        'discharge_rows': read_csv(case_dir / 'discharge_timeseries.csv'),
        'exchange_history': read_csv(case_dir / 'exchange_history.csv'),
        'exchange_link_rows': read_csv(case_dir / 'exchange_link_timeseries.csv'),
        'field_rows': read_csv(case_dir / 'two_d_field_summary.csv'),
        'timing': read_json(case_dir / 'timing_breakdown.json'),
        'geometry': read_json(case_dir / 'geometry.json'),
    }


def _crossing_time(times: np.ndarray, values: np.ndarray, threshold: float) -> float:
    return float(_crossing_diagnostic(times, values, threshold)['crossing_time_interp'])


def _rise_duration(times: np.ndarray, values: np.ndarray) -> float:
    if times.size == 0 or values.size == 0:
        return 0.0
    initial = float(values[0])
    peak = float(np.max(values))
    amp = peak - initial
    if amp <= 1.0e-12:
        return 0.0
    t10 = _crossing_time(times, values, initial + 0.1 * amp)
    t90 = _crossing_time(times, values, initial + 0.9 * amp)
    return float(max(t90 - t10, 0.0))


def _series_grid(rows: list[dict[str, Any]], *, series_id: str, id_key: str, value_key: str, duration: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    times, values = _filtered_series_arrays(rows, id_key=id_key, id_value=series_id, value_key=value_key)
    grid = _analysis_grid(duration, dt=ANALYSIS_DT)
    return times, values, _interp_linear(times, values, grid)


def _field_by_cell(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(row['cell_id']): row for row in rows}


def _weighted_iou(reference_mask: np.ndarray, candidate_mask: np.ndarray, area: np.ndarray) -> tuple[float, float]:
    intersection = float(np.sum(area[reference_mask & candidate_mask]))
    union = float(np.sum(area[reference_mask | candidate_mask]))
    if union <= 1.0e-12:
        return 1.0, 1.0
    return float(intersection / union), float(intersection / union)


def _sign_flip_count(values: list[float]) -> int:
    nonzero = [np.sign(float(value)) for value in values if abs(float(value)) > 1.0e-12]
    if len(nonzero) < 2:
        return 0
    return int(sum(1 for prev, cur in zip(nonzero[:-1], nonzero[1:]) if prev != cur))


def _peak_time(grid: np.ndarray, values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    return float(grid[int(np.argmax(values))])


def _peak_value(values: np.ndarray) -> float:
    return float(np.max(values)) if values.size else 0.0


def _field_metrics(
    current_rows: list[dict[str, Any]],
    reference_rows: list[dict[str, Any]],
    *,
    wet_threshold: float,
    partition: str | None = None,
) -> dict[str, float]:
    current_map = _field_by_cell(current_rows)
    reference_map = _field_by_cell(reference_rows)
    shared_ids = sorted(set(current_map).intersection(reference_map))
    if partition is not None:
        shared_ids = [cell_id for cell_id in shared_ids if str(current_map[cell_id]['partition']) == partition]
    if not shared_ids:
        return {
            'max_depth_map_difference': 0.0,
            'arrival_time_map_difference': 0.0,
            'inundated_area_difference': 0.0,
            'wet_area_iou': 1.0,
            'wet_area_csi': 1.0,
        }
    cur_depth = np.asarray([float(current_map[cell_id]['max_depth']) for cell_id in shared_ids], dtype=float)
    ref_depth = np.asarray([float(reference_map[cell_id]['max_depth']) for cell_id in shared_ids], dtype=float)
    cur_arrival = np.asarray([float(current_map[cell_id]['arrival_time']) if current_map[cell_id]['arrival_time'] != '' else np.nan for cell_id in shared_ids], dtype=float)
    ref_arrival = np.asarray([float(reference_map[cell_id]['arrival_time']) if reference_map[cell_id]['arrival_time'] != '' else np.nan for cell_id in shared_ids], dtype=float)
    area = np.asarray([float(current_map[cell_id]['area']) for cell_id in shared_ids], dtype=float)
    wet_cur = cur_depth >= float(wet_threshold)
    wet_ref = ref_depth >= float(wet_threshold)
    wet_area_iou, wet_area_csi = _weighted_iou(wet_ref, wet_cur, area)
    arrival_mask = np.isfinite(cur_arrival) & np.isfinite(ref_arrival)
    return {
        'max_depth_map_difference': float(np.max(np.abs(cur_depth - ref_depth))) if cur_depth.size else 0.0,
        'arrival_time_map_difference': float(np.max(np.abs(cur_arrival[arrival_mask] - ref_arrival[arrival_mask]))) if np.any(arrival_mask) else 0.0,
        'inundated_area_difference': float(abs(np.sum(area[wet_cur]) - np.sum(area[wet_ref]))),
        'wet_area_iou': float(wet_area_iou),
        'wet_area_csi': float(wet_area_csi),
    }


def rebuild_chapter_case_outputs(case_dir: Path, reference_dir: Path | None = None) -> dict[str, Any]:
    payload = _load_case_dir(case_dir)
    config = payload['config']
    duration = float(config['duration'])
    primary_stage_probe = str(config.get('probe_defs', {}).get('primary_stage_probe', 'mainstem_mid'))
    primary_discharge_probe = str(config.get('probe_defs', {}).get('primary_discharge_probe', 'mainstem_right_q'))
    mass_balance_rows = payload['mass_balance_rows']
    exchange_link_rows = payload['exchange_link_rows']

    stage_t, stage_v, stage_grid = _series_grid(payload['stage_1d_rows'], series_id=primary_stage_probe, id_key='probe_id', value_key='stage', duration=duration)
    discharge_t, discharge_v, discharge_grid = _series_grid(payload['discharge_rows'], series_id=primary_discharge_probe, id_key='series_id', value_key='discharge', duration=duration)
    grid = _analysis_grid(duration, dt=ANALYSIS_DT)

    cumulative_mass_error, normalized_mass_error = _cumulative_mass_error(mass_balance_rows)
    summary = {
        'case_name': str(config['case_name']),
        'scenario_family': str(config['scenario_family']),
        'case_variant': str(config['case_variant']),
        'scheduler_mode': str(config['scheduler_mode']),
        'exchange_interval': float(config['exchange_interval']) if config['exchange_interval'] is not None else np.nan,
        'reference_policy': str(config['reference_policy']),
        'source_mode': str(payload['provenance'].get('source_mode', 'synthetic')),
        'wall_clock_seconds': float(payload['timing'].get('wall_clock_seconds', 0.0)),
        'simulated_duration': duration,
        'exchange_event_count': int(len({float(row['time']) for row in exchange_link_rows if float(row['time']) > 0.0})),
        'first_exchange_time': float(min((float(row['time']) for row in exchange_link_rows if float(row['time']) > 0.0), default=0.0)),
        'cumulative_exchange_volume': float(sum(abs(float(row['dV_exchange'])) for row in exchange_link_rows)),
        'sign_flip_count': int(_sign_flip_count([float(row['Q_exchange']) for row in exchange_link_rows])),
        'link_mass_closure_error': float(max((abs(float(row['mass_error'])) for row in payload['exchange_history']), default=0.0)),
        'final_total_mass_error': float(mass_balance_rows[-1]['system_mass_error']) if mass_balance_rows else 0.0,
        'normalized_mass_error': float(normalized_mass_error),
        'cumulative_mass_error': float(cumulative_mass_error),
        'relative_cost_ratio': 1.0,
        'interval_over_t_arr_ref': np.nan,
        'interval_over_t_rise_ref': np.nan,
        'stage_rmse': 0.0,
        'discharge_rmse': 0.0,
        'peak_stage_error': 0.0,
        'peak_discharge_error': 0.0,
        'peak_time_error': 0.0,
        'arrival_time_error': 0.0,
        'phase_lag': 0.0,
        'hydrograph_NSE': 1.0,
        'max_depth_map_difference': 0.0,
        'arrival_time_map_difference': 0.0,
        'inundated_area_difference': 0.0,
        'wet_area_iou': 1.0,
        'wet_area_csi': 1.0,
        'first_exchange_offset_vs_arrival': 0.0,
    }

    threshold = _threshold_from_series(stage_v)
    current_crossing = _crossing_diagnostic(stage_t, stage_v, threshold)
    crossing_rows = [
        {
            'series_id': f'{primary_stage_probe}_candidate',
            'threshold': float(threshold),
            'found_crossing': bool(current_crossing['found_crossing']),
            'bracket_t0': float(current_crossing['bracket_t0']) if not np.isnan(current_crossing['bracket_t0']) else np.nan,
            'bracket_t1': float(current_crossing['bracket_t1']) if not np.isnan(current_crossing['bracket_t1']) else np.nan,
            'bracket_y0': float(current_crossing['bracket_y0']) if not np.isnan(current_crossing['bracket_y0']) else np.nan,
            'bracket_y1': float(current_crossing['bracket_y1']) if not np.isnan(current_crossing['bracket_y1']) else np.nan,
            'crossing_time_interp': float(current_crossing['crossing_time_interp']) if not np.isnan(current_crossing['crossing_time_interp']) else np.nan,
            'peak_value': float(current_crossing['peak_value']) if not np.isnan(current_crossing['peak_value']) else np.nan,
            'peak_time': float(current_crossing['peak_time']) if not np.isnan(current_crossing['peak_time']) else np.nan,
        }
    ]
    summary['first_exchange_offset_vs_arrival'] = float(summary['first_exchange_time'] - float(current_crossing['crossing_time_interp']))

    stage_diff_rows: list[dict[str, Any]] = []
    partition_rows: list[dict[str, Any]] = []
    exchange_summary_rows: list[dict[str, Any]] = []

    if reference_dir is not None:
        ref_payload = _load_case_dir(reference_dir)
        ref_stage_t, ref_stage_v, ref_stage_grid = _series_grid(ref_payload['stage_1d_rows'], series_id=primary_stage_probe, id_key='probe_id', value_key='stage', duration=duration)
        ref_discharge_t, ref_discharge_v, ref_discharge_grid = _series_grid(ref_payload['discharge_rows'], series_id=primary_discharge_probe, id_key='series_id', value_key='discharge', duration=duration)
        ref_threshold = _threshold_from_series(ref_stage_v)
        ref_crossing = _crossing_diagnostic(ref_stage_t, ref_stage_v, ref_threshold)
        crossing_rows.append(
            {
                'series_id': f'{primary_stage_probe}_reference',
                'threshold': float(ref_threshold),
                'found_crossing': bool(ref_crossing['found_crossing']),
                'bracket_t0': float(ref_crossing['bracket_t0']) if not np.isnan(ref_crossing['bracket_t0']) else np.nan,
                'bracket_t1': float(ref_crossing['bracket_t1']) if not np.isnan(ref_crossing['bracket_t1']) else np.nan,
                'bracket_y0': float(ref_crossing['bracket_y0']) if not np.isnan(ref_crossing['bracket_y0']) else np.nan,
                'bracket_y1': float(ref_crossing['bracket_y1']) if not np.isnan(ref_crossing['bracket_y1']) else np.nan,
                'crossing_time_interp': float(ref_crossing['crossing_time_interp']) if not np.isnan(ref_crossing['crossing_time_interp']) else np.nan,
                'peak_value': float(ref_crossing['peak_value']) if not np.isnan(ref_crossing['peak_value']) else np.nan,
                'peak_time': float(ref_crossing['peak_time']) if not np.isnan(ref_crossing['peak_time']) else np.nan,
            }
        )
        summary['relative_cost_ratio'] = float(summary['wall_clock_seconds'] / max(float(ref_payload['timing'].get('wall_clock_seconds', 1.0)), 1.0e-9))
        summary['stage_rmse'] = float(_rmse(ref_stage_grid, stage_grid))
        summary['discharge_rmse'] = float(_rmse(ref_discharge_grid, discharge_grid))
        summary['peak_stage_error'] = float(_peak_value(stage_grid) - _peak_value(ref_stage_grid))
        summary['peak_discharge_error'] = float(_peak_value(discharge_grid) - _peak_value(ref_discharge_grid))
        summary['peak_time_error'] = float(_peak_time(grid, stage_grid) - _peak_time(grid, ref_stage_grid))
        summary['arrival_time_error'] = float(current_crossing['crossing_time_interp'] - ref_crossing['crossing_time_interp'])
        summary['phase_lag'] = float(_phase_lag_seconds(ref_stage_grid, stage_grid))
        summary['hydrograph_NSE'] = float(_nash_sutcliffe_efficiency(ref_discharge_grid, discharge_grid))
        summary['first_exchange_offset_vs_arrival'] = float(summary['first_exchange_time'] - float(ref_crossing['crossing_time_interp']))
        rise_ref = _rise_duration(ref_stage_t, ref_stage_v)
        arr_ref = float(ref_crossing['crossing_time_interp'])
        if config['exchange_interval'] is not None:
            interval = float(config['exchange_interval'])
            summary['interval_over_t_arr_ref'] = float(interval / arr_ref) if arr_ref > 1.0e-12 else np.nan
            summary['interval_over_t_rise_ref'] = float(interval / rise_ref) if rise_ref > 1.0e-12 else np.nan
        field_metrics = _field_metrics(payload['field_rows'], ref_payload['field_rows'], wet_threshold=0.01)
        summary.update(field_metrics)
        for partition in sorted(set(str(row['partition']) for row in payload['field_rows'])):
            part_metrics = _field_metrics(payload['field_rows'], ref_payload['field_rows'], wet_threshold=0.01, partition=partition)
            partition_rows.append(
                {
                    'case_name': summary['case_name'],
                    'scenario_family': summary['scenario_family'],
                    'partition': partition,
                    **part_metrics,
                }
            )
        for t, ref_stage, cur_stage in zip(grid, ref_stage_grid, stage_grid):
            stage_diff_rows.append(
                {
                    't': float(t),
                    'stage_ref': float(ref_stage),
                    'stage_case': float(cur_stage),
                    'diff': float(cur_stage - ref_stage),
                    'threshold': float(ref_threshold),
                    'ref_crossing_time': float(ref_crossing['crossing_time_interp']),
                    'case_crossing_time': float(current_crossing['crossing_time_interp']),
                    'arrival_time_diff': float(current_crossing['crossing_time_interp'] - ref_crossing['crossing_time_interp']),
                }
            )

    link_groups: dict[str, list[dict[str, Any]]] = {}
    for row in exchange_link_rows:
        link_groups.setdefault(str(row['link_id']), []).append(row)
    for link_id, rows in sorted(link_groups.items()):
        q_values = [float(row['Q_exchange']) for row in rows]
        meta_type = 'frontal_direct' if 'front' in link_id else 'lateral_exchange'
        exchange_summary_rows.append(
            {
                'case_name': summary['case_name'],
                'scenario_family': summary['scenario_family'],
                'link_id': link_id,
                'link_type': meta_type,
                'exchange_event_count': len(rows),
                'peak_Q_exchange': float(max((abs(value) for value in q_values), default=0.0)),
                'cumulative_exchange_volume': float(sum(abs(float(row['dV_exchange'])) for row in rows)),
                'sign_flip_count': int(_sign_flip_count(q_values)),
                'mean_deta': float(np.mean([float(row['deta']) for row in rows])) if rows else 0.0,
                'first_exchange_time': float(min((float(row['time']) for row in rows), default=0.0)),
                'link_mass_closure_error': float(max((abs(float(row.get('mass_error', 0.0))) for row in payload['exchange_history'] if str(row['link_id']) == link_id), default=0.0)),
            }
        )

    return {
        'summary': summary,
        'crossing_diagnostics': crossing_rows,
        'stage_diff_rows': stage_diff_rows,
        'partition_rows': partition_rows,
        'exchange_summary_rows': exchange_summary_rows,
    }
