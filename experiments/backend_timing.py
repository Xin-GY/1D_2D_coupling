from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from coupling.runtime_env import repair_anuga_editable_build_env
from experiments.chapter_cases import ChapterExperimentCase, generate_test7_cases, prepare_chapter_case
from experiments.io import ensure_dir, write_csv, write_json
from experiments.test7_data import Test7DataProvenance


repair_anuga_editable_build_env()


def _benchmark_strict_case(provenance: Test7DataProvenance, profile: str) -> ChapterExperimentCase:
    for case in generate_test7_cases(provenance, profile=profile):
        if case.scheduler_mode == 'strict_global_min_dt':
            return case
    raise RuntimeError('Unable to locate the benchmark strict_global_min_dt case for backend timing')


def _run_one_d_only_case(case: ChapterExperimentCase, backend: str, cache_root: Path, mesh_variant: str) -> dict[str, Any]:
    bench_case = replace(
        case,
        case_name=f'{case.case_name}_{backend}_1donly',
        one_d_backend=backend,
        mesh_variant=mesh_variant,
    )
    payload = prepare_chapter_case(bench_case, cache_root / bench_case.case_name)
    one_d = payload['manager'].one_d

    started = time.perf_counter()
    initial_dt = float(one_d.initialize())
    step_count = 0
    while float(one_d.network.current_sim_time) + 1.0e-12 < float(bench_case.duration):
        remaining = float(bench_case.duration) - float(one_d.network.current_sim_time)
        dt = min(float(one_d.predict_cfl_dt()), remaining)
        if dt <= 1.0e-12:
            break
        used_dt = float(one_d.advance_one_step(dt))
        if used_dt <= 0.0:
            break
        step_count += 1
    wall_clock = time.perf_counter() - started
    return {
        'backend': backend,
        'scenario_family': bench_case.scenario_family,
        'base_case_name': case.case_name,
        'case_name': bench_case.case_name,
        'duration': float(bench_case.duration),
        'mesh_variant': mesh_variant,
        'initial_cfl_dt': float(initial_dt),
        'final_time': float(one_d.network.current_sim_time),
        'step_count': int(step_count),
        'wall_clock_seconds': float(wall_clock),
        'total_volume_final': float(one_d.get_total_volume()),
    }


def write_one_d_backend_timing_comparison(
    output_root: Path,
    provenance: Test7DataProvenance,
    *,
    profile: str,
    mesh_variant: str = 'refined_figures',
) -> list[dict[str, Any]]:
    output_root = ensure_dir(Path(output_root))
    summaries_root = ensure_dir(output_root / 'summaries')
    cache_root = ensure_dir(output_root / 'logs' / 'one_d_backend_timing_cache')

    benchmark_case = _benchmark_strict_case(provenance, profile=profile)
    rows = [
        _run_one_d_only_case(benchmark_case, 'legacy', cache_root, mesh_variant),
        _run_one_d_only_case(benchmark_case, 'fastest_exact', cache_root, mesh_variant),
    ]
    legacy_time = next(row['wall_clock_seconds'] for row in rows if row['backend'] == 'legacy')
    for row in rows:
        row['relative_to_legacy'] = float(row['wall_clock_seconds'] / max(float(legacy_time), 1.0e-9))

    write_csv(summaries_root / 'one_d_backend_timing.csv', rows)
    write_json(summaries_root / 'one_d_backend_timing.json', rows)
    return rows
