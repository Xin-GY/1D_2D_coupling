from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from experiments.io import read_csv, read_json, write_csv, write_json
from experiments.metrics import _analysis_grid, _filtered_series_arrays, _interp_linear, _rmse

DEFAULT_RERUN_ROOT = Path('artifacts/chapter_case_reruns/benchmark_1200_legacy')
CASE_SUFFIXES = [
    'strict_global_min_dt',
    'fixed_interval_002s',
    'fixed_interval_005s',
    'fixed_interval_015s',
    'fixed_interval_060s',
    'fixed_interval_300s',
]


def parse_args(description: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--output-root', default='artifacts/chapter_coupling_analysis')
    parser.add_argument('--rerun-root', default=str(DEFAULT_RERUN_ROOT))
    return parser.parse_args()


def _case_dir(rerun_root: Path, suffix: str) -> Path:
    matches = sorted((rerun_root / 'cases').glob(f'*_{suffix}'))
    for match in matches:
        if (match / 'timing_breakdown.json').exists():
            return match
    raise FileNotFoundError(f'No rerun case found for suffix={suffix} under {rerun_root}')


def _series_grid(case_dir: Path, probe_id: str) -> tuple[Any, Any, Any]:
    rows = read_csv(case_dir / 'stage_timeseries_1d.csv')
    times, values = _filtered_series_arrays(rows, id_key='probe_id', id_value=probe_id, value_key='stage')
    if times.size == 0:
        raise ValueError(f'No stage series for probe {probe_id} in {case_dir / "stage_timeseries_1d.csv"}')
    duration = float(times[-1])
    grid = _analysis_grid(duration)
    return times, values, _interp_linear(times, values, grid)


def benchmark_1200_cost_rows(rerun_root: Path | str) -> list[dict[str, Any]]:
    rerun_root = Path(rerun_root)
    strict_case = _case_dir(rerun_root, 'strict_global_min_dt')
    strict_config = read_json(strict_case / 'config.json')
    probe_id = str(strict_config.get('probe_defs', {}).get('primary_stage_probe', 'mainstem_mid'))
    strict_times, strict_values, strict_grid_values = _series_grid(strict_case, probe_id)
    analysis_grid = _analysis_grid(float(strict_times[-1]))
    strict_wall = float(read_json(strict_case / 'timing_breakdown.json')['wall_clock_seconds'])
    rows: list[dict[str, Any]] = []

    for suffix in CASE_SUFFIXES:
        case_dir = _case_dir(rerun_root, suffix)
        config = read_json(case_dir / 'config.json')
        timing = read_json(case_dir / 'timing_breakdown.json')
        _, _, candidate_grid_values = _series_grid(case_dir, probe_id)
        one_d = float(timing['one_d_advance_time'])
        two_d = float(timing['two_d_gpu_kernel_time'])
        boundary = float(timing['boundary_update_time'])
        exchange_manager = float(timing['gpu_inlets_apply_time']) + float(timing['scheduler_manager_overhead'])
        wall = float(timing['wall_clock_seconds'])
        misc = max(wall - one_d - two_d - boundary - exchange_manager, 0.0)
        stage_rmse = 0.0 if suffix == 'strict_global_min_dt' else float(_rmse(strict_grid_values, candidate_grid_values))
        exchange_interval = float(config.get('exchange_interval') or 0.0)
        scheduler_mode = str(config.get('scheduler_mode', 'strict'))
        rows.append({
            'case_name': str(config.get('case_name', case_dir.name)),
            'case_suffix': suffix,
            'scheduler_mode': scheduler_mode,
            'exchange_interval': exchange_interval,
            'probe_id': probe_id,
            'stage_rmse': stage_rmse,
            'wall_clock_seconds': wall,
            'relative_cost_ratio': wall / strict_wall if strict_wall > 0.0 else 0.0,
            'one_d_advance_time': one_d,
            'two_d_gpu_kernel_time': two_d,
            'boundary_update_time': boundary,
            'exchange_manager_time': exchange_manager,
            'misc_io_time': misc,
            'one_d_share': one_d / wall if wall > 0.0 else 0.0,
            'two_d_share': two_d / wall if wall > 0.0 else 0.0,
            'boundary_share': boundary / wall if wall > 0.0 else 0.0,
            'exchange_manager_share': exchange_manager / wall if wall > 0.0 else 0.0,
            'misc_io_share': misc / wall if wall > 0.0 else 0.0,
            'source_case_dir': str(case_dir),
            'source_stage_csv': str(case_dir / 'stage_timeseries_1d.csv'),
            'source_timing_json': str(case_dir / 'timing_breakdown.json'),
        })
    return rows


def write_benchmark_1200_cost_summary(rerun_root: Path | str) -> tuple[Path, Path, list[dict[str, Any]]]:
    rerun_root = Path(rerun_root)
    rows = benchmark_1200_cost_rows(rerun_root)
    summary_dir = rerun_root / 'summaries'
    csv_path = summary_dir / 'benchmark_1200_cost_summary.csv'
    json_path = summary_dir / 'benchmark_1200_cost_summary.json'
    write_csv(csv_path, rows)
    write_json(json_path, rows)
    return csv_path, json_path, rows
